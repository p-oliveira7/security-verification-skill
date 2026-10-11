"""Generate explicit synthetic assessments; this is not a semantic analyzer."""
import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from security_gate.core import render, triage


def scenarios():
    base = ROOT / 'examples/tenant-api'
    artifacts = []
    for name in ('api.py','requirements.md','scanner.json'):
        content = (base/name).read_text(encoding='utf-8')
        artifacts.append({'path':name,'content':content,'sha256':hashlib.sha256(content.encode()).hexdigest()})
    # Fixture revision is intentionally synthetic, not a repository commit.
    context = {'version':1,'revision':'a'*40,'artifacts':artifacts}
    evidence = []
    for id_, kind, path, start, end in [('CODE','code','api.py',9,11),('SAFE','code','api.py',2,6),
                                     ('REQ','document','requirements.md',2,2),
                                     ('FLOW','flow','requirements.md',3,6),('SCAN','scanner','scanner.json',1,9)]:
        content = next(x['content'] for x in artifacts if x['path']==path)
        evidence.append({'id':id_,'kind':kind,'path':path,'start':start,'end':end,
                         'quote':'\n'.join(content.splitlines()[start-1:end])})
    obligation = {'id':'O-TENANT','operation':'GET /invoices/{id}','control':'REQ-TENANT',
                  'mandatory':True,'status':'violated','rationale':'O handler inseguro retorna amount sem verificar tenant.',
                  'evidence_refs':['CODE','REQ','FLOW']}
    candidate = {'id':'SEC-001','operation':obligation['operation'],'resource':'invoice',
                 'boundary':'tenant','condition':'tenant-check-missing','expected_control':'validar tenant antes de retornar valor',
                 'impact':'exposição de valor de fatura de outra empresa','severity':'P1','classification':'supported',
                 'rationale':'U-A consulta I-B pelo caminho inseguro; nenhuma camada adicional existe nesta fixture.',
                 'evidence_refs':['CODE','REQ','FLOW'],'obligation_refs':['O-TENANT'],
                 'categories':['API1:2023'],'root_cause':'invoice-tenant-filter','correction':'verificar tenant no acesso à fatura'}
    review = {'version':1,'revision':context['revision'],'assessed_at':'2026-10-11T12:00:00Z',
              'scope':[obligation['operation']],'evidence':evidence,'obligations':[obligation],
              'candidates':[candidate],'external_checks':[],'correlations':[],'dependencies':[]}
    broken = deepcopy(review)
    correct = deepcopy(review)
    correct['candidates'] = []
    correct['obligations'][0].update(status='verified',rationale='O caminho seguro rejeita tenant divergente antes da resposta.',evidence_refs=['SAFE','REQ','FLOW'])
    overlap = deepcopy(review)
    overlap['external_checks'] = [{'id':'CX-1','tool':'Checkmarx','mode':'synthetic','profile':'fixture',
        'rule':'SYNTHETIC-TENANT-AUTH','revision':context['revision'],'executed_at':'2026-10-11T11:00:00Z',
        'status':'failed','mandatory':True,'operation':candidate['operation'],'resource':'invoice','boundary':'tenant',
        'condition':'tenant-check-missing','evidence_refs':['SCAN'],'limitations':'fixture, sem execução de scanner real'}]
    overlap['correlations'] = [{'id':'COR-1','candidate_id':'SEC-001','check_id':'CX-1',
        'rationale':'Relatório sintético aponta o mesmo handler, acesso à fatura e omissão de tenant.',
        'evidence_refs':['CODE','FLOW','SCAN']}]
    insufficient = deepcopy(correct)
    insufficient['obligations'][0].update(status='unknown',rationale='Scan de autorização obrigatório não fornecido; cobertura não comprovada.',evidence_refs=[])
    insufficient['external_checks'] = deepcopy(overlap['external_checks'])
    insufficient['external_checks'][0].update(status='not_run',evidence_refs=[])
    return context, {'correct':correct,'cross-tenant':broken,'scanner-overlap':overlap,'insufficient-coverage':insufficient}


if __name__ == '__main__':
    out = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work/scenarios'
    out.mkdir(parents=True, exist_ok=True)
    context, reviews = scenarios()
    policy = json.loads((ROOT/'policies/security-v1.json').read_text())
    (out/'context.json').write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
    for name, review in reviews.items():
        result = triage(context,review,policy)
        (out/f'{name}.review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/f'{name}.result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/f'{name}.md').write_text(render(result),encoding='utf-8')
        print(f'{name}: {result["decision"]}, can_continue={result["can_continue"]}')
