"""Exames ocupacionais (ASO) e treinamentos com vencimento (AJ-19 do docs/PRD-alteracoes.md; NR-1, NR-7).

Aviso ao RH e ao gestor 30 dias antes do vencimento; vencido vira inconsistência (aviso no fechamento, sem
bloquear). O próximo vencimento do ASO é informado pelo RH (PCMSO); vazio, sugere 1 ano depois do exame.
"""

from datetime import date, timedelta

from hrms_secullum_brasil.engine.banco_horas import adicionar_meses

ANTECEDENCIA_DIAS = 30
OK = "ok"
A_VENCER = "a_vencer"
VENCIDO = "vencido"
DEMISSIONAL = "Demissional"


def situacao(vencimento: date | None, hoje: date, antecedencia: int = ANTECEDENCIA_DIAS) -> str:
	if vencimento is None:
		return OK
	if vencimento < hoje:
		return VENCIDO
	if vencimento <= hoje + timedelta(days=antecedencia):
		return A_VENCER
	return OK


def vencimento_sugerido(data_exame: date, tipo: str, meses: int = 12) -> date | None:
	"""Sugestão quando o RH não informa: 12 meses depois do exame (o demissional não vence)."""
	if tipo == DEMISSIONAL:
		return None
	return adicionar_meses(data_exame, meses)
