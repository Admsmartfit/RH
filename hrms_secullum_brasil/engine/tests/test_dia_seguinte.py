"""WhatsApp do dia seguinte (docs/PRD-whatsapp-dia-seguinte.md): regras puras."""

from datetime import date, datetime

import pytest

from hrms_secullum_brasil.engine import dia_seguinte as d1

AGORA = datetime(2026, 11, 4, 9, 0)


def fatos(**campos):
	return d1.FatosDoDia(**{"tipo": "marcacao_impar", "aberta_em": datetime(2026, 11, 4, 1, 0), **campos})


def test_pendencia_normal_pode_sair():
	assert d1.bloqueio(fatos(), AGORA) is None


@pytest.mark.parametrize(
	("campos", "motivo"),
	[
		({"tipo": "aso_vencido"}, d1.TIPO_FORA),
		({"ativo": False}, d1.INATIVO),
		({"periodo_fechado": True}, d1.FECHADO),
		({"no_termo": True}, d1.NO_TERMO),
		({"ja_respondido": True}, d1.JA_RESPONDIDO),
		({"ja_cobrado": True}, d1.JA_COBRADO),
		({"ausencia_justificada": True}, d1.AUSENCIA),
		({"tipo": "falta", "tem_jornada": False}, d1.SEM_JORNADA),
		({"tipo": "atraso", "tem_jornada": False}, d1.SEM_JORNADA),
		({"tipo": "falta", "perfil_tipo": "Escala", "escala_publicada": False}, d1.SEM_ESCALA),
		({"tipo": "falta", "perfil_tipo": "Horista", "escala_publicada": False}, d1.SEM_ESCALA),
		({"aberta_em": datetime(2026, 11, 4, 8, 0)}, d1.RECENTE),
	],
)
def test_filtros_de_seguranca(campos, motivo):
	assert d1.bloqueio(fatos(**campos), AGORA) == motivo


def test_falta_de_perfil_fixo_ou_com_escala_publicada_sai():
	assert d1.bloqueio(fatos(tipo="falta", perfil_tipo="Fixa"), AGORA) is None
	assert d1.bloqueio(fatos(tipo="falta", perfil_tipo="Escala", escala_publicada=True), AGORA) is None


def test_batida_esquecida_em_feriado_trabalhado_ainda_avisa():
	assert d1.bloqueio(fatos(tem_jornada=False), AGORA) is None


def test_sem_espera_e_sem_data_de_abertura():
	recente = fatos(aberta_em=datetime(2026, 11, 4, 8, 59))
	assert d1.bloqueio(recente, AGORA, horas_estabilizar=0) is None
	assert d1.bloqueio(fatos(aberta_em=None), AGORA) is None


def test_textos_por_tipo_e_varios_no_dia():
	assert "{batidas}" in d1.texto_padrao("marcacao_impar") and "{link}" in d1.texto_padrao("marcacao_impar")
	assert d1.texto_padrao("interjornada") == d1.TEXTO_COLABORADOR
	assert "Se fez a pausa" in d1.texto_padrao("intrajornada")
	assert "sem autorização" in d1.texto_padrao("excesso_jornada_nao_autorizada")
	assert (
		"excesso_jornada_nao_autorizada" in d1.SEMPRE_CONFERIR
		and "excesso_jornada_nao_autorizada" in d1.TIPOS_D1
	)
	assert d1.descricao_dos_tipos(["falta"]) == d1.explicacao("falta")
	varios = d1.descricao_dos_tipos(["atraso", "intrajornada", "atraso"])
	assert varios.count("•") == 2
	assert "0 batidas" not in d1.descricao_dos_tipos(["marcacao_impar"])


def test_link_entra_no_fim_quando_o_texto_nao_tem():
	assert d1.com_link("Oi {primeiro_nome}") == "Oi {primeiro_nome}\nResponda pelo link (é só seu): {link}"
	assert d1.com_link("Oi {link}") == "Oi {link}"


