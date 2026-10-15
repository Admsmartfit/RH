"""Garante que os defaults dos JSONs de DocType batem com engine/defaults_legais.py."""

import json
from pathlib import Path

import pytest

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.validacoes_cadastro import erros_faixas_he

DOCTYPES = Path(__file__).resolve().parents[2] / "configuracao_ponto" / "doctype"


def _campos(doctype):
	caminho = DOCTYPES / doctype / f"{doctype}.json"
	return {f["fieldname"]: f for f in json.loads(caminho.read_text(encoding="utf-8"))["fields"]}


def _como_texto(valor):
	if isinstance(valor, bool):
		return "1" if valor else "0"
	return str(valor)


DEFAULTS_CCT = {
	"tolerancia_por_marcacao": d.TOLERANCIA_POR_MARCACAO_MIN,
	"tolerancia_diaria": d.TOLERANCIA_DIARIA_MIN,
	"computar_todo_tempo_ao_exceder": d.COMPUTAR_TODO_TEMPO_AO_EXCEDER,
	"compensar_atraso_com_he": d.COMPENSAR_ATRASO_COM_HE,
	"duplicidade_minutos": d.DUPLICIDADE_MIN,
	"limite_he_diaria": d.LIMITE_HE_DIARIA_MIN,
	"noturno_inicio": d.NOTURNO_INICIO,
	"noturno_fim": d.NOTURNO_FIM,
	"minutos_hora_noturna": d.MINUTOS_HORA_NOTURNA,
	"percentual_adicional_noturno": d.PERCENTUAL_ADICIONAL_NOTURNO,
	"prorrogacao_noturna": d.PRORROGACAO_NOTURNA,
	"jornada_sem_intervalo_ate": d.JORNADA_SEM_INTERVALO_ATE_MIN,
	"intervalo_curto": d.INTERVALO_CURTO_MIN,
	"jornada_intervalo_curto_ate": d.JORNADA_INTERVALO_CURTO_ATE_MIN,
	"intervalo_minimo": d.INTERVALO_MINIMO_MIN,
	"intervalo_maximo": d.INTERVALO_MAXIMO_MIN,
	"permite_reducao_intrajornada": d.PERMITE_REDUCAO_INTRAJORNADA,
	"intervalo_reduzido": d.INTERVALO_REDUZIDO_MIN,
	"percentual_indenizacao_intrajornada": d.PERCENTUAL_INDENIZACAO_INTRAJORNADA,
	"interjornada_minima": d.INTERJORNADA_MIN,
	"descanso_semanal_minimo": d.DESCANSO_SEMANAL_MIN,
	"dsr_perde_por_falta": d.DSR_PERDE_POR_FALTA,
	"dsr_perde_feriado_da_semana": d.DSR_PERDE_FERIADO_DA_SEMANA,
	"dsr_perde_por_atraso": d.DSR_PERDE_POR_ATRASO,
	"dsr_reflexo_he_noturno": d.DSR_REFLEXO_HE_NOTURNO,
	"banco_modalidade": d.BANCO_MODALIDADE_PADRAO,
	"banco_prazo_meses": d.PRAZO_MAXIMO_BANCO_MESES[d.BANCO_MODALIDADE_PADRAO],
	"banco_alerta_vencimento_dias": d.BANCO_ALERTA_VENCIMENTO_DIAS,
	"banco_permite_descontar_negativo": d.BANCO_PERMITE_DESCONTAR_SALDO_NEGATIVO,
	"banco_debita_atrasos": d.BANCO_DEBITA_ATRASOS,
	"semanas_mes_professor": d.SEMANAS_MES_PROFESSOR,
}


@pytest.mark.parametrize(("campo", "esperado"), DEFAULTS_CCT.items())
def test_default_da_regra_cct(campo, esperado):
	campos = _campos("regra_sindical_cct")
	assert campo in campos, f"campo {campo} ausente em regra_sindical_cct.json"
	assert campos[campo].get("default") == _como_texto(esperado)


def test_default_divisor_do_perfil():
	assert _campos("perfil_de_jornada")["divisor"]["default"] == str(d.DIVISOR_PADRAO)


def test_opcoes_de_tipo_de_dia_e_banco():
	assert _campos("faixa_hora_extra")["tipo_dia"]["options"].split("\n") == list(d.TIPOS_DIA)
	opcoes_banco = _campos("regra_sindical_cct")["banco_modalidade"]["options"].split("\n")
	assert opcoes_banco == list(d.PRAZO_MAXIMO_BANCO_MESES)


def test_faixas_padrao_sao_validas():
	assert erros_faixas_he(d.FAIXAS_HE_PADRAO) == []


TIPOS_DO_ENGINE = {
	"marcacao_impar",
	"marcacao_duplicada",
	"falta",
	"atraso",
	"he_acima_limite",
	"intrajornada",
	"interjornada",
	"intervalo_superior_2h",
	"banco_horas_rescisao",
	"aula_nao_registrada",
	"limite_aulas_excedido",
}


def test_tipos_de_inconsistencia_do_engine_existem_no_doctype():
	pasta = DOCTYPES.parent.parent / "apuracao" / "doctype" / "inconsistencia_de_ponto"
	campos = {
		f["fieldname"]: f
		for f in json.loads((pasta / "inconsistencia_de_ponto.json").read_text(encoding="utf-8"))["fields"]
	}
	assert set(campos["tipo"]["options"].split("\n")) >= TIPOS_DO_ENGINE


def test_faixas_padrao_do_banco_so_dia_util_e_sabado():
	assert {f.tipo_dia for f in d.FAIXAS_HE_PADRAO if f.vai_para_banco} == {
		d.TIPO_DIA_UTIL,
		d.TIPO_DIA_SABADO,
	}
