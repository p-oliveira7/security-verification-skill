# Contrato v1 e regras determinísticas

O validador executável é `security_gate/core.py::validate`. Rejeita campos desconhecidos, IDs repetidos, versões diferentes, tipos incorretos, referências órfãs e trechos divergentes. Os JSON produzidos por `examples/build_scenarios.py` são exemplos completos do contrato. Não há dependências externas de JSON Schema; a implementação Python é a única fonte normativa da validação.

## Artefatos de entrada

`context.json`: `version=1`, `revision` completa de 40/64 dígitos hexadecimais, `artifacts[]` com `path`, conteúdo UTF-8 e SHA-256. O coletor lê blobs Git de arquivos regulares rastreados. Links simbólicos, arquivos binários não UTF-8 e arquivos não rastreados não são suportados. Não coletar segredos. Arquivos de um scan externo precisam estar no snapshot usado como evidência; para uso real, mantenha uma cópia sanitizada rastreada da evidência na revisão de auditoria pertinente.

`review.json` contém:

| Campo | Contrato e propósito |
|---|---|
| `version`, `revision`, `assessed_at` | v1, mesma revisão do contexto, instante ISO 8601 com timezone; define a referência temporal reproduzível. |
| `scope` | Lista não vazia de operações únicas. Cada operação exige obrigação avaliada. |
| `evidence` | `id`, `kind` (`code`, `document`, `flow`, `scanner`), `path`, `start`, `end`, `quote` literal, linhas inclusivas começando em 1. |
| `obligations` | `id`, `operation`, `control`, `mandatory` booleano, `status`, `rationale`, `evidence_refs`. Estados: `verified`, `violated`, `unknown`, `not_applicable`. |
| `candidates` | IDs e operação; recurso, fronteira, condição, controle esperado, impacto, severidade P0–P3, classificação, justificativa, referências de evidência/obrigações, categorias, causa e correção. Veja exemplo gerado. |
| `external_checks` | Envelope normalizado descrito em [external.md](external.md). Lista vazia não prova execução de scanner. |
| `correlations` | `id`, `candidate_id`, `check_id`, `rationale`, `evidence_refs`. Alegação de equivalência examinada pelas regras mecânicas e pelo agente. |
| `dependencies` | `id`, `operation`, `missing`, `attempted_resolution`, `question`. Só dependências indispensáveis impedem continuidade. |

Obrigações verificadas/violadas exigem evidência de código, documento e fluxo. `unknown` pode ter lista vazia, justamente para tornar a falta visível. `not_applicable` exige justificativa e evidência, nunca é substituto para inventário desconhecido. Candidatos `supported` e `excluded` exigem os três tipos; `hypothesis` exige ao menos uma referência válida. Um candidato sustentado deve apontar obrigação violada do mesmo fluxo; exclusão exige obrigações verificadas ou não aplicáveis. A relevância da evidência é revisada pelo agente, não provada por presença de tipos.

## Regras do planejamento e implementação

| Regra | Comportamento nesta versão |
|---|---|
| S-01 | Erro de contrato encerra a execução com `INVALID`, exit 3. Recuperar fonte e executar novamente. |
| S-02 | Campo obrigatório vazio ou evidência insuficiente para a classificação invalida o contrato; plausibilidade vira hipótese após investigação do agente. |
| S-03 | Correlação exige falha externa atual, revisão/condição/operação/recurso/fronteira iguais e candidato sustentado. Preserva falha e adiciona origem ao mesmo registro. |
| S-04 | Exclusão explícita exige justificativa, código/documento/fluxo e obrigações compatíveis; o motor não descobre controles compensatórios. |
| S-05 | Achado sustentado em severidade bloqueadora, obrigação mandatória violada ou check obrigatório atual falho gera `BLOCK`. |
| S-06 | Hipótese mantém severidade potencial e gera `INCOMPLETE`, salvo bloqueador já sustentado. |
| S-07 | Obrigação desconhecida ou check ausente/antigo/incompatível/inconclusivo gera lacuna e `INCOMPLETE`, mesmo sem candidatos. |
| S-08 | Sem agrupamento automático por texto, categoria ou causa declarada. Preserva causas separadas; equivalência semântica é responsabilidade do agente. |
| S-09 | Dependência concreta define `can_continue=false`; pergunta e tentativa de resolução são preservadas. |
| S-10 | Na ausência de dependência, `can_continue=true` mesmo com `BLOCK` ou `INCOMPLETE`. |

Precedência: `BLOCK` > `INCOMPLETE` > `REVIEWED`. `REVIEWED` significa que não há pendências detectadas no conjunto declarado. Não é um PASS global nem certificação. Obrigações mandatórias violadas bloqueiam mesmo que o modelo não emita candidato. Um conflito de correlação não aceito torna a revisão incompleta, salvo bloqueador prevalecente. Falha externa atual obrigatória continua bloqueando mesmo sem correlação.

Política v1: versão, lista de severidades bloqueadoras e idade máxima externa em horas (exemplo: 168). Sem score que esconda bloqueadores, sem limite de achados. Datas futuras em relação a `assessed_at` são incompatíveis. Comparação e ordenação são reproduzíveis para mesmas entradas. O instante declarado deve ser verificado pelo revisor no uso real; o motor não consulta relógio nem servidor de CI.

## Saída e integridade

Saída inclui revisão, política completa, escopo, decisão, continuidade, registros, checks, obrigações, lacunas, auditoria de correlação, dependências, evidências, hashes e limites. O renderizador mantém esses conteúdos e não recalcula decisões. Exit codes: 0 `REVIEWED`, 1 `BLOCK`, 2 `INCOMPLETE`, 3 erro de contrato/execução. Em erro, arquivos de execuções anteriores podem continuar existindo: consumidores devem respeitar exit code e usar diretório novo por execução.

Hashes conferem consistência do snapshot, não autenticidade. Em triagem real, passe `--repo REPO` para reconstruir os blobs da revisão e comparar o snapshot. Sem `--repo`, o relatório declara origem não revalidada. Mesmo com Git, identidade do autor, validade de documentos, autenticidade de scanner, abrangência do escopo e conclusão semântica não são atestadas pelo motor.
