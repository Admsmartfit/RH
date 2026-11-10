"""docs/PRD-termo-ocorrencias.md (TO-04): regularização proposta, resumo, prazos em dias úteis e reincidência."""

from datetime import date

from hrms_secullum_brasil.engine import termo_ocorrencias as to
from hrms_secullum_brasil.engine.cartao_edicao import ORIGINAL, Batida
from hrms_secullum_brasil.engine.sugestoes import COBRAVEIS, TIPOS, ContextoDia

PREVISTO = ((480, 720), (780, 1020))  # 08:00-12:00 13:00-17:00
FINADOS = {date(2026, 11, 2)}


def ctx(*minutos, previsto=PREVISTO, **kw):
	return ContextoDia(tuple(Batida(m, ORIGINAL, f"raw-{m}") for m in minutos), previsto, **kw)


# textos do termo (RH, 09/11/2026): fato neutro, sem lei, sem efeito na folha; "Horário correto" hachurado nas
# linhas que são só registro (batida faltando, intervalo, falta e aula deixam o campo aberto)


def test_intervalo_deixa_o_horario_aberto_para_escrever_o_intervalo():
	# RH, 09/11/2026: quem não respondeu pelo link escreve no termo o horário do intervalo
	sem = to.propor_dia(["intrajornada"], ctx(480, 1020, previsto=()))
	assert sem == to.Proposta(
		"Jornada de 9 h sem o registro do intervalo mínimo de 1 h. Se fez o intervalo, escreva o horário.",
		sem_horario=False,
	)
	curto = to.propor_dia(["intrajornada"], ctx(480, 720, 750, 1020))
	assert (
		curto.texto
		== "Intervalo registrado de 30 min, menor que o mínimo de 1 h. Se fez o intervalo, escreva o horário."
	)
	assert curto.horarios is None and not curto.sem_horario
	horista = to.propor_dia(["intrajornada"], ctx(558, 814, previsto=(), horista=True))
	assert horista.texto.startswith("Jornada de 4h16 sem o registro do intervalo mínimo de 15 min.")
	assert horista.intervalo is None  # o termo não inclui mais o intervalo


def test_batida_faltando_pede_o_horario_sem_sugerir():
	p = to.propor_dia(["marcacao_impar"], ctx(480, 720, 780))
	assert p == to.Proposta("Não houve registro da saída. Escreva o horário correto.", sem_horario=False)
	entrada = to.propor_dia(["marcacao_impar"], ctx(720, 780, 1020))
	assert entrada.texto.startswith("Não houve registro da entrada.")


def test_batida_faltando_e_sem_intervalo_no_mesmo_dia():
	p = to.propor_dia(["intrajornada", "marcacao_impar"], ctx(540, previsto=((540, 810),), horista=True))
	assert p.texto.startswith("Não houve registro da saída. Escreva o horário correto.")
	assert not p.sem_horario  # um tipo do dia deixa o horário aberto


def test_batida_repetida_e_desconsiderada():
	p = to.propor_dia(["marcacao_duplicada"], ctx(480, 482, 720, 780, 1020))
	assert p.horarios == (480, 720, 780, 1020)
	assert (
		p.texto
		== "Batida 08:02 registrada em duplicidade (2 min depois de 08:00); a repetida é desconsiderada."
	)
	assert p.sem_horario


