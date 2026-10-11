import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from security_gate.core import ContractError, collect, triage

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scenarios',ROOT/'examples/build_scenarios.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
api_spec = importlib.util.spec_from_file_location('api',ROOT/'examples/tenant-api/api.py')
api = importlib.util.module_from_spec(api_spec)
api_spec.loader.exec_module(api)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.context, self.reviews = fixtures.scenarios()
        self.policy = json.loads((ROOT/'policies/security-v1.json').read_text())
        self.review = deepcopy(self.reviews['cross-tenant'])

    def run_gate(self, review=None):
        return triage(self.context,review or self.review,self.policy)

    def test_four_outcomes(self):
        for name, expected in [('correct','REVIEWED'),('cross-tenant','BLOCK'),('scanner-overlap','BLOCK'),('insufficient-coverage','INCOMPLETE')]:
            with self.subTest(name=name):
                result = self.run_gate(self.reviews[name])
                self.assertEqual(result['decision'],expected)
                self.assertTrue(result['can_continue'])

    def test_fixture_behavior(self):
        actor={'tenant':'A'}
        invoices={'I-A':{'tenant':'A','amount':10},'I-B':{'tenant':'B','amount':42}}
        self.assertEqual(api.get_invoice(actor,'I-A',invoices),10)
        with self.assertRaises(PermissionError):
            api.get_invoice(actor,'I-B',invoices)
        self.assertEqual(api.get_invoice_unsafe(actor,'I-B',invoices),42)

    def test_overlap_preserves_failure_and_origin(self):
        result=self.run_gate(self.reviews['scanner-overlap'])
        self.assertEqual(len(result['records']),1)
        self.assertEqual(result['records'][0]['external_origins'],['CX-1'])
        self.assertEqual(result['external_checks'][0]['status'],'failed')

    def test_false_correlations_are_not_deduplicated(self):
        for field,value in [('operation','POST /other'),('resource','user'),('boundary','service'),('condition','different'),('revision','b'*40),('executed_at','2025-10-11T11:00:00Z'),('executed_at','2026-10-12T11:00:00Z'),('status','passed'),('status','inconclusive'),('status','error')]:
            with self.subTest(field=field,value=value):
                r=deepcopy(self.reviews['scanner-overlap'])
                r['external_checks'][0][field]=value
                if field=='operation':
                    with self.assertRaises(ContractError):self.run_gate(r)
                else:
                    result=self.run_gate(r)
                    self.assertFalse(result['audit'][0]['accepted'])
                    self.assertEqual(result['records'][0]['external_origins'],[])

    def test_invalid_evidence_fails_closed(self):
        mutations=[lambda r:r['evidence'][0].update(quote='inventado'),
                   lambda r:r['evidence'][0].update(start=True),
                   lambda r:r['evidence'][0].update(end=9999),
                   lambda r:r['evidence'][0].update(path='../secret'),
                   lambda r:r['evidence'].append(deepcopy(r['evidence'][0])),
                   lambda r:r['candidates'][0].update(evidence_refs=['REQ']),
                   lambda r:r['candidates'][0].update(obligation_refs=['missing']),
                   lambda r:r.update(revision='b'*40),
                   lambda r:r.update(version=True),
                   lambda r:r.update(unknown=True),
                   lambda r:r['obligations'][0].update(mandatory='true'),
                   lambda r:r['candidates'][0].update(categories=['API99:2023']),
                   lambda r:r['candidates'][0].update(severity='critical'),
                   lambda r:r['candidates'][0].update(classification='excluded')]
        for mutation in mutations:
            with self.subTest(mutation=mutations.index(mutation)):
                r=deepcopy(self.review);mutation(r)
                with self.assertRaises(ContractError):self.run_gate(r)

    def test_hash_tampering(self):
        self.context['artifacts'][0]['content']+='tampered'
        with self.assertRaises(ContractError):self.run_gate()

    def test_mandatory_obligation_without_candidate(self):
        self.review['candidates']=[]
        self.assertEqual(self.run_gate()['decision'],'BLOCK')

    def test_empty_review_cannot_approve(self):
        self.review['obligations']=[];self.review['candidates']=[]
        with self.assertRaises(ContractError):self.run_gate()

    def test_unassessed_operation_cannot_approve(self):
        self.review['scope'].append('DELETE /invoices/{id}')
        with self.assertRaises(ContractError):self.run_gate()

    def test_hypothesis_keeps_severity(self):
        self.review['candidates'][0]['classification']='hypothesis'
        self.review['obligations'][0]['status']='unknown'
        result=self.run_gate()
        self.assertEqual(result['decision'],'INCOMPLETE')
        self.assertEqual(result['records'][0]['severity'],'P1')

    def test_compensating_control_exclusion(self):
        self.review['candidates'][0].update(classification='excluded',rationale='Filtro compensatório demonstrado no handler seguro.',evidence_refs=['SAFE','REQ','FLOW'])
        self.review['obligations'][0].update(status='verified',evidence_refs=['SAFE','REQ','FLOW'])
        result=self.run_gate()
        self.assertEqual(result['decision'],'REVIEWED')
        self.assertEqual(result['records'][0]['rule'],'S-04')

    def test_dependency_separate_from_block(self):
        self.review['dependencies']=[{'id':'D1','operation':self.review['scope'][0],'missing':'política temporal',
            'attempted_resolution':'contrato e ADR consultados','question':'Jobs autorizados sobrevivem à revogação?'}]
        result=self.run_gate()
        self.assertEqual(result['decision'],'BLOCK')
        self.assertFalse(result['can_continue'])

    def test_determinism(self):
        self.assertEqual(self.run_gate(),self.run_gate())

    def test_cli_exit_codes_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name, code in [('correct',0),('cross-tenant',1),('insufficient-coverage',2)]:
                for file,value in [('context',self.context),('review',self.reviews[name]),('policy',self.policy)]:
                    (root/f'{file}.json').write_text(json.dumps(value),encoding='utf-8')
                command=[sys.executable,'-m','security_gate','triage','--context',str(root/'context.json'),'--review',str(root/'review.json'),
                         '--policy',str(root/'policy.json'),'--out',str(root/'out.json'),'--report',str(root/'report.md')]
                done=subprocess.run(command,cwd=ROOT,capture_output=True)
                self.assertEqual(done.returncode,code,done.stderr)
                self.assertIn('Continuidade:',(root/'report.md').read_text(encoding='utf-8'))
            (root/'review.json').write_text('{"version":1,"version":1}',encoding='utf-8')
            self.assertEqual(subprocess.run(command,cwd=ROOT,capture_output=True).returncode,3)

    def test_collection_reads_committed_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            def g(*args):
                return subprocess.check_output(['git','-C',tmp,*args],stderr=subprocess.PIPE)
            g('init');g('config','user.email','fixture@example.invalid');g('config','user.name','Fixture')
            file=Path(tmp)/'api.py';file.write_text('original\n')
            g('add','api.py');g('commit','-m','fixture')
            file.write_text('local changes\n')
            context=collect(tmp,'HEAD',['api.py'])
            self.assertEqual(context['artifacts'][0]['content'],'original\n')
            with self.assertRaises(ContractError):collect(tmp,'HEAD',['not-tracked.py'])

    def test_cli_revalidates_snapshot_against_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def g(*args):
                return subprocess.check_output(['git','-C',tmp,*args],stderr=subprocess.PIPE)
            g('init');g('config','user.email','fixture@example.invalid');g('config','user.name','Fixture')
            for name in ('api.py','requirements.md','scanner.json'):
                (root/name).write_bytes((ROOT/'examples/tenant-api'/name).read_bytes())
            g('add','.');g('commit','-m','fixture')
            context=collect(tmp,'HEAD',['api.py','requirements.md','scanner.json'])
            review=deepcopy(self.reviews['correct']);review['revision']=context['revision']
            for name,value in [('context',context),('review',review),('policy',self.policy)]:
                (root/f'{name}.json').write_text(json.dumps(value),encoding='utf-8')
            command=[sys.executable,'-m','security_gate','triage','--repo',tmp,'--context',str(root/'context.json'),
                     '--review',str(root/'review.json'),'--policy',str(root/'policy.json'),'--out',str(root/'out.json'),'--report',str(root/'report.md')]
            run=subprocess.run(command,cwd=ROOT,capture_output=True)
            self.assertEqual(run.returncode,0,run.stderr)
            import hashlib
            context['artifacts'][0]['content']+='forged\n'
            context['artifacts'][0]['sha256']=hashlib.sha256(context['artifacts'][0]['content'].encode()).hexdigest()
            (root/'context.json').write_text(json.dumps(context),encoding='utf-8')
            self.assertEqual(subprocess.run(command,cwd=ROOT,capture_output=True).returncode,3)


if __name__=='__main__':unittest.main()
