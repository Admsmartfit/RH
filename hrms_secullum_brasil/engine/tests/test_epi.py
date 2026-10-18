"""AJ-18: EPI e uniforme."""

from datetime import date, timedelta
from decimal import Decimal

from hrms_secullum_brasil.engine.epi import (
	ca_vencido,
	item_obrigatorio,
	saldo_com_colaborador,
	sem_primeira_entrega,
	troca_vencida,
)
from hrms_secullum_brasil.engine.valoracao import BaseValoracao, MinutosPeriodo, valorar

ADMISSAO = date(2026, 10, 1)


def test_aceite_asg_sem_luvas_em_5_dias_gera_alerta():
	assert not sem_primeira_entrega(ADMISSAO, ADMISSAO + timedelta(days=5), entregue=False)
	assert sem_primeira_entrega(ADMISSAO, ADMISSAO + timedelta(days=6), entregue=False)
	assert not sem_primeira_entrega(ADMISSAO, ADMISSAO + timedelta(days=6), entregue=True)
	assert not sem_primeira_entrega(None, ADMISSAO, entregue=False)


def test_aceite_luvas_com_troca_a_cada_30_dias_alertam_no_31_dia():
	entrega = date(2026, 10, 1)
	assert not troca_vencida(entrega, 30, entrega + timedelta(days=30))
	assert troca_vencida(entrega, 30, entrega + timedelta(days=31))
	assert not troca_vencida(entrega, 0, entrega + timedelta(days=400))


def test_ca_vencido():
	assert ca_vencido(date(2026, 10, 1), date(2026, 10, 2))
	assert not ca_vencido(date(2026, 10, 2), date(2026, 10, 2))
	assert not ca_vencido(None, date(2026, 10, 2))


def test_saldo_a_devolver():
	assert saldo_com_colaborador([("Entrega", 2), ("Entrega", 1), ("Devolução", 2)]) == 1


def test_item_por_cargo_ou_para_todos():
	assert item_obrigatorio([], "Recepcionista")
	assert item_obrigatorio(["ASG"], "ASG")
	assert not item_obrigatorio(["ASG"], "Recepcionista")


def test_desconto_so_por_dano_doloso():
	base = BaseValoracao(salario=Decimal("1800.00"), divisor=220)
	v = {lanc.codigo: lanc.valor for lanc in valorar(base, MinutosPeriodo(desconto_epi=Decimal("45.00")))}
	assert v == {"DESC_EPI": Decimal("45.00")}
	assert valorar(base, MinutosPeriodo()) == []
