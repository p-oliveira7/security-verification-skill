# Validação e guia de comparação

## O que foi executado

Em 11/10/2026, Python 3.12.12 no Windows: `python -m unittest discover -s tests -v` passou 16 métodos de teste (incluindo subcasos de correlação e contrato). A primeira execução no sandbox teve dois erros de permissão em diretórios temporários do Windows; a execução autorizada fora do sandbox passou integralmente.

A suíte verifica os quatro resultados sintéticos, comportamento seguro/inseguro entre empresas, preservação de falha/origem externa, divergências de condição/recurso/fronteira/revisão, datas antigas/futuras e estados externos não suficientes. Também verifica trechos adulterados, hashes divergentes, linhas e tipos inválidos, referências órfãs, IDs duplicados, contrato vazio, operação sem obrigação, exclusão sustentada, severidade de hipótese, continuidade independente, estabilidade, exit codes da CLI, JSON com chave duplicada e coleta de commit ignorando alteração local.

Também foi testada a conferência do snapshot contra Git pela CLI, incluindo adulteração de conteúdo com hash recalculado: ainda assim foi rejeitada. `quick_validate.py` da skill-creator aprovou estrutura e frontmatter. Não foi executado scanner real, avaliação independente por outro modelo, CI remoto ou teste em cliente Claude Code/Cursor. Não se deve interpretar aprovação dos testes como prova de detecção semântica. Os quatro cenários são fixtures transparentes, não um benchmark representativo de produção.

## Como comparar com outra implementação

| Pergunta | Evidência para comparar |
|---|---|
| Quem descobre o risco? | Nesta versão, agente; código só valida e encaminha declarações. Verifique se a outra solução distingue as responsabilidades. |
| O que prova o achado? | Cadeia ator/recurso/controle/efeito e referências literais de código, requisito e fluxo. Avalie se outra solução só usa categoria ou plausibilidade. |
| Ausência de candidatos aprova? | Não se obrigação mandatória estiver violada/desconhecida; revisão vazia é inválida. Ainda depende de inventário honesto pelo agente. |
| Como scanner entra? | Envelope normalizado explícito, idade, revisão, regra/perfil, fluxo e limites. Nesta versão não há parser proprietário. |
| Deduplicação apaga bloqueio? | Não; origem externa e falha permanecem no consolidado. Categoria igual é insuficiente. |
| Incerteza vira vulnerabilidade? | Não; hipótese e lacuna permanecem distinguíveis e impedem conclusão completa. |
| Pode continuar após bloqueio? | Sim; `can_continue` depende exclusivamente de dependência indispensável documentada. |
| Quais testes medem o modelo? | Nenhum nesta suíte. Acrescentar avaliações cegas de comportamento antes de afirmar qualidade semântica. |

## Próxima validação em adoção real

Usar fontes corporativas sanitizadas, fixar matriz de controles e critérios de impacto, selecionar formatos/versões reais de relatórios e implementar adaptadores com testes de proveniência. Medir riscos omitidos, falsos positivos, perguntas indispensáveis, duplicações e estabilidade semântica em revisões repetidas. Incluir abuso de benefício, corrida transacional, revogação de job e webhook com confiança indevida; estas lentes estão instruídas e aceitas no contrato, mas não têm fixtures executáveis próprias nesta primeira versão.

O registro de causa/correção é descritivo. O motor preserva candidatos separados; consolidar automaticamente causas com mesma correção exigiria um contrato específico de equivalência, ainda não implementado. A opção conservadora evita ocultar fluxos diferentes.
