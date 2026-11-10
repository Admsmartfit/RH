"""Sincronização programa → Secullum (docs/PRD-sincronizacao-secullum.md): travas, catálogo, quantidades e operações."""

import json
from datetime import date
from pathlib import Path

import pytest

from hrms_secullum_brasil.integrations.secullum import auditoria_horarios as au
from hrms_secullum_brasil.integrations.secullum import sincronizacao as s

HORARIOS = json.loads(
	(Path(__file__).parent.parent / "fixtures" / "reais" / "horarios.json").read_text(encoding="utf-8")
)
POR_NUMERO = {h["Numero"]: h for h in HORARIOS}


# ------------------------------------------------------------------ travas e catálogo


@pytest.mark.parametrize(
	"modo, caso, empresa, suspenso, pode",
	[
		(s.BLOQUEADO, True, True, False, False),
		(s.TESTE, False, True, False, False),
		(s.TESTE, True, True, False, True),
		(s.LIGADO, False, True, False, True),
		(s.LIGADO, False, False, False, False),  # empresa ainda não liberada (SS-9)
		(s.LIGADO, True, False, False, True),  # caso de teste aberto passa mesmo assim
		(s.LIGADO, True, True, True, False),  # suspenso vence tudo
		("qualquer", True, True, False, False),
	],
)
def test_pode_enviar(modo, caso, empresa, suspenso, pode):
	assert s.pode_enviar(modo, caso_aberto=caso, empresa_liberada=empresa, suspenso=suspenso)[0] is pode


def test_catalogo_cobre_todos_os_tipos_e_codigos_unicos():
	assert {c.tipo for c in s.CATALOGO} == set(s.TIPOS)
	assert len(s.POR_CODIGO) == len(s.CATALOGO)
	assert set(s.NOMES_TIPOS) == set(s.TIPOS)


def test_ligar_so_com_os_obrigatorios_aprovados():
	assert s.faltando_para_ligar(s.FOLGA_ESCALA, set()) == ["T-F1", "T-F2", "T-F3", "T-F4", "T-F5"]
	assert s.faltando_para_ligar(s.FOLGA_ESCALA, {"T-F1", "T-F2", "T-F3", "T-F4"}) == ["T-F5"]
	assert s.faltando_para_ligar(s.AFASTAMENTO, {"T-A1", "T-A2"}) == []


# ------------------------------------------------------------------ quantidades (SS-D8)


@pytest.mark.parametrize(
	"tipo, minutos, nome, enviado, arredondou",
	[
		("atestado", 90, "AT0130", 90, False),
		("falta", 180, "FT0300", 180, False),
		("atestado", 75, "AT0130", 90, True),  # 1h15 → para cima
		("falta", 75, "FT0100", 60, True),  # 1h15 → para baixo
		("falta", 20, "FT0030", 30, True),  # nunca abaixo de 0h30
		("atestado", 600, "AT0800", 480, True),  # teto de 8h
	],
)
def test_justificativa_do_horista(tipo, minutos, nome, enviado, arredondou):
	assert s.justificativa_horista(tipo, minutos) == (nome, enviado, arredondou)


def test_justificativas_por_quantidade_tem_valor_do_dia():
	todas = s.justificativas_por_quantidade()
	assert len(todas) == 32
	at = next(j for j in todas if j.nome == "AT0130")
	ft = next(j for j in todas if j.nome == "FT0130")
	assert (at.valor_dia, at.opcoes) == ("01:30", {"ajuste": True})
	assert (ft.valor_dia, ft.opcoes) == ("01:30", {"lancarComoHorasFalta": True})
	assert all(len(j.nome) <= 7 for j in s.todas_as_justificativas())
	assert s.quantidade_arredondada(0, para_cima=True) == 0


