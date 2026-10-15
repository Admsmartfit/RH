import pytest

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.defaults_legais import FaixaHE
from hrms_secullum_brasil.engine.validacoes_cadastro import (
	avisos_tolerancia,
	erros_banco_horas,
	erros_faixas_he,
	erros_intrajornada,
	erros_tolerancia,
)


class TestTolerancia:
	def test_padrao_legal_sem_avisos_nem_erros(self):
		assert erros_tolerancia(5, 10) == []
		assert avisos_tolerancia(5, 10) == []

	def test_aviso_por_marcacao(self):
		avisos = avisos_tolerancia(6, 10)
		assert len(avisos) == 1
		assert "marcação" in avisos[0]

	def test_aviso_diaria(self):
		avisos = avisos_tolerancia(5, 15)
		assert len(avisos) == 1
		assert "diária" in avisos[0]

	def test_dois_avisos(self):
		assert len(avisos_tolerancia(10, 20)) == 2

	def test_valores_menores_que_o_padrao_nao_geram_aviso(self):
		assert avisos_tolerancia(0, 0) == []

	@pytest.mark.parametrize(("marcacao", "diaria"), [(-1, 10), (5, -1)])
	def test_negativo_e_erro(self, marcacao, diaria):
		assert erros_tolerancia(marcacao, diaria)

	def test_diaria_menor_que_por_marcacao_e_erro(self):
		assert erros_tolerancia(5, 4)


def _faixas_com(*extras, sem=()):
	base = [f for f in d.FAIXAS_HE_PADRAO if f.tipo_dia not in sem]
	return [*base, *extras]


class TestFaixasHE:
	def test_padrao_valido(self):
		assert erros_faixas_he(d.FAIXAS_HE_PADRAO) == []

	def test_faixas_progressivas_validas(self):
		faixas = _faixas_com(FaixaHE("Útil", 0, 120, 50), FaixaHE("Útil", 120, 0, 70), sem=("Útil",))
		assert erros_faixas_he(faixas) == []

	def test_ordem_de_entrada_nao_importa(self):
		faixas = _faixas_com(FaixaHE("Útil", 120, 0, 70), FaixaHE("Útil", 0, 120, 50), sem=("Útil",))
		assert erros_faixas_he(faixas) == []

	def test_falta_tipo_de_dia(self):
		erros = erros_faixas_he(_faixas_com(sem=("Feriado",)))
		assert erros == ["Falta faixa de hora extra para o tipo de dia Feriado."]

	def test_percentual_abaixo_de_50(self):
		erros = erros_faixas_he(_faixas_com(FaixaHE("Sábado", 0, 0, 40), sem=("Sábado",)))
		assert len(erros) == 1
		assert "50%" in erros[0]

	def test_tipo_invalido(self):
		assert erros_faixas_he(_faixas_com(FaixaHE("Segunda", 0, 0, 50))) == [
			"Tipo de dia inválido: Segunda."
		]

	def test_buraco_entre_faixas(self):
		faixas = _faixas_com(FaixaHE("Útil", 0, 60, 50), FaixaHE("Útil", 120, 0, 70), sem=("Útil",))
		assert "começar em 60" in erros_faixas_he(faixas)[0]

	def test_nao_comeca_em_zero(self):
		faixas = _faixas_com(FaixaHE("Útil", 10, 0, 50), sem=("Útil",))
		assert "começar em 0" in erros_faixas_he(faixas)[0]

	def test_sem_limite_no_meio(self):
		faixas = _faixas_com(FaixaHE("Útil", 0, 0, 50), FaixaHE("Útil", 0, 120, 70), sem=("Útil",))
		assert erros_faixas_he(faixas)

	def test_ultima_faixa_com_limite(self):
		faixas = _faixas_com(FaixaHE("Útil", 0, 120, 50), sem=("Útil",))
		assert erros_faixas_he(faixas) == ["Útil: a última faixa deve ser sem limite (até = 0)."]

	def test_fim_menor_que_inicio(self):
		faixas = _faixas_com(FaixaHE("Útil", 0, 120, 50), FaixaHE("Útil", 120, 60, 70), sem=("Útil",))
		assert "fim menor ou igual" in erros_faixas_he(faixas)[0]


def _intra(**kw):
	params = {
		"jornada_sem_intervalo_ate": 240,
		"intervalo_curto": 15,
		"jornada_intervalo_curto_ate": 360,
		"intervalo_minimo": 60,
		"intervalo_maximo": 120,
		"permite_reducao": False,
		"intervalo_reduzido": 30,
	}
	params.update(kw)
	return erros_intrajornada(**params)


class TestIntrajornada:
	def test_padrao_valido(self):
		assert _intra() == []

	def test_reducao_a_30_valida(self):
		assert _intra(permite_reducao=True, intervalo_reduzido=30) == []

	def test_reducao_abaixo_de_30(self):
		assert "611-A" in _intra(permite_reducao=True, intervalo_reduzido=20)[0]

	def test_reducao_ignorada_quando_desligada(self):
		assert _intra(permite_reducao=False, intervalo_reduzido=10) == []

	def test_reduzido_maior_que_minimo(self):
		assert _intra(permite_reducao=True, intervalo_reduzido=90)

	def test_limites_nao_crescentes(self):
		assert _intra(jornada_sem_intervalo_ate=360)

	def test_intervalo_curto_zero(self):
		assert _intra(intervalo_curto=0)

	def test_maximo_menor_que_minimo(self):
		assert _intra(intervalo_maximo=30)


class TestBancoHoras:
	@pytest.mark.parametrize(
		("modalidade", "prazo"), [("Mensal", 1), ("Semestral", 6), ("Semestral", 3), ("Anual", 12)]
	)
	def test_prazos_validos(self, modalidade, prazo):
		assert erros_banco_horas(modalidade, prazo) == []

	@pytest.mark.parametrize(
		("modalidade", "prazo"), [("Mensal", 2), ("Semestral", 7), ("Anual", 13), ("Anual", 0)]
	)
	def test_prazo_fora_do_limite_legal(self, modalidade, prazo):
		assert erros_banco_horas(modalidade, prazo)

	def test_modalidade_invalida(self):
		assert erros_banco_horas("Bienal", 24) == ["Modalidade de banco de horas inválida: Bienal."]
