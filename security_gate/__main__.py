import argparse
import json
import subprocess
import sys
from pathlib import Path
from .core import ContractError, collect, render, triage


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f'chave JSON duplicada: {key}')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(value, encoding='utf-8')


def main():
    p = argparse.ArgumentParser(description='Contratos e triagem contextual; não é scanner semântico.')
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('collect')
    c.add_argument('--repo', required=True)
    c.add_argument('--revision', required=True)
    c.add_argument('--paths', nargs='+', required=True)
    c.add_argument('--out', required=True)
    t = sub.add_parser('triage')
    t.add_argument('--repo', help='Revalida o snapshot contra objetos Git da revisão declarada.')
    for arg in ('context','review','policy','out','report'):
        t.add_argument('--'+arg, required=True)
    a = p.parse_args()
    try:
        if a.command == 'collect':
            result = collect(a.repo, a.revision, a.paths)
        else:
            context = read(a.context)
            if a.repo:
                actual = collect(a.repo, context['revision'], [x['path'] for x in context['artifacts']])
                if actual != context:
                    raise ContractError('snapshot diverge dos objetos Git')
            result = triage(context, read(a.review), read(a.policy))
            result['limitations'].append('Snapshot conferido contra Git local.' if a.repo else 'Snapshot validado internamente; origem Git não revalidada nesta execução.')
            write(a.report, render(result))
        write(a.out, json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        if a.command == 'triage':
            print(f"{result['decision']} | continuidade={result['can_continue']} | relatório={a.report}")
            return {'REVIEWED':0,'BLOCK':1,'INCOMPLETE':2}[result['decision']]
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f'INVALID: {exc}', file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())
