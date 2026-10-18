"""EPI e uniforme (AJ-18 do docs/PRD-alteracoes.md; CLT art. 166 e 456-A; NR-6).

Regras dos alertas diários: colaborador do cargo sem a primeira entrega depois de N dias da admissão, troca
vencida (última entrega + prazo de troca), CA vencido e itens a devolver na demissão. EPI e uniforme nunca
geram desconto em folha, salvo dano doloso com decisão registrada do RH.
"""

from collections.abc import Iterable
from datetime import date, timedelta

PRAZO_PRIMEIRA_ENTREGA_DIAS = 5


def sem_primeira_entrega(
	admissao: date | None, hoje: date, entregue: bool, prazo: int = PRAZO_PRIMEIRA_ENTREGA_DIAS
) -> bool:
	return not entregue and admissao is not None and hoje > admissao + timedelta(days=prazo)


def troca_vencida(ultima_entrega: date | None, prazo_troca_dias: int, hoje: date) -> bool:
	"""Troca a cada N dias: no dia N+1 depois da entrega, alerta (ex.: 30 dias → alerta no 31º dia)."""
	return bool(ultima_entrega and prazo_troca_dias) and hoje > ultima_entrega + timedelta(
		days=prazo_troca_dias
	)


def ca_vencido(validade: date | None, hoje: date) -> bool:
	return validade is not None and validade < hoje


def saldo_com_colaborador(movimentos: Iterable[tuple[str, int]]) -> int:
	"""Quantidade em poder do colaborador: entregas menos devoluções (("Entrega"|"Devolução", quantidade))."""
	return sum(qtd if tipo == "Entrega" else -qtd for tipo, qtd in movimentos)


def item_obrigatorio(cargos_do_item: Iterable[str], cargo: str | None) -> bool:
	"""Item sem cargos = vale para todos (ex.: uniforme); com cargos = só para esses cargos."""
	cargos = set(cargos_do_item)
	return not cargos or (cargo in cargos)