def test_liberacao_gradual():
	assert d1.pode_ir_para_producao(19) == (False, 1)
	assert d1.pode_ir_para_producao(20) == (True, 0)
	assert d1.pode_ir_para_producao(0, minimo=0) == (True, 0)


def test_volta_para_teste_com_descartes_recentes():
	recentes = [datetime(2026, 11, 1), datetime(2026, 11, 3), datetime(2026, 11, 4)]
	assert d1.deve_voltar_para_teste(recentes, AGORA)
	assert not d1.deve_voltar_para_teste([datetime(2026, 10, 1), *recentes[1:]], AGORA)
	assert not d1.deve_voltar_para_teste(recentes, AGORA, limite=0)


def test_prazo_da_resposta_em_dias_uteis():
	# enviada na sexta 06/11: prazo terça 10/11 (sábado e domingo não contam)
	sexta = date(2026, 11, 6)
	assert d1.prazo_da_resposta(sexta, set()) == date(2026, 11, 10)
	assert not d1.sem_resposta(sexta, date(2026, 11, 10), set())
	assert d1.sem_resposta(sexta, date(2026, 11, 11), set())
	assert d1.prazo_da_resposta(sexta, {date(2026, 11, 9)}) == date(2026, 11, 11)  # feriado na segunda


def test_resumo_da_resposta_para_o_gestor():
	dias = [
		{"data": "03/11", "incluidos": ["17:00"]},
		{"data": "04/11", "explicacao": "treinamento externo"},
		{"data": "05/11", "nao_reconhece": True},
		{"data": "06/11", "retirados": ["12:00"], "incluidos": ["12:10"]},
	]
	assert d1.resumo_da_resposta(dias) == (
		"incluiu 17:00 em 03/11; explicou 04/11 (treinamento externo); não reconhece 05/11; "
		"incluiu 12:10 e tirou 12:00 em 06/11"
	)
	assert d1.resumo_da_resposta([{"data": "03/11"}]) == "confirmou os horários"


def test_selo_whatsapp_na_central():
	enviada, prazo = date(2026, 11, 4), date(2026, 11, 6)
	assert d1.selo_whatsapp(None) is None
	assert d1.selo_whatsapp("Enviada", enviada, prazo=prazo) == {
		"texto": "WhatsApp 04/11 · aguardando resposta até 06/11",
		"tom": d1.NEUTRO,
	}
	assert d1.selo_whatsapp("Lida", enviada)["texto"] == "WhatsApp 04/11 · lido · aguardando resposta"
	assert d1.selo_whatsapp("Entregue", enviada, sem_resposta=True)["tom"] == d1.RUIM
	assert d1.selo_whatsapp("Barrada", filtro="dia sem escala")["texto"] == "WhatsApp barrado: dia sem escala"
	assert d1.selo_whatsapp("Barrada")["texto"] == "WhatsApp barrado: filtro de segurança"
	assert d1.selo_whatsapp("Aguardando envio manual")["tom"] == d1.ATENCAO
	assert d1.selo_whatsapp("Descartada")["texto"] == "WhatsApp descartado"
	assert d1.selo_whatsapp("Erro")["texto"] == "WhatsApp: erro"
	assert d1.selo_whatsapp("Enviada", resposta="Aguardando aprovação")["texto"] == "Respondeu — aprovar"
	assert d1.selo_whatsapp("Enviada", resposta="Aprovada")["tom"] == d1.BOM
	assert d1.selo_whatsapp("Enviada", resposta="Recusada")["tom"] == d1.RUIM


def test_com_o_colaborador():
	assert d1.com_o_colaborador("Enviada", False, False)
	assert not d1.com_o_colaborador("Enviada", True, False)  # prazo vencido: volta para o RH
	assert not d1.com_o_colaborador("Lida", False, True)  # respondeu: o RH aprova
	assert not d1.com_o_colaborador("Aguardando envio manual", False, False)


