"""Validate declared evidence and route agent assessments without semantic inference."""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import PurePosixPath


class ContractError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ContractError(message)


def obj(value, fields, label):
    require(type(value) is dict and set(value) == set(fields.split()), f'{label}: campos inválidos')


def string(value):
    return type(value) is str and bool(value.strip())


def strings(value):
    return type(value) is list and all(string(x) for x in value) and len(value) == len(set(value))


def timestamp(value):
    require(string(value), 'timestamp ausente')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(dt.utcoffset() is not None, 'timestamp deve incluir timezone')
        return dt.astimezone(timezone.utc)
    except ValueError as exc:
        raise ContractError('timestamp inválido') from exc


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE)


def collect(repo, revision, paths):
    commit = git(repo, 'rev-parse', '--verify', revision + '^{commit}').decode().strip()
    tracked = set(git(repo, 'ls-tree', '-r', '--name-only', commit).decode().splitlines())
    artifacts = []
    for path in sorted(set(paths)):
        require(path in tracked, f'arquivo não rastreado: {path}')
        mode = git(repo, 'ls-tree', commit, '--', path).decode().split()[0]
        require(mode in ('100644', '100755'), 'somente arquivos regulares')
        content = git(repo, 'show', f'{commit}:{path}').decode('utf-8')
        artifacts.append({'path': path, 'content': content,
                          'sha256': hashlib.sha256(content.encode()).hexdigest()})
    require(bool(artifacts), 'coleta vazia')
    return {'version': 1, 'revision': commit, 'artifacts': artifacts}


def index(items, label):
    require(type(items) is list, f'{label}: lista esperada')
    result = {}
    for item in items:
        require(type(item) is dict and string(item.get('id')), f'{label}: id inválido')
        require(item['id'] not in result, f'{label}: id duplicado')
        result[item['id']] = item
    return result


