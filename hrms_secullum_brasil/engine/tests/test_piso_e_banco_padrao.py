"""AJ-01 (piso por cargo) e AJ-05 (banco de horas padrão por cargo, com vigência no mês seguinte)."""

from datetime import date
from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.banco_horas import nova_vigencia_banco, participa_na_data
from hrms_secullum_brasil.engine.piso import HORISTA, MENSALISTA, aviso_piso, piso_proporcional

H44, H40 = 44 * 60, 40 * 60
PISO = Decimal("1650.00")


@pytest.mark.parametrize(
	("salario", "carga", "avisa"),
	[
		(Decimal("1600.00"), H44, True),  # recepcionista 44h com R$ 1.600,00: alerta
		(Decimal("1900.00"), H44, False),
		(Decimal("1500.00"), H40, False),  # 40h: piso proporcional de R$ 1.500,00
	],
)
def test_aj01_aceite(salario, carga, avisa):
	assert bool(aviso_piso(salario, MENSALISTA, PISO, H44, carga)) is avisa


def test_piso_proporcional():
	assert piso_proporcional(MENSALISTA, PISO, H44, H40) == Decimal("1500.00")
	assert piso_proporcional(MENSALISTA, PISO, H44, None) == PISO  # perfil sem carga: piso cheio


def test_horista_compara_o_valor_da_hora_sem_proporcao():
	assert piso_proporcional(HORISTA, Decimal("15.20"), H44, 20 * 60) == Decimal("15.20")
	assert aviso_piso(Decimal("16.50"), HORISTA, Decimal("15.20"), H44, 20 * 60) is None
	assert "por hora" in aviso_piso(Decimal("15.00"), HORISTA, Decimal("15.20"), H44, 20 * 60)


def test_sem_piso_cadastrado_nao_avisa():
	assert aviso_piso(Decimal("100.00"), MENSALISTA, Decimal("0"), H44, H44) is None


class TestBancoPadrao:
	HOJE = date(2026, 10, 15)

	def test_admissao_vale_desde_o_inicio(self):
		assert nova_vigencia_banco(False, None, True, self.HOJE, admissao=True) is None

	def test_mudanca_no_meio_do_mes_vale_no_mes_seguinte(self):
		desde = nova_vigencia_banco(True, None, False, self.HOJE)
		assert desde == date(2026, 11, 1)
		assert participa_na_data(False, desde, date(2026, 10, 31)) is True  # ainda participa em outubro
		assert participa_na_data(False, desde, date(2026, 11, 1)) is False

	def test_sem_mudanca_mantem_a_data(self):
		assert nova_vigencia_banco(True, date(2026, 9, 1), True, self.HOJE) == date(2026, 9, 1)

	def test_voltar_atras_antes_de_valer_desfaz_a_mudanca(self):
		assert nova_vigencia_banco(False, date(2026, 11, 1), True, self.HOJE) is None

	def test_nova_mudanca_depois_de_valer(self):
		assert nova_vigencia_banco(False, date(2026, 10, 1), True, self.HOJE) == date(2026, 11, 1)

	def test_dezembro_vira_janeiro(self):
		assert nova_vigencia_banco(True, None, False, date(2026, 12, 20)) == date(2027, 1, 1)

	def test_sem_data_vale_sempre(self):
		assert participa_na_data(True, None, date(2020, 1, 1)) is True