def test_origem_e_resumo_das_correcoes():
	assert d1.origem_da_correcao(["Informado pelo colaborador no WhatsApp em 04/11 (RWP-1)"]) == "colaborador"
	assert d1.origem_da_correcao(["Esqueceu de bater o ponto", None]) == "rh"
	resumo = d1.resumo_das_correcoes(
		[
			None,
			{"situacao": "Aprovado", "origem": "colaborador", "secullum": "Enviado"},
			{"situacao": "Aprovado", "origem": "rh", "secullum": "Erro"},
			{"situacao": "Aguardando aprovação", "origem": "colaborador"},
			{"situacao": "Recusado"},
		]
	)
	assert resumo == {"colaborador": 1, "rh": 1, "aguardando": 1, "recusados": 1, "erro_secullum": 1}


def test_pode_cobrar_pelo_cartao():
	sexta = date(2026, 11, 6)
	assert d1.pode_cobrar(None, None, sexta, set()) == (True, None)
	assert d1.pode_cobrar("Barrada", None, sexta, set()) == (True, None)
	assert d1.pode_cobrar("Erro", None, sexta, set()) == (True, None)
	pode, motivo = d1.pode_cobrar("Lida", sexta, date(2026, 11, 9), set())
	assert not pode and motivo.endswith("aguardando resposta até 10/11.")
	assert d1.pode_cobrar("Lida", sexta, date(2026, 11, 11), set()) == (True, None)  # passou o prazo
	assert d1.pode_cobrar("Enviada", sexta, sexta, set(), sem_resposta_marcado=True) == (True, None)
	assert not d1.pode_cobrar("Enviada", sexta, sexta, set(), respondeu=True)[0]
	assert "fila de conferência" in d1.pode_cobrar("Aguardando envio manual", None, sexta, set())[1]


def test_pelo_whatsapp_conta_as_pausas_incluidas():
	assert d1.pausas_incluidas(["08:00", "12:15"], ["08:00", "10:00", "10:15", "12:15"]) == 1
	assert (
		d1.pausas_incluidas(["08:00", "12:15"], ["08:00", "09:00", "09:10", "10:00", "10:10", "12:15"]) == 2
	)
	assert (
		d1.pausas_incluidas(["08:00", "10:00", "10:15"], ["08:00", "10:00", "10:15", "12:15"]) == 0
	)  # só a saída
	assert d1.pausas_incluidas(["08:00"], ["08:00", "12:00"]) == 0


def test_mensagem_de_varias_pendencias_no_texto_do_rh():
	# pedido do RH (08/11/2026): o texto exato, sem orientação interna
	from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

	tipos = ["intrajornada", "excesso_jornada_nao_autorizada"]
	texto = montar_mensagem(
		d1.TEXTO_VARIOS,
		primeiro_nome="Enzo",
		data="26/10",
		dia_semana="segunda-feira",
		descricao=d1.descricao_dos_tipos(tipos),
		quantidade=d1.quantidade(tipos),
		link="{link}",
	)
	assert texto == (
		"Olá, Enzo!\n\n"
		"Identificamos duas pendências no seu registro de ponto de 26/10 (segunda-feira):\n"
		"• Intervalo de almoço inferior ao tempo mínimo estabelecido.\n"
		"• Registro de horas além da jornada contratada sem autorização prévia (mesmo considerando tolerâncias e "
		"pausas).\n\n"
		"Para justificar o ocorrido ou solicitar a correção, acesse o seu link exclusivo: {link}"
	)
	assert d1.quantidade(["falta"]) == "uma"
	assert d1.quantidade(list("abcdefghijkl")) == "12"


def test_nenhum_texto_ao_colaborador_tem_orientacao_interna():
	# "nunca coloque o texto pausa paga" (RH, 08/11/2026): nem as instruções do balão do cartão
	textos = [d1.TEXTO_COLABORADOR, d1.TEXTO_VARIOS, *d1.TEXTOS_COLABORADOR.values()]
	textos += [d1.explicacao(t) for t in d1.DESCRICOES_COLABORADOR]
	for texto in textos:
		minusculo = texto.lower()
		for proibido in ("pausa paga", "notificação oficial", "fila", "conferir", "termo", "cartão"):
			assert proibido not in minusculo, (proibido, texto)
