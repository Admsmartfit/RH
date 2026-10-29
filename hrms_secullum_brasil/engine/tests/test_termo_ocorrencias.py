"""docs/PRD-termo-ocorrencias.md (TO-04): regularização proposta, resumo, prazos em dias úteis e reincidência."""

from datetime import date

from hrms_secullum_brasil.engine import termo_ocorrencias as to
from hrms_secullum_brasil.engine.cartao_edicao import ORIGINAL, Batida
from hrms_secullum_brasil.engine.sugestoes import COBRAVEIS, TIPOS, ContextoDia

PREVISTO = ((480, 720), (780, 1020))  # 08:00-12:00 13:00-17:00
FINADOS = {date(2026, 11, 2)}


def ctx(*minutos, previsto=PREVISTO, **kw):
	return ContextoDia(tuple(Batida(m, ORIGINAL, f"raw-{m}") for m in minutos), previsto, **kw)


def test_horista_sem_pausa_recebe_o_intervalo_do_termo_no_meio():
	# 02/10 do Marco: 09:18 às 13:34 sem pausa -> 11:26 às 11:41 (RH, 28/10/2026)
	p = to.propor_dia(["intrajornada"], ctx(558, 814, previsto=(), horista=True))
	assert p.horarios == (558, 686, 701, 814)
	assert p.texto == "Incluir o intervalo 11:26 às 11:41"
	assert p.intervalo == (686, 701)


def test_intervalo_curto_ja_registrado_fica_como_ciencia():
	p = to.propor_dia(["intrajornada"], ctx(558, 686, 700, 814, previsto=(), horista=True))
	assert p.horarios is None
	assert p.texto.startswith("Ciente: o intervalo que faltou é pago")


def test_batida_faltando_recebe_a_prevista():
	p = to.propor_dia(["marcacao_impar"], ctx(480, 720, 780))
	assert p.horarios == (480, 720, 780, 1020)
	assert p.texto == "Incluir a batida prevista 17:00"


def test_batida_faltando_e_sem_intervalo_no_mesmo_dia():
	# horista bateu só a entrada 09:00 (saída prevista 13:30): entra a saída e depois o intervalo do termo
	p = to.propor_dia(["intrajornada", "marcacao_impar"], ctx(540, previsto=((540, 810),), horista=True))
	assert p.horarios == (540, 675, 690, 810)
	assert p.texto == "Incluir a batida prevista 13:30; Incluir o intervalo 11:15 às 11:30"


def test_batida_repetida_e_desconsiderada():
	p = to.propor_dia(["marcacao_duplicada"], ctx(480, 482, 720, 780, 1020))
	assert p.horarios == (480, 720, 780, 1020)
	assert p.texto == "Desconsiderar a batida repetida 08:02"


def test_falta_e_atraso_nao_tem_horario_a_propor():
	falta = to.propor_dia(["falta"], ctx())
	assert (falta.horarios, falta.texto) == (
		None,
		"Ciente da falta: desconta o dia e o DSR da semana (Lei 605/49, art. 6º)",
	)
	atraso = to.propor_dia(["atraso"], ctx(500, 720, 780, 1020, banco_atraso=True))
	assert (atraso.horarios, atraso.texto) == (None, "Ciente: o atraso é debitado do banco de horas")


def test_tipo_sem_manter_vira_ciente_generico():
	assert to.propor_dia(["aula_nao_registrada"], ctx()).texto.startswith("Ciente da falta da aula")
	assert to._ciente("cref_vencido", ctx()) == to.CIENTE
	assert to.propor_dia([], ctx()).texto == to.CIENTE


def test_montar_itens_um_por_dia_e_so_os_tipos_do_termo():
	dias = [
		to.DiaTermo(
			date(2026, 10, 5), (("INC-2", "atraso"), ("INC-3", "configuracao_ausente")), ctx(500, 1020)
		),
		to.DiaTermo(date(2026, 10, 2), (("INC-1", "marcacao_impar"),), ctx(480, 720, 780)),
		to.DiaTermo(date(2026, 10, 6), (("INC-4", "sete_dias_seguidos"),), ctx()),
	]
	itens = to.montar_itens(dias)
	assert [(i.data.day, i.tipos, i.inconsistencias) for i in itens] == [
		(2, ("marcacao_impar",), ("INC-1",)),
		(5, ("atraso",), ("INC-2",)),
	]
	assert itens[0].marcacoes == (480, 720, 780)
	assert itens[0].proposta.horarios == (480, 720, 780, 1020)