def test_corpo_mantem_o_que_existe_e_liga_a_regra():
	folga = next(j for j in s.LEGAIS if j.nome == "FOLGA")
	atual = {"NomeAbreviado": "FOLGA", "NomeCompleto": "FOLGA", "DescontarDsr": True}
	corpo = s.corpo_justificativa(folga, atual)
	assert corpo["calcularComoFolga"] is True and corpo["descontarDsr"] is True
	assert s.justificativa_diverge(folga, atual) == [
		"calcularComoFolga desligado",
		"naoPermitirFuncionariosUtilizar desligado",
	]
	assert (
		s.justificativa_diverge(
			folga, {**atual, "CalcularComoFolga": True, "NaoPermitirFuncionariosUtilizar": True}
		)
		== []
	)
	assert s.justificativa_diverge(folga, None) == ["não existe"]
	at = next(j for j in s.justificativas_por_quantidade() if j.nome == "AT0100")
	assert s.corpo_justificativa(at)["valorDia"] == "01:00"
	assert s.justificativa_diverge(at, {"Ajuste": True, "ValorDia": "02:00"}) == [
		"valor do dia 02:00 (esperado 01:00)"
	]


# ------------------------------------------------------------------ operações e conferência


def test_operacoes_do_dia_e_desfazer():
	dia = date(2026, 11, 10)
	ops = s.op_justificativa_dia("123", dia, "FOLGA", grupos=2)
	assert [o.corpo["Grupo"] for o in ops] == [1, 2]
	assert ops[0].descricao() == "POST CartaoPonto/Justificativa FOLGA"
	retira = s.op_retirar_justificativa_dia("123", dia, "escala mudou")
	assert retira[0].corpo["Coluna"] == "Entrada1" and retira[0].metodo == "DELETE"
	af = s.op_afastamento("123", dia, date(2026, 11, 12), "L-MATER", "Licença")
	assert af.corpo["justificativaNome"] == "L-MATER" and af.descricao().endswith("L-MATER")
	assert s.op_retirar_afastamento("123", dia, dia).params["funcionarioCpf"] == "123"
	est = s.op_estrutura("MATRIZ", ["1"], ["2", "3"])
	assert est.corpo["responsaveis"] == [{"cpf": "1"}] and len(est.corpo["funcionariosVinculados"]) == 2
	assert s.op_justificativa_cadastro(s.LEGAIS[0]).como_dict()["rota"] == "Justificativas"


def test_conferencia_no_cartao_e_afastamentos():
	assert s.justificativa_no_cartao({"Entrada1": "folga"}, "FOLGA")
	assert not s.justificativa_no_cartao(None, "FOLGA")
	assert (
		s.tem_batida({"Entrada1": "08:00"})
		and not s.tem_batida({"Entrada1": "FOLGA"})
		and not s.tem_batida(None)
	)
	afs = [{"Cpf": "123.4", "Inicio": "2026-11-10T00:00:00", "Fim": "2026-11-12T00:00:00"}]
	assert s.afastamento_presente(afs, "1234", date(2026, 11, 10), date(2026, 11, 12))
	assert not s.afastamento_presente(afs, "1234", date(2026, 11, 10), date(2026, 11, 13))


# ------------------------------------------------------------------ auditoria dos horários (SS-2)


def test_auditoria_de_um_horario_de_asg_real():
	achados = {a.codigo: a for a in au.auditar(POR_NUMERO[10], au.Esperado())}
	assert "H10-A58" in achados and "H10-TOL" in achados
	tol = achados["H10-TOL"]
	assert tol.passos[0].startswith("Secullum → Cadastros → Horários → clique no nº 10")
	assert {"campo": "Dias[DiaSemana=0].ToleranciaFalta", "valor": 5} in tol.esperados
	assert tol.passos[-1] == au.FECHAR


def test_auditoria_do_horista_nao_cobra_coluna_simples():
	codigos = {a.codigo for a in au.auditar(POR_NUMERO[2], au.Esperado(horista=True))}
	assert "H2-FX0" not in codigos and "H2-FX-8H" in codigos
	adiant = next(a for a in au.auditar(POR_NUMERO[2], au.Esperado(horista=True)) if a.codigo == "H2-ADIANT")
	assert adiant.bloqueia_fechamento is False


