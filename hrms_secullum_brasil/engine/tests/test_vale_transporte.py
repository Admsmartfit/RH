"""Vale-transporte: sugestão, desconto de 6%, trava por média e arquivo GVBus (AJ-06)."""

from datetime import date
from decimal import Decimal

from hrms_secullum_brasil.engine.vale_transporte import (
	ALERTA,
	OK,
	TOTAL_CAMPOS,
	TRAVA,
	LinhaGVBus,
	Tarifa,
	campos_da_linha,
	desconto_em_folha,
	dias_de_trabalho,
	erros_da_linha,
	gerar_arquivo,
	media_historica,
	nivel_trava,
	nome_arquivo,
	sugerir,
	variacao_percentual,
)

SEG_A_SEX = range(5)
PASSAGEM = (Tarifa("A", Decimal("5.00"), 2),)
FERIADO_OUTUBRO = {date(2026, 10, 12)}
CPF = "52998224725"


def test_dias_de_trabalho_5x2_em_outubro_de_2026():
	assert len(dias_de_trabalho(2026, 10, SEG_A_SEX)) == 22


def test_troca_de_escala_prevalece_sobre_o_perfil():
	dias = dias_de_trabalho(2026, 10, SEG_A_SEX, trocas={date(2026, 10, 18): True, date(2026, 10, 21): False})
	assert date(2026, 10, 18) in dias and date(2026, 10, 21) not in dias
	assert len(dias) == 22


def test_sugestao_desconta_feriado():
	s = sugerir(dias_de_trabalho(2026, 10, SEG_A_SEX), PASSAGEM, feriados=FERIADO_OUTUBRO)
	assert (s.dias_previstos, s.dias, s.valor) == (21, 21, Decimal("210.00"))


def test_sugestao_abate_acerto_do_mes_anterior_e_abono():
	dias = dias_de_trabalho(2026, 10, SEG_A_SEX)
	s = sugerir(dias, PASSAGEM, feriados=FERIADO_OUTUBRO, acerto=1)
	assert (s.dias, s.valor) == (20, Decimal("200.00"))
	s = sugerir(dias, PASSAGEM, feriados=FERIADO_OUTUBRO, acerto=1, abono=2)
	assert s.dias == 18


def test_sugestao_desconta_ausencias_e_nunca_fica_negativa():
	dias = dias_de_trabalho(2026, 10, SEG_A_SEX)
	ferias = {date(2026, 10, d) for d in range(1, 32)}
	assert sugerir(dias, PASSAGEM, ausencias=ferias, acerto=3).dias == 0


def test_sugestao_com_duas_tarifas():
	tarifas = (Tarifa("A", Decimal("5.00"), 2), Tarifa("B", Decimal("3.40"), 1))
	assert sugerir([date(2026, 10, 1)], tarifas).valor == Decimal("13.40")


def test_desconto_de_6_por_cento_limitado_ao_beneficio():
	assert desconto_em_folha(Decimal("1650.00"), Decimal("200.00")) == Decimal("99.00")
	assert desconto_em_folha(Decimal("1650.00"), Decimal("80.00")) == Decimal("80.00")


def test_media_historica_usa_os_ultimos_meses():
	assert media_historica([Decimal("500"), Decimal("190"), Decimal("200"), Decimal("210")]) == Decimal(
		"200.00"
	)
	assert media_historica([Decimal("100"), Decimal("300")], meses=6) == Decimal("200.00")
	assert media_historica([]) is None
	assert media_historica([Decimal("100")], meses=0) is None


def test_niveis_de_trava():
	media = Decimal("200.00")
	assert nivel_trava(variacao_percentual(Decimal("220"), media)) == OK  # 10%
	assert nivel_trava(variacao_percentual(Decimal("230"), media)) == ALERTA  # 15%
	assert nivel_trava(variacao_percentual(Decimal("240"), media)) == ALERTA  # 20%
	assert nivel_trava(variacao_percentual(Decimal("260"), media)) == ALERTA  # 30%
	assert nivel_trava(variacao_percentual(Decimal("270"), media)) == TRAVA  # 35%
	assert nivel_trava(variacao_percentual(Decimal("150"), media)) == OK  # queda não trava


def test_sem_historico_nao_trava():
	assert variacao_percentual(Decimal("999"), None) is None
	assert nivel_trava(None) == OK


def linha(**campos):
	dados = {
		"nome": "João da Silva",
		"matricula": "1001",
		"cpf": "529.982.247-25",
		"rg": "1234567 ES",
		"cartao": "01234567890123",
		"cargo": "Recepcionista",
		"admissao": date(2022, 3, 15),
		"endereco": "Rua da Praia; 100",
		"bairro": "Centro",
		"municipio": "Vila Velha",
		"cep": "29100-000",
		"telefone": "(27) 99999-8888",
		"setor": "Recepção",
		"tarifas": PASSAGEM,
	}
	dados.update(campos)
	return LinhaGVBus(**dados)


def test_linha_no_layout_de_27_campos():
	campos = campos_da_linha(linha())
	assert len(campos) == TOTAL_CAMPOS
	assert campos[:14] == [
		"JOÃO DA SILVA",
		"1001",
		"RECEPCIONISTA",
		"15/03/2022",
		"RUA DA PRAIA 100",
		"CENTRO",
		"VILA VELHA",
		"29100000",
		"27999998888",
		"RECEPÇÃO",
		"A",
		"02",
		"",
		"",
	]
	assert campos[14:23] == [""] * 9
	assert campos[23:] == ["", "01234567890123", CPF, "1234567 ES"]


def test_segunda_tarifa_e_data_de_inatividade():
	campos = campos_da_linha(
		linha(
			tarifas=(Tarifa("A", Decimal("5"), 2), Tarifa("B", Decimal("3"), 1)),
			inativo_desde=date(2026, 10, 20),
		)
	)
	assert campos[10:14] == ["A", "02", "B", "01"]
	assert campos[23] == "20/10/2026"


def test_erros_bloqueiam_a_linha():
	assert erros_da_linha(linha()) == []
	assert erros_da_linha(linha(cpf="111.111.111-11")) == ["ERR-01: CPF ausente ou inválido."]
	assert erros_da_linha(linha(rg=" ")) == ["ERR-01: RG ausente."]
	assert erros_da_linha(linha(cartao="")) == ["ERR-02: número do CartãoGV não cadastrado."]
	assert len(erros_da_linha(linha(nome="", matricula="", tarifas=PASSAGEM * 3))) == 3


def test_arquivo_iso_8859_1_crlf_sem_linhas_com_erro():
	conteudo = gerar_arquivo([linha(), linha(nome="Maria", cartao="")])
	texto = conteudo.decode("iso-8859-1")
	assert texto.count("\r\n") == 1 and texto.endswith("\r\n")
	assert texto.startswith("JOÃO DA SILVA;1001;")
	assert texto.rstrip("\r\n").count(";") == TOTAL_CAMPOS - 1
	assert ";A;02;;;;;;;;;;;;;01234567890123;" in texto


def test_nome_do_arquivo():
	assert (
		nome_arquivo("23.620.822/0002-51", date(2026, 11, 1), date(2026, 10, 15))
		== "GVBUS_CARGA_23620822000251_202611_15.txt"
	)
