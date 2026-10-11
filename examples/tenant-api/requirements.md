# Política sintética
REQ-TENANT: um ator só pode consultar faturas de sua própria empresa.
A fatura I-B pertence à empresa B; o ator U-A pertence à empresa A.
GET /invoices/I-B: U-A -> handler -> seleção I-B -> autorização de tenant -> resposta ou rejeição.
O fluxo inseguro seleciona I-B e retorna o valor sem avaliar a empresa do ator.
Impacto: exposição do valor de uma fatura de outra empresa. Severidade sintética P1.
