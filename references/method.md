# Método da análise contextual

## Coleta e investigação

Comece pela operação e pelo efeito de negócio. Identifique quem inicia a ação, em nome de quem ela ocorre, qual objeto ou campo é acessado, qual tenant governa o recurso e onde os controles realmente executam. Consulte handler, serviço, persistência, middleware, gateway, jobs e integrações relevantes. A seleção de arquivos do coletor é explícita: ele não descobre automaticamente todas as rotas ou dependências. Registre faltas de inventário como obrigações desconhecidas.

Capture o requisito aplicável com linhas literais. Uma convenção presumida de segurança não substitui uma política temporal de revogação ou de conclusão de jobs. Se faltar política, mantenha hipótese ou lacuna e explique qual decisão ela impede. Toda operação em `scope` deve ter uma obrigação; a lista de obrigações deve incluir também condições sem candidatos. Sem essa etapa, um modelo que não emite candidatos poderia produzir falsa tranquilidade.

Para um achado sustentado, descreva a cadeia ator → entrada → recurso → controle efetivo → efeito proibido. Verifique a existência de controles compensatórios antes de declarar ausência de autorização. Código, documento e fluxo precisam estar referenciados; a suficiência semântica e a veracidade do impacto permanecem responsabilidade do agente/revisor. Um documento descrevendo o fluxo não demonstra sozinho que ele está implementado. Registre teste executado, resultado e revisão quando existirem; não invente execução.

## Seleção por gatilhos

Taxonomia fixada: [OWASP API Security Top 10, edição 2023](https://owasp.org/API-Security/editions/2023/en/0x11-t10/). Ela organiza a revisão, não define severidade nem certifica cobertura completa.

| Categoria | Gatilho e pergunta verificável |
|---|---|
| API1:2023 — autorização por objeto | ID, lote, tenant, proprietário: o sujeito pode acessar cada objeto retornado? |
| API2:2023 — autenticação | Tokens, sessões, delegação: a identidade continua válida em cada etapa? |
| API3:2023 — autorização por propriedade | Entrada, saída, atualização parcial: quais campos cada papel pode ler/alterar? |
| API4:2023 — consumo de recursos | Paginação, payload, fan-out: limites cobrem multiplicadores e custo efetivo? |
| API5:2023 — autorização por função | Rotas administrativas e métodos alternativos: todos os caminhos validam o papel? |
| API6:2023 — fluxos sensíveis | Reserva, benefício, emissão: uso autorizado pode violar limite de negócio? |
| API7:2023 — SSRF | URL ou redirecionamento externo: destino e egress mantêm a fronteira permitida? |
| API8:2023 — configuração | Gateway, CORS, erros, deployment: configuração efetiva sustenta a exposição prevista? |
| API9:2023 — inventário | Versões, aliases, legados: todos os caminhos expostos estão inventariados? |
| API10:2023 — consumo de APIs | Parceiros, webhooks: origem, dados e efeitos externos são validados e autorizados? |

Lentes complementares não criam achados adicionais por si:

- `business_flow_abuse`: ator autorizado, limite de negócio e benefício/custo indevido demonstrado.
- `replay_and_concurrency`: invariante sensível, fronteira transacional e efeito de reenvio/simultaneidade. Ausência de header de idempotência não basta.
- `permission_lifecycle`: evento de revogação/troca de papel, regra temporal, caches e identidade usada pelo worker.
- `cross_service_trust`: origem, contrato, fronteira de confiança e autorização do efeito produzido.

## Impacto, apresentação e continuidade

Use consequência, classe de dados, alcance de tenants, duração e reversibilidade para justificar P0–P3; a política de exemplo bloqueia P0/P1. Não classifique P0 apenas pelo rótulo OWASP. Confiança insuficiente transforma a conclusão em hipótese; não torna um impacto potencialmente grave menos grave.

Apresente resumo legível antes do JSON técnico. Explique resultado, continuidade e próximo passo. Preserve todas as causas, mesmo que o resumo seja curto. Para correlação, mantenha os IDs das duas origens e a justificativa; não confunda deduplicação com resolução. O motor não agrupa automaticamente causas com textos parecidos. Se o agente consolidar uma causa antes do contrato, deve preservar cada fluxo/impacto e evidências; para esta versão, prefira registros separados quando não houver equivalência demonstrada.

Dependência é algo concreto que impede a próxima análise, após busca nas fontes. Um achado P1 com comportamento esperado claro bloqueia a aprovação, mas permite continuar com cenários de teste. Se não se sabe se um job deve sobreviver à revogação, registre as fontes consultadas e a pergunta mínima. A skill permanece utilizável sem Intent ou Coverage; cenários de teste são saída opcional da conversa, não execução automática de outro gate.
