"""Custo das quebras e do turno no cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-06). Python puro.

Valor-hora e percentuais pelo `engine/valoracao.BaseValoracao` (salário vigente ÷ divisor, percentuais da CCT e o
adicional de risco na base das horas extras, OJ 47). É uma **previsão**: o que é pago sai da apuração do ponto real
no fechamento (DE-3); o custo assumido fica só registrado na escala.

- Interjornada: minutos que faltaram para 11h como hora extra (OJ 355).
- Intervalo: minutos suprimidos com o adicional da indenização (art. 71, §4º).
- 7º dia seguido e feriado sem folga: as horas do dia em dobro (OJ 410 / Súmula 146) — custo = o adicional de 100%.
- Domingos, intervalo acima de 2h, indisponibilidade e antecedência: sem valor previsto, mas com risco (multa,
  tempo à disposição, reclamação); a explicação diz qual.
- Excesso e sobreposição bloqueiam: não há "manter com custo".
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine import adicional_risco as adicional
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import DiaEscala
from hrms_secullum_brasil.engine.models import RegraApuracao
from hrms_secullum_brasil.engine.noturno import minutos_fictos, minutos_noturnos
from hrms_secullum_brasil.engine.valoracao import BaseValoracao

CENTAVO = Decimal("0.01")
SESSENTA = Decimal(60)
CEM = Decimal(100)
DOBRO = 100  # % adicional do dia em dobro

RISCOS = {
	ev.DOMINGOS: "Sem valor previsto; risco de autuação (folga no domingo, art. 386 / Lei 10.101).",
	ev.INTERVALO_LONGO: "Sem valor previsto; o intervalo acima de 2h sem acordo pode virar tempo à disposição.",
	ev.INDISPONIBILIDADE: "Sem valor previsto; o colaborador informou que não pode.",
	ev.ANTECEDENCIA: "Sem valor previsto; mudança em cima da hora pode ser contestada (art. 468).",
}


def _reais(valor: Decimal) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class CustoQuebra:
	tipo: str
	valor: Decimal | None  # None = bloqueia (não dá para manter)
	explicacao: str


def valor_hora_extra(base: BaseValoracao) -> Decimal:
	"""Valor-hora com o adicional de risco (OJ 47), base das horas extras e das indenizações."""
	vh = base.valor_hora
	divisor = adicional.DIVISOR_HORISTA if base.horista else base.divisor
	if base.adicional_risco and divisor:
		vh += Decimal(base.adicional_risco) / divisor
	return vh


def _horas(minutos: int, valor_hora: Decimal, percentual: float | int) -> Decimal:
	return Decimal(int(minutos)) / SESSENTA * valor_hora * (Decimal(str(percentual)) / CEM)


def custo_quebra(quebra: ev.Quebra, base: BaseValoracao, minutos_do_dia: int = 0) -> CustoQuebra:
	"""Custo previsto de manter a quebra. `minutos_do_dia` = horas escaladas no dia (7º dia, feriado)."""
	vh = valor_hora_extra(base)
	if quebra.tipo in ev.BLOQUEANTES:
		return CustoQuebra(quebra.tipo, None, "Bloqueia: não pode ser mantida.")
	if quebra.tipo == ev.INTERJORNADA:
		valor = _horas(quebra.minutos, vh, 100 + base.percentual_interjornada)
		texto = f"{quebra.minutos} min de interjornada pagos como extra ({base.percentual_interjornada:g}%, OJ 355)."
	elif quebra.tipo == ev.INTERVALO:
		valor = _horas(quebra.minutos, vh, 100 + base.percentual_intrajornada)
		texto = f"{quebra.minutos} min de intervalo indenizados ({base.percentual_intrajornada:g}%, art. 71, §4º)."
	elif quebra.tipo in (ev.SETIMO_DIA, ev.FERIADO_SEM_FOLGA):
		valor = _horas(minutos_do_dia, vh, DOBRO)
		texto = f"{minutos_do_dia // 60}h{minutos_do_dia % 60:02d} do dia pagas em dobro (+100%)."
	else:
		return CustoQuebra(quebra.tipo, Decimal("0.00"), RISCOS.get(quebra.tipo, "Sem valor previsto."))
	return CustoQuebra(quebra.tipo, _reais(valor), texto)


def custos(quebras: Iterable[ev.Quebra], dias: Iterable[DiaEscala], base: BaseValoracao) -> list[CustoQuebra]:
	por_data = {dia.data: dia for dia in dias}
	return [custo_quebra(q, base, por_data[q.data].minutos if q.data in por_data else 0) for q in quebras]


def total(custos_: Iterable[CustoQuebra]) -> Decimal | None:
	"""Soma do que pode ser mantido; None se alguma quebra bloqueia."""
	valores = [c.valor for c in custos_]
	if any(v is None for v in valores):
		return None
	return _reais(sum(valores, Decimal("0")))


def custo_turno(
	dia: DiaEscala,
	base: BaseValoracao,
	regra: RegraApuracao | None = None,
	*,
	em_dobro: bool = False,
) -> Decimal:
	"""Custo previsto do turno: horas x valor-hora, adicional noturno (hora ficta) e, em feriado/7º dia, o dobro."""
	if not dia.trabalho:
		return Decimal("0.00")
	regra = regra or RegraApuracao()
	vh = base.valor_hora
	valor = _horas(dia.minutos, vh, 100)
	pares = [(p.inicio, p.fim) for p in dia.periodos]
	noturnos = minutos_noturnos(pares, regra)
	if noturnos:
		valor += _horas(
			minutos_fictos(noturnos, regra.minutos_hora_noturna),
			valor_hora_extra(base),
			base.percentual_noturno,
		)
	if em_dobro:
		valor += _horas(dia.minutos, valor_hora_extra(base), DOBRO)
	return _reais(valor)
