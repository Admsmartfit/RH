"""Modo de teste, ritmo e aceite do WhatsApp (docs/PRD-whatsapp-aceite-auditoria.md)."""

import json
from datetime import date, datetime
from pathlib import Path

from hrms_secullum_brasil.engine import aceite_whatsapp as a
from hrms_secullum_brasil.engine import whatsapp_envio as w

CONFIG = (
	Path(__file__).resolve().parents[2]
	/ "configuracao_ponto"
	/ "doctype"
	/ "configuracao_apuracao"
	/ "configuracao_apuracao.json"
)


def _assinar(token):
	return f"S{len(token)}"


def test_cabecalho_teste_so_final_do_numero():
	assert w.cabecalho_teste("Ana Souza", "Colaborador", "(27) 99876-1234") == (
		"[TESTE] para: Ana Souza — Colaborador (final 1234)"
	)
	assert w.cabecalho_teste(None, "RH", None) == "[TESTE] para: - — RH (final ----)"
	assert w.texto_de_teste("Oi", "[TESTE]") == "[TESTE]\n\nOi"


def test_marcar_links_de_teste():
	texto = (
		"Responda: https://p.com/ponto/resposta?t=abc.def\n"
		"Assine em https://p.com/ponto/assinar?token=x_y-z.w.\n"
		"Painel: https://p.com/ponto/cockpit"
	)
	marcado = w.marcar_links_de_teste(texto, _assinar)
	assert "https://p.com/ponto/resposta?t=abc.def&teste=S7\n" in marcado
	assert "https://p.com/ponto/assinar?token=x_y-z.w&teste=S7.\n" in marcado
	assert marcado.endswith("https://p.com/ponto/cockpit")
	assert w.marcar_links_de_teste("sem link", _assinar) == "sem link"
	assert w.marcar_links_de_teste(None, _assinar) == ""


def test_precisa_de_aceite_so_colaborador_em_ligado():
	assert w.precisa_de_aceite(w.LIGADO, "Colaborador")
	assert not w.precisa_de_aceite(w.LIGADO, "Colaborador", exigir=False)
	assert not w.precisa_de_aceite(w.LIGADO, "Gestor")
	assert not w.precisa_de_aceite(w.LIGADO, "RH")
	assert not w.precisa_de_aceite(w.TESTE, "Colaborador")
	assert not w.precisa_de_aceite(w.DESLIGADO, "Colaborador")


def test_proximo_horario_entre_minimo_e_maximo():
	agora = datetime(2026, 11, 5, 10, 0, 0)
	assert w.proximo_horario(None, agora, 20, 90, 0) == datetime(2026, 11, 5, 10, 0, 20)
	assert w.proximo_horario(None, agora, 20, 90, 1) == datetime(2026, 11, 5, 10, 1, 30)
	ultimo = datetime(2026, 11, 5, 10, 5, 0)
	assert w.proximo_horario(ultimo, agora, 20, 90, 0.5) == datetime(2026, 11, 5, 10, 5, 55)
	# a última da fila já passou: conta de agora
	assert w.proximo_horario(datetime(2026, 11, 5, 9, 0), agora, 20, 20, 0.3) == datetime(
		2026, 11, 5, 10, 0, 20
	)
	# mínimo e máximo trocados e negativos
	assert w.proximo_horario(None, agora, 90, 20, 0) == datetime(2026, 11, 5, 10, 0, 20)
	assert w.proximo_horario(None, agora, -5, 0, 0.7) == agora
	for i in range(11):
		saida = w.proximo_horario(None, agora, 20, 90, i / 10)
		assert 20 <= (saida - agora).total_seconds() <= 90


def test_proximo_horario_respeita_8h_20h():
	assert w.proximo_horario(None, datetime(2026, 11, 5, 19, 59, 50), 20, 90, 0) == datetime(
		2026, 11, 6, 8, 0
	)
	assert w.proximo_horario(None, datetime(2026, 11, 5, 6, 30), 20, 90, 0) == datetime(2026, 11, 5, 8, 0)
	assert w.dentro_do_horario(datetime(2026, 11, 5, 8, 0))
	assert not w.dentro_do_horario(datetime(2026, 11, 5, 20, 0))


def test_limite_do_dia_com_aquecimento():
	inicio = date(2026, 11, 1)
	assert w.limite_do_dia(date(2026, 11, 1), inicio) == 30
	assert w.limite_do_dia(date(2026, 11, 4), inicio) == 30 + 120 * 3 // 7
	assert w.limite_do_dia(date(2026, 11, 8), inicio) == 150
	assert w.limite_do_dia(date(2026, 10, 30), inicio) == 30
	assert w.limite_do_dia(date(2026, 11, 3), None) == 150
	assert w.limite_do_dia(date(2026, 11, 1), inicio, limite=10) == 10
	assert w.limite_do_dia(date(2026, 11, 3), inicio, limite=None) == 0
	dias = [w.limite_do_dia(date(2026, 11, d), inicio) for d in range(1, 9)]
	assert dias == sorted(dias)