def test_auditoria_44h_folga_interjornada_dsr_e_noturno():
	h = json.loads(json.dumps(POR_NUMERO[10]))
	for d in h["Dias"][:5]:
		d.update({"Compensado": True, "Carga": 540})
	h["Extras"]["UsarInterjornada"] = False
	h["Opcoes"].update({"NaoCalcularNenhumaHoraNoturna": True, "QualquerMinutoAtrasadoComoFalta": True})
	h["Opcoes"]["LimiteMinimoDeFaltasNoDiaMinutos"] = 15
	h["Descanso"]["DescontarAtrasosEFaltasDSR"] = True
	next(g for g in h["FaixasExtras"] if g["DiaSemana"] == 4)["Faixas"][0]["Coluna"] = 0.0
	codigos = {a.codigo for a in au.auditar(h, au.Esperado())}
	assert {"H10-44H", "H10-INTER", "H10-NOT", "H10-ATRAS", "H10-LIMFA", "H10-DSR", "H10-FX4"} <= codigos
	assert au.semana_prevista(h) == 5 * 540


def test_verificacao_depois_do_ajuste():
	h = json.loads(json.dumps(POR_NUMERO[10]))
	tol = next(a for a in au.auditar(h, au.Esperado()) if a.codigo == "H10-TOL")
	assert au.divergencias(h, tol.esperados)
	for d in h["Dias"]:
		d["ToleranciaExtra"] = d["ToleranciaFalta"] = 5
	assert au.divergencias(h, tol.esperados) == []
	assert au.divergencias(None, tol.esperados) == ["horário não encontrado no Secullum"]
	assert au.ler(h, "FaixasExtras[DiaSemana=4].Faixas[0].Coluna") == 100.0
	assert au.ler(h, "Opcoes.Inexistente.X") is None
	assert au.ler(h, "Dias[9]") is None and au.ler(h, "Opcoes[0]") is None
	assert au.divergencias(h, [{"campo": "Extras.Interjornada", "valor": "11:00"}]) == []
	assert au.divergencias(h, [{"campo": "Opcoes.Carga", "valor": 5}])


def test_pausa_paga_vai_no_grupo_livre_sem_cobrir_batida():
	registro = {"Entrada1": "08:00", "Saida1": "12:52"}
	assert s.grupo_livre(registro) == 2
	assert s.grupo_livre(registro, 3) == 3
	assert s.grupo_livre({f"{t}{g}": "08:00" for g in range(1, 6) for t in ("Entrada", "Saida")}) is None
	assert s.grupo_livre(None) == 1

	op = s.op_justificativa_grupo("123", date(2026, 11, 3), s.PAUSA_PAGA.nome, 2).como_dict()
	assert op["corpo"] == {"Cpf": "123", "Data": "2026-11-03", "Grupo": 2, "Justificativa": "PAUSA15"}
	assert s.cabe_no_dia(registro, [op]) == (True, "")
	# o grupo 1 tem a batida: a pausa nunca vai nele
	no_um = s.op_justificativa_grupo("123", date(2026, 11, 3), "PAUSA15", 1).como_dict()
	assert s.cabe_no_dia(registro, [no_um]) == (False, "o grupo 1 do cartão já está ocupado")
	# as outras justificativas continuam proibidas em dia com batida
	outra = s.op_justificativa_grupo("123", date(2026, 11, 3), "ATESTAD", 2).como_dict()
	assert s.cabe_no_dia(registro, [outra]) == (False, "o colaborador bateu ponto no dia")
	assert s.cabe_no_dia({}, [outra]) == (True, "")
	assert s.PAUSA_PAGA in s.todas_as_justificativas()
	assert not s.POR_CODIGO["T-P1"].obrigatorio and not s.POR_CODIGO["T-P2"].obrigatorio


