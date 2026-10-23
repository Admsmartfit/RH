"""CP-04 (docs/PRD-cartao-ponto.md): explicação e sugestões por tipo de inconsistência."""

import json
from pathlib import Path

from hrms_secullum_brasil.engine.cartao_edicao import (
	ABONAR,
	DESCONSIDERAR,
	INCLUIR,
	ORIGINAL,
	Batida,
	ler_horario,
)
from hrms_secullum_brasil.engine.sugestoes import (
	DESK,
	EDITAR,
	JORNADA_FRAGMENTADA,
	MANTER,
	TIPOS,
	ContextoDia,
	orientar,
)

INCONSISTENCIA = (
	Path(__file__).resolve().parents[2]
	/ "apuracao"
	/ "doctype"
	/ "inconsistencia_de_ponto"
	/ "inconsistencia_de_ponto.json"
)
PREVISTO = ((480, 720), (780, 1020))


def batidas(*horas):
	return tuple(Batida(ler_horario(h), ORIGINAL, f"R{n}") for n, h in enumerate(horas))


def acoes(orientacao):
	return [s.acao for s in orientacao.sugestoes]


def test_todo_tipo_do_select_tem_orientacao():
	campos = json.loads(INCONSISTENCIA.read_text(encoding="utf-8"))["fields"]
	tipos = next(f for f in campos if f["fieldname"] == "tipo")["options"].split("\n")
	assert set(tipos) - TIPOS == set()
	for tipo in tipos:
		orientacao = orientar(tipo)
		assert orientacao.explicacao and orientacao.sugestoes, tipo


def test_tipo_desconhecido_sem_correcao_automatica():
	assert acoes(orientar("inexistente")) == [DESK]


def test_marcacao_impar_sugere_o_previsto():
	o = orientar("marcacao_impar", ContextoDia(batidas("08:00", "12:00", "13:00"), PREVISTO))
	primeira = o.sugestoes[0]
	assert (primeira.acao, primeira.minuto, primeira.rotulo) == (
		INCLUIR,
		1020,
		"Incluir 17:00 (horário previsto)",
	)
	assert o.sugestoes[-1].acao == DESCONSIDERAR
	assert "3 batidas" in o.explicacao


def test_marcacao_impar_sem_previsto():
	o = orientar("marcacao_impar", ContextoDia(batidas("08:00")))
	assert acoes(o) == [INCLUIR, DESCONSIDERAR]
	assert "1 batida " in o.explicacao


def test_duplicada_desconsidera_a_repetida():
	o = orientar("marcacao_duplicada", ContextoDia(batidas("08:00", "08:02", "12:00"), duplicidade_minutos=5))
	assert [(s.acao, s.referencia) for s in o.sugestoes] == [(DESCONSIDERAR, "R1")]


def test_duplicada_sem_achar_a_repetida():
	assert acoes(orientar("marcacao_duplicada")) == [EDITAR]


def test_falta():
	o = orientar("falta", ContextoDia(previsto=PREVISTO))
	assert acoes(o) == [ABONAR, INCLUIR, MANTER]
	assert "08:00 a 17:00" in o.sugestoes[1].rotulo
	assert acoes(orientar("falta")) == [ABONAR, MANTER]


def test_intrajornada_mostra_o_intervalo():
	o = orientar(
		"intrajornada", ContextoDia(batidas("08:00", "12:00", "12:40", "17:00"), intervalo_minimo=60)
	)
	assert "40 min (mínimo 60)" in o.explicacao


def test_intervalo_longo_oferece_a_jornada_fragmentada():
	assert acoes(orientar("intervalo_superior_2h"))[0] == JORNADA_FRAGMENTADA


def test_horista_sem_intervalo_sugere_o_termo():
	from hrms_secullum_brasil.engine.sugestoes import INCLUIR_INTERVALO

	o = orientar("intrajornada", ContextoDia(batidas("08:00", "12:12"), horista=True))
	assert o.sugestoes[0].acao == INCLUIR_INTERVALO
	assert o.explicacao == "Passou do limite da jornada sem registrar intervalo."
	assert INCLUIR_INTERVALO not in acoes(orientar("intrajornada", ContextoDia(batidas("08:00", "12:12"))))
