"""Conferência com o Secullum (pedido do RH, 30/10/2026). Python puro.

A coleta de hora em hora relê só os últimos dias; alguém pode mudar no Secullum um dia mais antigo do período ainda
aberto (batida manual, atestado, folga). Por isso:

- **conferência completa** a cada N dias (padrão 3), de madrugada: relê todo o período aberto (do dia seguinte ao
  último fechamento, no máximo `maximo` dias);
- **mudança retroativa**: o que mudou num dia com mais de `dias` dias vira aviso para o RH;
- **trava no fechamento**: só fecha com uma conferência recente do período, sem batida chegada depois dela e sem
  divergência de totais com o Secullum (ou com a divergência justificada).
"""

from collections.abc import Iterable
from datetime import date, datetime, timedelta

INTERVALO_DIAS = 3
MAXIMO_DIAS = 62
AVISO_RETROATIVO_DIAS = 3
VALIDADE_HORAS = 24
TOLERANCIA_MIN = 5


def inicio_da_conferencia(hoje: date, fechados: Iterable[date | None], maximo: int = MAXIMO_DIAS) -> date:
	"""O primeiro dia aberto entre as empresas do banco (o dia seguinte ao menor fechamento), limitado a `maximo` dias
	para trás. Empresa sem fechamento: os `maximo` dias."""
	limite = hoje - timedelta(days=maximo)
	fechados = list(fechados)
	if not fechados or any(f is None for f in fechados):
		return limite
	return max(limite, min(fechados) + timedelta(days=1))


def deve_conferir(ultima: datetime | None, agora: datetime, intervalo_dias: int = INTERVALO_DIAS) -> bool:
	if ultima is None:
		return True
	# meia hora de folga: a conferência de 3 dias atrás às 02:30 não pode escapar por minutos
	return agora - ultima >= timedelta(days=intervalo_dias) - timedelta(minutes=30)


def retroativa(data: date, hoje: date, dias: int = AVISO_RETROATIVO_DIAS) -> bool:
	"""A mudança é num dia com mais de `dias` dias (fora do que se espera da rotina do dia a dia)."""
	return data < hoje - timedelta(days=dias)


def divergentes(diferencas: Iterable[int], tolerancia: int = TOLERANCIA_MIN) -> int:
	return sum(1 for d in diferencas if abs(d) > tolerancia)


def bloqueios_do_fechamento(
	conferido_em: datetime | None,
	agora: datetime,
	divergencias: int,
	justificativa: str | None,
	batidas_depois: int = 0,
	validade_horas: int = VALIDADE_HORAS,
) -> list[str]:
	"""O que impede fechar o ponto do período, em linguagem de RH."""
	if conferido_em is None:
		return ['Falta a conferência com o Secullum: use o botão "Conferir com o Secullum".']
	saida = []
	if agora - conferido_em > timedelta(hours=validade_horas):
		saida.append(
			f"A conferência com o Secullum tem mais de {validade_horas}h ({conferido_em:%d/%m %H:%M}): confira de novo."
		)
	if batidas_depois:
		saida.append(
			f"Chegaram {batidas_depois} batida(s) do Secullum depois da conferência: confira de novo antes de fechar."
		)
	if divergencias and not (justificativa or "").strip():
		saida.append(
			f"Há {divergencias} divergência(s) de totais com o Secullum: corrija ou escreva a justificativa no fechamento."
		)
	return saida