def test_fila_nunca_apaga_coluna_com_batida():
	registro = {"Entrada1": "08:02", "Saida1": "12:00", "Entrada2": "FOLGA", "Saida2": "FOLGA"}
	ops = [o.como_dict() for o in s.op_retirar_justificativa_dia("1", date(2026, 11, 1), "x", grupos=2)]
	vao, puladas = s.sem_apagar_batida(registro, ops)
	assert [o["corpo"]["Coluna"] for o in vao] == ["Entrada2"]
	assert puladas == ["Entrada1=08:02"]
	assert s.sem_apagar_batida(None, ops) == (ops, [])


def test_pausa_paga_completa_t_p3():
	# RH, 09/11/2026: a saída vai para a Saída 2, o intervalo entra no meio e a PAUSA15 no 3º par
	dia = date(2026, 10, 26)
	assert s.horario_da_pausa("16:55", "21:27") == ("19:03", "19:18")
	assert s.horario_da_pausa("22:00", "02:30") == ("00:07", "00:22")  # atravessa a meia-noite
	with pytest.raises(ValueError, match="curta"):
		s.horario_da_pausa("08:00", "09:00")
	ops, pausa = s.ops_pausa_paga("123", dia, {"Entrada1": "16:55", "Saida1": "21:27"})
	assert pausa == ("19:03", "19:18")
	assert [(o.rota, o.corpo.get("Coluna") or o.corpo.get("ColunaDestino")) for o in ops] == [
		("CartaoPonto/Troca", "Saida2"),
		("CartaoPonto/Manual", "Saida1"),
		("CartaoPonto/Manual", "Entrada2"),
		("CartaoPonto/Justificativa", None),
	]
	assert ops[-1].corpo["Grupo"] == 3 and ops[-1].corpo["Justificativa"] == "PAUSA15"
	assert all(o.corpo["Cpf"] == "123" for o in ops)
	# a fila aceita: o 3º par está livre e nada é apagado
	dicts = [o.como_dict() for o in ops]
	assert s.cabe_no_dia({"Entrada1": "16:55", "Saida1": "21:27"}, dicts) == (True, "")
	assert s.sem_apagar_batida({"Entrada1": "16:55", "Saida1": "21:27"}, dicts) == (dicts, [])
	# só dia com entrada e saída
	with pytest.raises(ValueError, match="só a entrada e a saída"):
		s.ops_pausa_paga(
			"123", dia, {"Entrada1": "08:00", "Saida1": "12:00", "Entrada2": "13:00", "Saida2": "17:00"}
		)
	with pytest.raises(ValueError, match="só a entrada e a saída"):
		s.ops_pausa_paga("123", dia, {"Entrada1": "ATESTAD", "Saida1": "ATESTAD"})


def test_desfazer_pausa_tira_so_o_intervalo():
	dia = date(2026, 10, 26)
	depois = {
		"Entrada1": "16:55",
		"Saida1": "19:03",
		"Entrada2": "19:18",
		"Saida2": "21:27",
		"Entrada3": "PAUSA15",
		"Saida3": "PAUSA15",
	}
	ops = s.ops_desfazer_pausa("123", dia, depois, ("19:03", "19:18"))
	dicts = [o.como_dict() for o in ops]
	assert [(d["metodo"], d["corpo"].get("Coluna") or d["corpo"].get("ColunaDestino")) for d in dicts] == [
		("DELETE", "Saida1"),
		("DELETE", "Entrada2"),
		("DELETE", "Entrada3"),
		("POST", "Saida1"),
	]
	assert [d.get("apagar_hora") for d in dicts] == ["19:03", "19:18", None, None]
	# a fila deixa apagar só as horas do intervalo; a batida do relógio continua protegida
	vao, puladas = s.sem_apagar_batida(depois, dicts)
	assert vao == dicts and puladas == []
	forjado = [{**dicts[0], "corpo": {**dicts[0]["corpo"], "Coluna": "Entrada1"}}]
	assert s.sem_apagar_batida(depois, forjado) == ([], ["Entrada1=16:55"])
	with pytest.raises(ValueError, match="não tem o intervalo"):
		s.ops_desfazer_pausa("123", dia, depois, ("19:03", "19:30"))