def validate(context, review, policy):
    obj(context, 'version revision artifacts', 'context')
    require(type(context['version']) is int and context['version'] == 1, 'versão inválida')
    require(type(context['revision']) is str and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', context['revision']), 'revisão completa obrigatória')
    require(type(context['artifacts']) is list and context['artifacts'], 'artefatos ausentes')
    artifacts = {}
    for a in context['artifacts']:
        obj(a, 'path content sha256', 'artifact')
        require(string(a['path']) and '\\' not in a['path'] and ':' not in a['path'], 'path inválido')
        p = PurePosixPath(a['path'])
        require(not p.is_absolute() and '..' not in p.parts and a['path'] not in artifacts, 'path inválido/duplicado')
        require(type(a['content']) is str and hashlib.sha256(a['content'].encode()).hexdigest() == a['sha256'], 'hash divergente')
        artifacts[a['path']] = a
    obj(policy, 'version blocking_severities external_max_age_hours', 'policy')
    require(string(policy['version']) and strings(policy['blocking_severities']) and set(policy['blocking_severities']) <= {'P0','P1','P2','P3'}, 'policy inválida')
    require(type(policy['external_max_age_hours']) is int and policy['external_max_age_hours'] > 0, 'janela inválida')
    obj(review, 'version revision assessed_at scope evidence obligations candidates external_checks correlations dependencies', 'review')
    require(type(review['version']) is int and review['version'] == 1 and review['revision'] == context['revision'], 'review de outra revisão')
    assessed = timestamp(review['assessed_at'])
    require(strings(review['scope']) and review['scope'], 'escopo ausente')
    evidence = index(review['evidence'], 'evidence')
    for e in evidence.values():
        obj(e, 'id kind path start end quote', 'evidence')
        require(e['kind'] in ('code','document','flow','scanner'), 'tipo de evidência inválido')
        require(e['path'] in artifacts, 'referência não coletada')
        lines = artifacts[e['path']]['content'].splitlines()
        require(type(e['start']) is int and type(e['end']) is int and 1 <= e['start'] <= e['end'] <= len(lines), 'linhas inválidas')
        require(string(e['quote']) and e['quote'] == '\n'.join(lines[e['start']-1:e['end']]), 'trecho divergente')

    def refs(value, nonempty=True):
        require(strings(value) and (bool(value) or not nonempty) and set(value) <= evidence.keys(), 'evidence_refs inválidas')

    obligations = index(review['obligations'], 'obligations')
    require(bool(obligations), 'obrigações ausentes: não aprovar revisão vazia')
    for o in obligations.values():
        obj(o, 'id operation control mandatory status rationale evidence_refs', 'obligation')
        require(o['operation'] in review['scope'] and string(o['control']) and type(o['mandatory']) is bool, 'obrigação inválida')
        require(o['status'] in ('verified','violated','unknown','not_applicable') and string(o['rationale']), 'status de obrigação inválido')
        refs(o['evidence_refs'], o['status'] != 'unknown')
        if o['status'] in ('verified','violated'):
            require({'code','document','flow'} <= {evidence[x]['kind'] for x in o['evidence_refs']}, 'obrigação decidida exige código, documento e fluxo')
    require(set(review['scope']) <= {o['operation'] for o in obligations.values()}, 'operação sem obrigação avaliada')
    candidates = index(review['candidates'], 'candidates')
    for c in candidates.values():
        obj(c, 'id operation resource boundary condition expected_control impact severity classification rationale evidence_refs obligation_refs categories root_cause correction', 'candidate')
        require(c['operation'] in review['scope'], 'operação fora do escopo')
        for field in ('resource','boundary','condition','expected_control','impact','rationale','root_cause','correction'):
            require(string(c[field]), f'candidate: {field} ausente')
        require(c['severity'] in ('P0','P1','P2','P3'), 'severidade inválida')
        require(c['classification'] in ('supported','hypothesis','excluded'), 'classificação inválida')
        refs(c['evidence_refs'])
        require(strings(c['obligation_refs']) and c['obligation_refs'] and set(c['obligation_refs']) <= obligations.keys(), 'obligation_refs inválidas')
        require(all(obligations[x]['operation'] == c['operation'] for x in c['obligation_refs']), 'obrigação de outro fluxo')
        allowed = {f'API{i}:2023' for i in range(1,11)} | {'business_flow_abuse','replay_and_concurrency','permission_lifecycle','cross_service_trust'}
        require(strings(c['categories']) and c['categories'] and set(c['categories']) <= allowed, 'categoria inválida')
        kinds = {evidence[x]['kind'] for x in c['evidence_refs']}
        if c['classification'] in ('supported','excluded'):
            require({'code','document','flow'} <= kinds, 'decisão sustentada exige código, documento e fluxo')
        if c['classification'] == 'supported':
            require(any(obligations[x]['status'] == 'violated' for x in c['obligation_refs']), 'achado sem obrigação violada')
        if c['classification'] == 'excluded':
            require(all(obligations[x]['status'] in ('verified','not_applicable') for x in c['obligation_refs']), 'exclusão contraditória')
    checks = index(review['external_checks'], 'external_checks')
    for x in checks.values():
        obj(x, 'id tool mode profile rule revision executed_at status mandatory operation resource boundary condition evidence_refs limitations', 'external_check')
        require(x['tool'] in ('Checkmarx','Sonar'), 'ferramenta não suportada')
        require(x['operation'] in review['scope'] and type(x['mandatory']) is bool, 'escopo/check inválido')
        for field in ('mode','profile','rule','revision','resource','boundary','condition','limitations'):
            require(string(x[field]), f'external_check: {field} ausente')
        require(x['status'] in ('passed','failed','not_run','inconclusive','error'), 'status externo inválido')
        timestamp(x['executed_at'])
        refs(x['evidence_refs'], x['status'] not in ('not_run','error'))
        require(all(evidence[e]['kind'] == 'scanner' for e in x['evidence_refs']), 'resultado externo exige relatório scanner')
    correlations = index(review['correlations'], 'correlations')
    for r in correlations.values():
        obj(r, 'id candidate_id check_id rationale evidence_refs', 'correlation')
        require(r['candidate_id'] in candidates and r['check_id'] in checks and string(r['rationale']), 'correlação inválida')
        refs(r['evidence_refs'])
    dependencies = index(review['dependencies'], 'dependencies')
    for d in dependencies.values():
        obj(d, 'id operation missing attempted_resolution question', 'dependency')
        require(d['operation'] in review['scope'] and all(string(d[k]) for k in ('missing','attempted_resolution','question')), 'dependência inválida')
    return assessed, candidates, checks, obligations


def triage(context, review, policy):
    assessed, candidates, checks, obligations = validate(context, review, policy)
    audit, gaps, correlated = [], [], {}
    fresh = {}
    for x in checks.values():
        age = (assessed - timestamp(x['executed_at'])).total_seconds() / 3600
        fresh[x['id']] = x['revision'] == context['revision'] and 0 <= age <= policy['external_max_age_hours'] and x['status'] in ('passed','failed')
        if not fresh[x['id']]:
            gaps.append({'id': x['id'], 'reason': 'cobertura externa ausente, antiga, incompatível ou inconclusiva', 'mandatory': x['mandatory']})
    for r in review['correlations']:
        c, x = candidates[r['candidate_id']], checks[r['check_id']]
        same = all(c[k] == x[k] for k in ('operation','resource','boundary','condition'))
        # Correlation cannot convert an external pass into proof against a supported violation.
        accepted = same and fresh[x['id']] and x['status'] == 'failed' and c['classification'] == 'supported'
        audit.append({'id':r['id'], 'rule':'S-03', 'accepted':accepted, 'rationale':r['rationale'], 'evidence_refs':r['evidence_refs']})
        if accepted:
            correlated.setdefault(c['id'], []).append(x['id'])
    for o in obligations.values():
        if o['status'] == 'unknown':
            gaps.append({'id':o['id'], 'reason':o['rationale'], 'mandatory':o['mandatory']})
    records = []
    for c in candidates.values():
        record = dict(c)
        record['external_origins'] = sorted(set(correlated.get(c['id'], [])))
        record['rule'] = {'supported':'S-05','hypothesis':'S-06','excluded':'S-04'}[c['classification']]
        records.append(record)
    records.sort(key=lambda c:(c['severity'],c['id']))
    blocking = any(c['classification']=='supported' and c['severity'] in policy['blocking_severities'] for c in records)
    blocking |= any(x['mandatory'] and x['status']=='failed' and fresh[x['id']] for x in checks.values())
    # A violated mandatory obligation remains a blocker even when no model candidate exists.
    blocking |= any(o['mandatory'] and o['status']=='violated' for o in obligations.values())
    incomplete = bool(gaps) or any(c['classification']=='hypothesis' for c in records)
    incomplete |= any(not a['accepted'] for a in audit)
    incomplete |= bool(review['dependencies'])
    decision = 'BLOCK' if blocking else 'INCOMPLETE' if incomplete else 'REVIEWED'
    return {'version':1, 'revision':context['revision'], 'policy':policy, 'scope':review['scope'],
            'decision':decision, 'can_continue':not bool(review['dependencies']),
            'records':records, 'external_checks':review['external_checks'], 'obligations':review['obligations'],
            'gaps':gaps, 'audit':audit, 'dependencies':review['dependencies'],
            'evidence':review['evidence'], 'artifact_hashes':{a['path']:a['sha256'] for a in context['artifacts']},
            'limitations':['Validação mecânica não comprova semântica ou exploração.', 'REVIEWED se limita às obrigações declaradas; não certifica segurança.']}


def render(result):
    lines = ['# Security — revisão contextual', '', f"Resultado: {result['decision']}",
             f"Continuidade: {'permitida' if result['can_continue'] else 'dependência indispensável'}",
             f"Revisão: {result['revision']}", f"Escopo: {', '.join(result['scope'])}", '']
    for record in result['records']:
        lines.extend([f"- {record['id']} — {record['classification']} / {record['severity']}: {record['impact']}",
                      f"  Motivo: {record['rationale']}",
                      f"  Próximo passo: {record['correction']}",
                      f"  Evidências: {', '.join(record['evidence_refs'])}; origens externas: {', '.join(record['external_origins']) or 'nenhuma comprovada'}.", ''])
    for gap in result['gaps']:
        lines.extend([f"- Lacuna {gap['id']}: {gap['reason']}", ''])
    for label, value in [('Achados, hipóteses e exclusões','records'), ('Obrigações','obligations'),
                         ('Checks externos','external_checks'), ('Lacunas','gaps'), ('Correlações','audit'),
                         ('Dependências','dependencies'), ('Evidências','evidence'), ('Limites','limitations')]:
        lines.extend([f'## {label}', '', '```json', json.dumps(result[value],ensure_ascii=False,indent=2), '```', ''])
    return '\n'.join(lines)