def test_fatos_do_dia_sem_lei_e_sem_efeito():
	falta = to.propor_dia(["falta"], ctx())
	assert falta == to.Proposta(
		"Não houve registro de ponto neste dia de trabalho previsto.", sem_horario=False
	)
	atraso = to.propor_dia(["atraso"], ctx(510, 720, 780, 980))
	assert atraso.texto == (
		"Entrada às 08:30, 30 min depois do horário previsto (08:00); saída às 16:20, 40 min antes do horário "
		"previsto (17:00)."
	)
	assert to.propor_dia(["he_acima_limite"], ctx(480, 720, 780, 1260)).texto == (
		"Jornada de 12 h, com 4 h além do previsto, acima do limite de 2 h extras por dia."
	)
	assert to.propor_dia(["intervalo_superior_2h"], ctx(480, 720, 900, 1080)).texto == (
		"Intervalo de 3 h, maior que o máximo de 2 h."
	)
	assert to.propor_dia(["intervalo_fora_de_hora"], ctx(480, 1000, 1020, 1080)).texto == (
		"Intervalo registrado no fim do expediente (16:40 às 17:00); o descanso deve ser feito no meio da jornada."
	)
	aula = to.propor_dia(["aula_nao_registrada"], ctx())
	assert (aula.texto, aula.sem_horario) == ("Aula prevista na grade sem registro de ponto.", False)
	assert to.propor_dia(["excesso_jornada_estagio"], ctx(480, 900)).texto == (
		"Jornada de 7 h, acima do limite diário do termo de estágio."
	)
	assert to.propor_dia(["intervalo_nao_marcado_horista"], ctx(1015, 1143, 1158, 1287)).texto == (
		"Jornada de 4h32, acima de 4 h, sem o registro do intervalo."
	)
	textos = " ".join(
		to.propor_dia([t], ctx(480, 720, 780, 1260)).texto for t in to.NOMES if t != "marcacao_duplicada"
	)
	for proibido in ("CLT", "art.", "Lei ", "desconta", "pago", "Ciente"):
		assert proibido not in textos
	assert "interjornada" not in to.NOMES  # o descanso de 11 h não vai ao termo
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
	assert itens[0].proposta.horarios is None


def correcao(situacao, **kw):
	return to.CorrecaoColaborador(
		date(2026, 11, 7),
		situacao,
		("16:55",),
		("16:55", "23:00"),
		decidida_em=kw.pop("decidida", None),
		**kw,
	)


def test_correcao_do_colaborador_pelo_link_aparece_no_termo():
	assert to.texto_da_correcao(correcao(to.APROVADA, decidida=date(2026, 11, 8))) == (
		"Horário 23:00 informado pelo(a) empregado(a) pelo link em 07/11; aprovado pelo RH em 08/11."
	)
	assert to.texto_da_correcao(correcao(to.AGUARDANDO_RH)).endswith("; aguardando aprovação do RH.")
	assert "não reconhece os registros do dia" in to.texto_da_correcao(
		to.CorrecaoColaborador(date(2026, 11, 7), to.AGUARDANDO_RH, nao_reconhece=True)
	)
	assert to.texto_da_correcao(
		to.CorrecaoColaborador(date(2026, 11, 7), to.AGUARDANDO_RH, ("08:00", "08:01"), ("08:00",))
	).startswith("08:01 retirado pelo(a) empregado(a)")
	assert "“trânsito parado”" in to.texto_da_correcao(
		to.CorrecaoColaborador(date(2026, 11, 7), to.AGUARDANDO_RH, explicacao="trânsito parado")
	)
	# aprovada: o dia entra mesmo resolvido, só como registro (a assinatura não mexe em nada)
	aprovada = to.DiaTermo(
		date(2026, 11, 6), (), ctx(480, 720, 780, 1020), correcao(to.APROVADA), ("marcacao_impar",)
	)
	# aguardando: as pendências do dia ficam com o RH (fora da assinatura)
	aguardando = to.DiaTermo(
		date(2026, 11, 5),
		(("INC-9", "marcacao_impar"),),
		ctx(480, 720, 780),
		correcao(to.AGUARDANDO_RH),
		("marcacao_impar",),
	)
	# recusada: o registro vem antes do fato do dia, que continua no termo
	recusada = to.DiaTermo(
		date(2026, 11, 4), (("INC-8", "marcacao_impar"),), ctx(480, 720, 780), correcao(to.RECUSADA), ()
	)
	itens = to.montar_itens([aprovada, aguardando, recusada])
	assert [(i.data.day, i.tipos, i.inconsistencias, i.proposta.sem_horario) for i in itens] == [
		(4, ("marcacao_impar",), ("INC-8",), False),
		(5, ("marcacao_impar",), (), True),
		(6, ("marcacao_impar",), (), True),
	]
	assert itens[0].proposta.texto.endswith(
		"não aprovado pelo RH. Não houve registro da saída. Escreva o horário correto."
	)


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
	assert set(to.NOMES) - to.SO_NO_TERMO <= COBRAVEIS
	assert not to.SO_NO_TERMO & COBRAVEIS  # o instrutor horista não é cobrado pelo WhatsApp
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
