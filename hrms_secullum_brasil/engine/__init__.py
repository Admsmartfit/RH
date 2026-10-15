"""Motor de cálculo CLT/CCT — Python puro.

Regras deste pacote:
- Proibido importar frappe, erpnext ou hrms (verificado por engine/tests/test_isolamento.py).
- Entrada e saída por dataclasses (marcações, jornada prevista, regra vigente, feriados ->
  minutos por categoria, ocorrências, inconsistências).
- Tempos em minutos inteiros; dinheiro em Decimal com ROUND_HALF_UP apenas no valor final.

Implementação a partir da Etapa 4 (docs/PRD.md, Seção 11).
"""

__all__: list[str] = []
