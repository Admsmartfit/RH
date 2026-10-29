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
	ABONO_PARCIAL,
	ATESTADO,
	COBRAR_WHATSAPP,
	DESK,
	EDITAR,
	FOLGA_COMPENSATORIA,
	INCLUIR_INTERVALO,
	JORNADA_COMPLETA,
	JORNADA_FRAGMENTADA,
	MANTER,
	TIPOS,
	ContextoDia,
	intervalo_do_termo,
	jornada_completa,
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
		"Inserir a batida prevista 17:00",
	)
	assert acoes(o)[-2:] == [DESCONSIDERAR, COBRAR_WHATSAPP]
	assert "3 batidas" in o.explicacao


def test_marcacao_impar_sem_previsto():
	o = orientar("marcacao_impar", ContextoDia(batidas("08:00")))
	assert acoes(o) == [INCLUIR, DESCONSIDERAR, COBRAR_WHATSAPP]
	assert "1 batida " in o.explicacao


def test_duplicada_desconsidera_a_repetida():
	o = orientar("marcacao_duplicada", ContextoDia(batidas("08:00", "08:02", "12:00"), duplicidade_minutos=5))
	assert [(s.acao, s.referencia) for s in o.sugestoes] == [(DESCONSIDERAR, "R1"), (COBRAR_WHATSAPP, None)]


def test_duplicada_sem_achar_a_repetida():
	assert acoes(orientar("marcacao_duplicada")) == [EDITAR, COBRAR_WHATSAPP]


def test_falta():
	o = orientar("falta", ContextoDia(previsto=PREVISTO))
	assert acoes(o) == [ABONAR, ATESTADO, JORNADA_COMPLETA, MANTER, COBRAR_WHATSAPP]
	completa = o.sugestoes[2]
	assert "08:00 a 17:00" in completa.rotulo
	assert completa.minutos == (480, 720, 780, 1020)
	assert acoes(orientar("falta")) == [ABONAR, ATESTADO, MANTER, COBRAR_WHATSAPP]


def test_manter_a_falta_diz_o_efeito_pelo_tipo_de_remuneracao():
	def manter(contexto):
		return next(s.rotulo for s in orientar("falta", contexto).sugestoes if s.acao == MANTER)

	assert "desconta o dia e o DSR da semana" in manter(ContextoDia())
	assert "nem o DSR proporcional" in manter(ContextoDia(horista=True, falta_horista_desconta_dsr=True))
	assert manter(ContextoDia(horista=True, falta_horista_desconta_dsr=False)).endswith("as horas do dia")


def test_atraso_e_he_dizem_se_vai_para_o_banco_ou_para_a_folha():
	def manter(tipo, contexto):
		return next(s.rotulo for s in orientar(tipo, contexto).sugestoes if s.acao == MANTER)

	assert acoes(orientar("atraso"))[0] == ABONO_PARCIAL
	assert manter("atraso", ContextoDia()).endswith("é descontado na folha")
	assert manter("atraso", ContextoDia(banco_atraso=True)).endswith("é debitado do banco de horas")
	assert "pagas como hora extra" in manter("he_acima_limite", ContextoDia())
	assert "vão para o banco de horas" in manter("he_acima_limite", ContextoDia(banco_he=True))


def test_quebras_de_descanso_oferecem_folga_compensatoria():
	for tipo in ("sete_dias_seguidos", "domingos_sem_folga", "descanso_semanal"):
		assert acoes(orientar(tipo))[-2:] == [FOLGA_COMPENSATORIA, COBRAR_WHATSAPP]
	assert FOLGA_COMPENSATORIA not in acoes(orientar("interjornada"))


def test_cobrar_pelo_whatsapp_em_toda_inconsistencia_do_ponto_do_dia():
	from hrms_secullum_brasil.engine.sugestoes import COBRAVEIS

	for tipo in COBRAVEIS:
		assert acoes(orientar(tipo)).count(COBRAR_WHATSAPP) == 1, tipo
	assert acoes(orientar("intrajornada", ContextoDia(batidas("07:44", "14:00"))))[-1] == COBRAR_WHATSAPP
	# cadastro, EPI, Secullum: não é com o colaborador
	assert COBRAR_WHATSAPP not in acoes(orientar("cref_vencido"))
	assert COBRAR_WHATSAPP not in acoes(orientar("erro_sync_cadastro"))


def test_jornada_completa_na_ordem():
	assert jornada_completa(((780, 1020), (480, 720))) == (480, 720, 780, 1020)
	assert jornada_completa(()) == ()


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


def test_intervalo_do_termo_no_meio_do_expediente():
	# exemplo do PDF do RH: 07:00 e 17:00 -> 12:00 às 13:00 (60 min da CCT)
	assert intervalo_do_termo([420, 1020], ContextoDia()) == (720, 780)
	# CCT com intervalo reduzido de 30 min
	assert intervalo_do_termo([420, 1020], ContextoDia(intervalo_minimo=30)) == (720, 750)
	# jornada de 4h a 6h: 15 min
	assert intervalo_do_termo([480, 780], ContextoDia()) == (630, 645)


def test_termo_so_no_dia_sem_nenhuma_pausa():
	# decisão do RH (28/10/2026): se já houve pausa, mesmo curta, não se sugere o termo
	assert intervalo_do_termo([480, 720, 730, 1020], ContextoDia()) is None  # pausa de 10 min
	assert intervalo_do_termo([720, 890, 904, 1019], ContextoDia(intervalo_curto=15)) is None  # 12/10: 14 min
	assert intervalo_do_termo([480, 720], ContextoDia()) is None  # até 4h: não precisa de pausa
	assert intervalo_do_termo([480, 720, 780], ContextoDia()) is None
	assert intervalo_do_termo([], ContextoDia()) is None


def test_horista_recebe_o_intervalo_do_termo_calculado():
	# 02/10 (Marco): 09:18-13:34 = 4h16 sem pausa -> 15 min no meio, 11:26 às 11:41
	o = orientar("intrajornada", ContextoDia(batidas("09:18", "13:34"), horista=True))
	termo = o.sugestoes[0]
	assert (termo.acao, termo.minutos) == (INCLUIR_INTERVALO, (686, 701))
	assert termo.rotulo.endswith("(11:26 às 11:41)")
	# 12/10: já houve pausa (14 min): sem a sugestão do termo
	ja_pausou = orientar(
		"intrajornada", ContextoDia(batidas("12:00", "14:50", "15:04", "16:59"), horista=True)
	)
	assert INCLUIR_INTERVALO not in acoes(ja_pausou)
