"""Vale-transporte: dias previstos, sugestão de carga, desconto em folha e travas sobre a média (AJ-06, parte 1).

Regras do docs/PRD-alteracoes.md (AJ-06):
- dias de trabalho do mês = dias da escala/perfil menos feriados e ausências já lançadas (férias, afastamentos);
- acerto do mês anterior: dias pagos e não trabalhados são abatidos da carga seguinte (Lei 7.418/1985, art. 1º);
- valor = dias x soma(quantidade diária x tarifa);
- desconto em folha = 6% do salário base, limitado ao valor do benefício (0% para estagiário);
- aumento sobre a média das cargas confirmadas: a partir de 15% pede motivo; acima de 30% trava até aprovação
  (queda não trava: decisão de 15/10/2026).

A geração das linhas do arquivo GVBus fica para quando o layout de 27 campos for confirmado (Etapa 9).
"""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.documentos import cpf_valido

CENTAVO = Decimal("0.01")
ALERTA_VARIACAO_PCT = 15  # a partir deste percentual: motivo obrigatório
TRAVA_VARIACAO_PCT = 30  # acima deste percentual: só com aprovação do Gestor de DP
MESES_MEDIA = 3  # cargas confirmadas consideradas na média (o PRD aceita de 3 a 6)

OK = "ok"
PEDE_MOTIVO = "pede_motivo"
TRAVADA = "travada"


def _reais(valor) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Tarifa:
	valor: Decimal
	quantidade_dia: int


def datas_do_mes(ano: int, mes: int, dias_da_semana: Iterable[int]) -> list[date]:
	"""Datas do mês nos dias da semana de trabalho (0 = segunda ... 6 = domingo)."""
	semana = set(dias_da_semana)
	_, ultimo = calendar.monthrange(ano, mes)
	return [date(ano, mes, dia) for dia in range(1, ultimo + 1) if date(ano, mes, dia).weekday() in semana]


def dias_previstos(
	datas_trabalho: Iterable[date], feriados: Iterable[date] = (), ausencias: Iterable[date] = ()
) -> int:
	fora = set(feriados) | set(ausencias)
	return sum(1 for dia in set(datas_trabalho) if dia not in fora)


def dias_a_carregar(previstos: int, acerto_mes_anterior: int = 0) -> int:
	"""Dias previstos menos os dias pagos e não trabalhados no mês anterior (nunca negativo)."""
	return max(0, previstos - max(0, acerto_mes_anterior))


def acerto_mes_anterior(datas_carregadas: Iterable[date], datas_trabalhadas: Iterable[date]) -> int:
	"""Dias da carga anterior em que a pessoa não trabalhou (falta, atestado, férias, afastamento): o VT é só
	para o deslocamento real (Lei 7.418/1985, art. 1º), então esses dias saem da carga seguinte."""
	trabalhadas = set(datas_trabalhadas)
	return sum(1 for dia in set(datas_carregadas) if dia not in trabalhadas)


def valor_por_dia(tarifas: Iterable[Tarifa]) -> Decimal:
	return sum((Decimal(t.valor) * t.quantidade_dia for t in tarifas), Decimal("0"))


def sugestao(dias: int, tarifas: Iterable[Tarifa]) -> Decimal:
	return _reais(valor_por_dia(tarifas) * max(0, dias))


def desconto_em_folha(
	salario_base: Decimal, valor_beneficio: Decimal, percentual: float = d.PERCENTUAL_DESCONTO_VT
) -> Decimal:
	"""Percentual do salário base, limitado ao valor do benefício (estagiário: percentual 0)."""
	teto = Decimal(salario_base) * Decimal(str(percentual)) / 100
	return _reais(min(teto, Decimal(valor_beneficio)))


def media_historica(cargas_confirmadas: Iterable[Decimal], meses: int = MESES_MEDIA) -> Decimal | None:
	"""Média das últimas `meses` cargas confirmadas (lista em ordem cronológica). Sem histórico: None."""
	ultimas = [Decimal(c) for c in cargas_confirmadas][-meses:] if meses > 0 else []
	if not ultimas:
		return None
	return sum(ultimas, Decimal("0")) / len(ultimas)


def variacao_percentual(valor: Decimal, media: Decimal | None) -> Decimal | None:
	if not media:
		return None
	return (Decimal(valor) - media) / media * 100


def avaliar_variacao(
	valor: Decimal,
	media: Decimal | None,
	alerta_pct: float = ALERTA_VARIACAO_PCT,
	trava_pct: float = TRAVA_VARIACAO_PCT,
) -> tuple[str, Decimal | None]:
	"""(situação, variação %). Sem histórico não há trava. Só o aumento trava; queda passa (decisão de 15/10/2026)."""
	variacao = variacao_percentual(valor, media)
	if variacao is None:
		return OK, None
	if variacao > Decimal(str(trava_pct)):
		return TRAVADA, variacao
	if variacao >= Decimal(str(alerta_pct)):
		return PEDE_MOTIVO, variacao
	return OK, variacao


def pendencias_cadastro(cpf: str | None, rg: str | None, cartao_gv: str | None) -> list[str]:
	"""Motivos para a linha ficar fora do arquivo (linha vermelha na tela)."""
	pendencias = []
	if not cpf or not cpf_valido(cpf):
		pendencias.append("CPF ausente ou inválido.")
	if not (rg or "").strip():
		pendencias.append("RG não cadastrado.")
	if not (cartao_gv or "").strip():
		pendencias.append("Número do CartãoGV não cadastrado.")
	return pendencias
