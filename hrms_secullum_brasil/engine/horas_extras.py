"""Classificação do dia e distribuição das horas extras em faixas (PRD, 5.3 e 5.12)."""

from collections.abc import Iterable
from datetime import date

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.defaults_legais import FaixaHE
from hrms_secullum_brasil.engine.models import MinutosFaixa


def tipo_do_dia(dia: date, *, feriado: bool, folga: bool) -> str:
	if feriado:
		return d.TIPO_DIA_FERIADO
	if dia.weekday() == 6:
		return d.TIPO_DIA_DOMINGO
	if dia.weekday() == 5:
		return d.TIPO_DIA_SABADO
	return d.TIPO_DIA_FOLGA if folga else d.TIPO_DIA_UTIL


def distribuir_em_faixas(minutos: int, tipo_dia: str, faixas: Iterable[FaixaHE]) -> list[MinutosFaixa]:
	"""Divide os minutos de HE do dia entre as faixas do tipo de dia (ate_min = 0: sem limite)."""
	if minutos <= 0:
		return []
	do_tipo = sorted((f for f in faixas if f.tipo_dia == tipo_dia), key=lambda f: f.de_min)
	if not do_tipo:
		raise ValueError(f"Regra sem faixa de hora extra para {tipo_dia}.")
	resultado = []
	restante = minutos
	for faixa in do_tipo:
		capacidade = restante if faixa.ate_min == 0 else faixa.ate_min - faixa.de_min
		usados = min(restante, capacidade)
		if usados > 0:
			resultado.append(MinutosFaixa(tipo_dia, faixa.percentual, usados, faixa.vai_para_banco))
			restante -= usados
		if restante == 0:
			break
	return resultado
