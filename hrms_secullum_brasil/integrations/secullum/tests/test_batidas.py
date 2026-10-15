from datetime import date, datetime

import pytest

from hrms_secullum_brasil.integrations.secullum.batidas import (
	RawExistente,
	Vinculo,
	escolher_vinculo,
	parse_fonte_dados,
	planejar_sincronizacao,
)


def registro(id_=1, hora="08:00", data="2026-10-13T00:00:00", tipo=0, **extra):
	return {
		"Id": id_,
		"FuncionarioId": "10",
		"FuncionarioPis": "170.33259.50-4",
		"FuncionarioCpf": "529.982.247-25",
		"EquipamentoId": 3,
		"Data": data,
		"DataInclusao": "2026-10-13T08:00:12",
		"Hora": hora,
		"Tipo": tipo,
		"Origem": 1,
		**extra,
	}


class TestParse:
	def test_campos(self):
		b = parse_fonte_dados(registro())
		assert b.origem_id == "1"
		assert b.cpf == "52998224725"
		assert b.pis == "17033259504"
		assert b.funcionario_id == "10"
		assert b.equipamento == "3"
		assert b.data_hora == datetime(2026, 10, 13, 8, 0)
		assert b.data == date(2026, 10, 13)
		assert b.tipo == "Original"
		assert b.origem == "RelogioPonto"
		assert b.data_inclusao == datetime(2026, 10, 13, 8, 0, 12)
		assert not b.desconsiderada

	@pytest.mark.parametrize("hora", ["08:00", "08:00:59", "08-00"])
	def test_formatos_de_hora_e_segundos_truncados(self, hora):
		assert parse_fonte_dados(registro(hora=hora)).data_hora == datetime(2026, 10, 13, 8, 0)

	def test_data_sem_horario(self):
		assert parse_fonte_dados(registro(data="2026-10-13")).data == date(2026, 10, 13)

	def test_sem_data_de_inclusao(self):
		assert parse_fonte_dados(registro(DataInclusao=None)).data_inclusao is None

	def test_desconsiderada(self):
		assert parse_fonte_dados(registro(tipo=3)).desconsiderada

	@pytest.mark.parametrize(
		("valor", "esperado"),
		[(1, "Manual"), ("2", "PreAssinalado"), ("Original", "Original"), (None, "Original")],
	)
	def test_rotulo_do_tipo(self, valor, esperado):
		assert parse_fonte_dados(registro(tipo=valor)).tipo == esperado

	def test_campos_opcionais_vazios(self):
		b = parse_fonte_dados(
			registro(FuncionarioCpf=None, EquipamentoId="", DataInclusao="lixo", Origem=None)
		)
		assert b.cpf == ""
		assert b.equipamento is None
		assert b.data_inclusao is None
		assert b.origem == "Desconhecido"

	@pytest.mark.parametrize(
		"alteracao", [{"Id": None}, {"Data": None}, {"Hora": ""}, {"Hora": "25:00"}, {"Data": "ontem"}]
	)
	def test_registro_invalido(self, alteracao):
		with pytest.raises(ValueError):
			parse_fonte_dados({**registro(), **alteracao})

	def test_hash_estavel_e_sensivel_a_mudancas(self):
		base = parse_fonte_dados(registro()).hash
		assert parse_fonte_dados(registro()).hash == base
		assert parse_fonte_dados(registro(hora="08:01")).hash != base
		assert parse_fonte_dados(registro(tipo=3)).hash != base

	def test_campos_desconhecidos_nao_entram_no_hash(self):
		assert parse_fonte_dados(registro(Novo="x")).hash == parse_fonte_dados(registro()).hash


def raw(nome, b):
	return RawExistente(nome, b.origem_id, b.hash)


class TestPlano:
	A = parse_fonte_dados(registro(1, "08:00"))
	B = parse_fonte_dados(registro(2, "12:00"))

	def test_primeira_coleta_insere_tudo(self):
		plano = planejar_sincronizacao([self.A, self.B], [])
		assert plano.inserir == [(self.A, None), (self.B, None)]
		assert plano.remover == []

	def test_segunda_coleta_nao_faz_nada(self):
		plano = planejar_sincronizacao([self.A, self.B], [raw("r1", self.A), raw("r2", self.B)])
		assert plano.inserir == []
		assert plano.remover == []
		assert plano.inalteradas == 2

	def test_registro_repetido_na_resposta(self):
		assert len(planejar_sincronizacao([self.A, self.A], []).inserir) == 1

	def test_batida_alterada_substitui_a_anterior(self):
		alterada = parse_fonte_dados(registro(1, "08:05"))
		plano = planejar_sincronizacao([alterada, self.B], [raw("r1", self.A), raw("r2", self.B)])
		assert plano.inserir == [(alterada, "r1")]
		assert plano.remover == []

	def test_batida_desconsiderada_substitui_a_anterior(self):
		desconsiderada = parse_fonte_dados(registro(1, "08:00", tipo=3))
		plano = planejar_sincronizacao([desconsiderada], [raw("r1", self.A)])
		assert plano.inserir == [(desconsiderada, "r1")]

	def test_batida_excluida_e_removida(self):
		plano = planejar_sincronizacao([self.B], [raw("r1", self.A), raw("r2", self.B)])
		assert plano.inserir == []
		assert plano.remover == ["r1"]

	def test_raws_ativas_duplicadas_do_mesmo_id_sao_limpas(self):
		antiga = RawExistente("r0", self.A.origem_id, "hash-velho")
		plano = planejar_sincronizacao([self.A], [antiga, raw("r1", self.A)])
		assert plano.inserir == []
		assert plano.remover == ["r0"]

		alterada = parse_fonte_dados(registro(1, "09:00"))
		plano = planejar_sincronizacao([alterada], [antiga, raw("r1", self.A)])
		assert plano.inserir == [(alterada, "r0")]
		assert plano.remover == ["r1"]


class TestVinculo:
	ANTIGO = Vinculo("EMP-1", date(2020, 1, 1), date(2025, 12, 31))
	NOVO = Vinculo("EMP-2", date(2026, 1, 1), None)

	def test_unico_candidato(self):
		assert escolher_vinculo([self.NOVO], date(2019, 1, 1)) == "EMP-2"

	def test_escolhe_o_ativo_na_data(self):
		assert escolher_vinculo([self.ANTIGO, self.NOVO], date(2025, 6, 1)) == "EMP-1"
		assert escolher_vinculo([self.ANTIGO, self.NOVO], date(2026, 6, 1)) == "EMP-2"

	def test_ambiguo_ou_nenhum(self):
		outro = Vinculo("EMP-3", None, None)
		assert escolher_vinculo([self.NOVO, outro], date(2026, 6, 1)) is None
		assert escolher_vinculo([self.ANTIGO, self.NOVO], date(2019, 1, 1)) is None
		assert escolher_vinculo([], date(2026, 6, 1)) is None
