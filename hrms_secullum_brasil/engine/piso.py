"""Piso salarial do cargo na CCT (AJ-01 do docs/PRD-alteracoes.md).

O salário contratual é livre (pode ser maior que o piso). O programa só avisa quando ele fica abaixo do piso
proporcional à carga do perfil: piso x carga do perfil / carga de referência. Horista: piso por hora, sem
proporção. Alerta, nunca bloqueio.
"""

from decimal import ROUND_HALF_UP, Decimal

MENSALISTA = "Mensalista"
HORISTA = "Horista"
CENTAVO = Decimal("0.01")


def piso_proporcional(
	tipo: str, valor_piso: Decimal, carga_referencia_min: int, carga_perfil_min: int | None
) -> Decimal:
	valor = Decimal(str(valor_piso))
	if tipo != HORISTA and carga_referencia_min and carga_perfil_min:
		valor = valor * carga_perfil_min / carga_referencia_min
	return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def aviso_piso(
	salario: Decimal,
	tipo: str,
	valor_piso: Decimal,
	carga_referencia_min: int,
	carga_perfil_min: int | None,
) -> str | None:
	if not valor_piso:
		return None
	piso = piso_proporcional(tipo, valor_piso, carga_referencia_min, carga_perfil_min)
	if Decimal(str(salario)) >= piso:
		return None
	unidade = "por hora" if tipo == HORISTA else "por mês"
	return f"Salário de R$ {Decimal(str(salario)):.2f} abaixo do piso do cargo (R$ {piso:.2f} {unidade})."
