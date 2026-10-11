# Integração com Checkmarx e Sonar

Esta versão implementa um envelope comum validado, não adaptadores para formatos proprietários. Não foi conectada a instalações corporativas nem executou scanners. Produtos, edições, perfis e versões mudam: inventarie o relatório real antes de adicionar um adaptador. O agente pode transcrever/normalizar um relatório, mantendo sua evidência literal e justificando cada mapeamento. Não use nomes de ferramentas como garantia de capacidade.

Cada `external_checks[]` tem exatamente:

```json
{
  "id": "CX-1",
  "tool": "Checkmarx",
  "mode": "SAST",
  "profile": "perfil efetivamente executado",
  "rule": "ID da regra efetiva",
  "revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "executed_at": "2026-10-11T11:00:00Z",
  "status": "failed",
  "mandatory": true,
  "operation": "GET /invoices/{id}",
  "resource": "invoice",
  "boundary": "tenant",
  "condition": "tenant-check-missing",
  "evidence_refs": ["SCAN"],
  "limitations": "Informar limites reais do escopo e da modalidade."
}
```

Ferramentas aceitas: `Checkmarx`, `Sonar`. Estados: `passed`, `failed`, `not_run`, `inconclusive`, `error`. Resultado observado e obrigatoriedade são distintos; scan obrigatório não informado deve ser representado como `not_run`, não omitido. Estados concluídos/inconclusivos exigem evidência do tipo scanner; erro e não executado podem não ter relatório. Declare instante da observação em `executed_at` para não executado e explique em `limitations`.

Para correlacionar, o agente investiga condição e cadeia de efeito nas fontes. Valores textuais iguais são apenas uma condição necessária mecânica, nunca prova semântica. Uma correlação válida inclui evidência do caminho, do relatório e justificativa. O motor exige a revisão exata e janela de validade; não deduplica por categoria OWASP, regra parecida ou linha próxima. Um resultado aprovado que contradiz achado contextual sustentado não é usado para ocultá-lo: a correlação é recusada e permanece auditável.

O scanner pode ter várias ocorrências. Normalize por condição e fluxo; preserve identificadores originais na evidência. Esta versão não colapsa automaticamente várias ocorrências de scanner nem vários candidatos. Isso evita perder causas diferentes por comparação textual. A apresentação mantém um registro contextual enriquecido com `external_origins`, sem declarar que o bloqueio externo foi resolvido.

Limite de proveniência: o validador verifica existência e igualdade dos trechos, não interpreta o conteúdo proprietário para conferir se o envelope foi transcrito corretamente. Essa conferência cabe ao agente/revisor. Um envelope falsamente rotulado é um problema de análise que testes de schema não resolvem. Antes da adoção em CI, implementar adaptadores versionados com fixtures reais sanitizadas, matriz de regras habilitadas e vínculo verificável entre scan e código analisado.