def test_defaults_da_configuracao_batem_com_o_engine():
	campos = {f["fieldname"]: f for f in json.loads(CONFIG.read_text(encoding="utf-8"))["fields"]}
	assert campos["whatsapp_intervalo_min"]["default"] == str(w.INTERVALO_MIN_S)
	assert campos["whatsapp_intervalo_max"]["default"] == str(w.INTERVALO_MAX_S)
	assert campos["whatsapp_limite_dia"]["default"] == str(w.LIMITE_DIA)
	assert campos["whatsapp_nome_contato"]["default"] == a.NOME_CONTATO_PADRAO
	assert campos["whatsapp_envio"]["options"].split("\n") == list(w.MODOS)


# ------------------------------------------------------------------ aceite


def test_mascarar_celular():
	assert a.mascarar_celular("(27) 99876-1234") == "(27) *****-1234"
	assert a.mascarar_celular("5527998761234") == "(27) *****-1234"
	assert a.mascarar_celular("1234") == "*****-1234"
	assert a.mascarar_celular("") == ""
	assert a.mascarar_celular(None) == ""


def test_confere_cpf_e_nascimento():
	assert a.confere("123.456.789-09", "1990-05-02", "12345678909", date(1990, 5, 2))
	assert a.confere("12345678909", "02/05/1990", "123.456.789-09", "1990-05-02")
	assert not a.confere("12345678909", "03/05/1990", "12345678909", date(1990, 5, 2))
	assert not a.confere("12345678900", "1990-05-02", "12345678909", date(1990, 5, 2))
	assert not a.confere("", "1990-05-02", "", date(1990, 5, 2))
	assert not a.confere("12345678909", "data ruim", "12345678909", date(1990, 5, 2))
	assert not a.confere("12345678909", "1990-05-02", "12345678909", None)


def test_situacao_depois_da_mudanca_do_celular():
	assert a.situacao_depois_da_mudanca(a.ACEITO, "27998761234", "(27) 99876-1234") == a.ACEITO
	assert a.situacao_depois_da_mudanca(a.ACEITO, "27998761234", "27911112222") == a.PENDENTE
	assert a.situacao_depois_da_mudanca(a.REVOGADO, "27998761234", "27911112222") == a.REVOGADO
	assert a.situacao_depois_da_mudanca(None, None, "27911112222") == a.PENDENTE


def test_vcard_e_primeira_mensagem():
	cartao = a.vcard("Ponto ES Fitness", "+55 (27) 99999-0000")
	assert "FN:Ponto ES Fitness" in cartao
	assert "TEL;TYPE=CELL;waid=5527999990000:+5527999990000" in cartao
	assert cartao.startswith("BEGIN:VCARD\r\n") and cartao.endswith("END:VCARD\r\n")
	link = a.link_primeira_mensagem("+55 27 99999-0000", "JOÃO DA SILVA")
	assert link.startswith("https://wa.me/5527999990000?text=")
	assert "Jo%C3%A3o" in link and "%20" in link and " " not in link
	assert "colaborador" in a.link_primeira_mensagem("27999990000", "")
	assert a.primeiro_nome(None) == ""


def test_segura_pela_unidade_so_em_ligado_com_regra():
	from hrms_secullum_brasil.engine import whatsapp_envio as w

	assert w.segura_pela_unidade(w.LIGADO, "Regra X", False, "Vila Velha", ["Serra"])
	assert not w.segura_pela_unidade(w.LIGADO, "Regra X", False, "Serra", ["Serra"])
	assert w.segura_pela_unidade(w.LIGADO, "Regra X", False, None, ["Serra"])  # sem unidade, segura
	assert w.segura_pela_unidade(w.LIGADO, "Regra X", False, "Serra", [])  # nenhuma liberada
	assert not w.segura_pela_unidade(w.LIGADO, "Regra X", True, "Vila Velha", [])  # envio manual do RH
	assert not w.segura_pela_unidade(w.LIGADO, None, False, "Vila Velha", [])  # código, aviso sem regra
	assert not w.segura_pela_unidade(
		w.TESTE, "Regra X", False, "Vila Velha", []
	)  # modo Teste: número de teste
	assert not w.segura_pela_unidade(w.LIGADO, "Regra X", False, "Vila Velha", None)  # testes Frappe


def test_liberacoes_novas():
	from hrms_secullum_brasil.engine import whatsapp_envio as w

	assert w.liberacoes_novas(["A"], ["A", "B"]) == ["B"]
	assert w.liberacoes_novas(["A"], ["A", "B", "C"]) == ["B", "C"]
	assert w.liberacoes_novas(["A", "B"], ["A"]) == []
	assert w.liberacoes_novas([], ["", "B", "B"]) == ["B"]