def test_resumo_agrupa_os_dias_por_tipo_e_poe_os_informativos_no_fim():
	dias = [
		to.DiaTermo(date(2026, 10, 8), (("A", "intrajornada"),), ctx(558, 814, previsto=(), horista=True)),
		to.DiaTermo(date(2026, 10, 2), (("B", "intrajornada"), ("C", "atraso")), ctx(558, 814, previsto=())),
	]
	texto = to.resumo_ocorrencias(
		to.montar_itens(dias),
		[("descanso_semanal", None), ("descanso_semanal", None), ("falta", date(2026, 10, 1))],
	)
	assert texto == (
		"• Intervalo não registrado ou menor que o mínimo: 02/10, 08/10\n"
		"• Atraso ou saída antecipada: 02/10\n"
		"• Descanso semanal menor que 35 h"
	)
	assert to.texto_marcacoes((558, 814)) == "09:18 13:34"
	assert to.texto_marcacoes(()) == "sem batida"


def test_todo_tipo_do_termo_existe_nas_sugestoes_e_e_cobravel():
	assert set(to.NOMES) <= TIPOS
	assert set(to.NOMES) <= COBRAVEIS
	assert set(to.INFORMATIVOS) <= TIPOS


def test_prazo_em_dias_uteis_pula_fim_de_semana_e_feriado():
	emissao = date(2026, 10, 29)  # quinta
	assert to.somar_dias_uteis(emissao, 3, FINADOS) == date(2026, 11, 4)  # sex, (sáb, dom, Finados) ter, qua
	assert to.dias_uteis_entre(emissao, date(2026, 11, 2), FINADOS) == 1
	assert to.dias_uteis_entre(emissao, emissao, FINADOS) == 0


def test_cobranca_do_gerente_depois_do_prazo_e_rh_no_10o_dia_util():
	emissao = date(2026, 10, 29)
	assert to.avisos_do_dia(emissao, date(2026, 11, 4), FINADOS) == ()
	assert to.avisos_do_dia(emissao, date(2026, 11, 5), FINADOS) == (to.GERENTE,)
	assert to.avisos_do_dia(emissao, date(2026, 11, 7), FINADOS) == ()  # sábado
	assert to.avisos_do_dia(emissao, date(2026, 11, 2), FINADOS) == ()  # feriado
	# 10º dia útil: sex 30, ter 3 ... sex 13/11
	assert to.avisos_do_dia(emissao, date(2026, 11, 13), FINADOS) == (to.GERENTE, to.RH)
	assert to.avisos_do_dia(emissao, date(2026, 11, 16), FINADOS, rh_avisado=True) == (to.GERENTE,)
	assert to.avisos_do_dia(emissao, date(2026, 11, 16), FINADOS) == (to.GERENTE, to.RH)  # o job não rodou


def test_reincidencia_conta_os_termos_da_janela():
	hoje = date(2026, 10, 29)
	tres = [date(2026, 8, 10), date(2026, 9, 15), hoje]
	assert to.reincidente(tres, hoje)
	assert not to.reincidente([date(2026, 7, 1), date(2026, 9, 15), hoje], hoje)
	assert not to.reincidente(tres, hoje, limite=0)
	assert to.reincidente(tres[1:], hoje, limite=2, janela_dias=60)


def test_estatisticas_por_colaborador():
	d = date(2026, 10, 1)
	termos = [
		to.TermoResumo("A", to.CONFORME, d, date(2026, 10, 3), ("intrajornada",)),
		to.TermoResumo("A", to.COM_ALTERACAO, d, date(2026, 10, 7), ("intrajornada", "atraso")),
		to.TermoResumo("A", to.RECUSADO, d, date(2026, 10, 2), ("falta",)),
		to.TermoResumo("A", to.CANCELADO, d),
		to.TermoResumo("B", to.AGUARDANDO, d, None, ("marcacao_impar",)),
	]
	e = to.estatisticas(termos)
	assert e["A"] == {
		"emitidos": 4,
		"conforme": 1,
		"com_alteracao": 1,
		"recusados": 1,
		"cancelados": 1,
		"aguardando": 0,
		"dias_medio": 4.0,
		"taxa_recusa": 33.3,
		"tipos": "Intervalo não registrado ou menor que o mínimo (2), Atraso ou saída antecipada (1), Falta (dia sem batida) (1)",
	}
	assert (e["B"]["aguardando"], e["B"]["dias_medio"], e["B"]["taxa_recusa"]) == (1, None, None)
