"""Relatório de auditoria (docs/PRD-whatsapp-aceite-auditoria.md, AU-03 a AU-06)."""

import json
from datetime import date, datetime

from hrms_secullum_brasil.engine import auditoria as au

INICIO, FIM = date(2026, 11, 2), date(2026, 11, 8)


def _trat(**kw):
	base = {
		"name": "TP-1",
		"employee": "E1",
		"employee_name": "Ana Souza",
		"company": "ES Praia",
		"data": "2026-11-03",
		"tipo": "Inclusao de marcacao",
		"data_hora": "2026-11-03 07:00:00",
		"motivo": "Esqueceu de bater",
		"owner": "gestor@x.com",
		"docstatus": 1,
		"aprovado_por": "rh@x.com",
		"aprovado_em": "2026-11-03 14:20:00",
		"creation": "2026-11-03 10:00:00",
		"modified": "2026-11-03 14:20:00",
	}
	base.update(kw)
	return base


def test_tratamento_inclusao_aprovado():
	linha = au.linha_tratamento(_trat(anexo="/private/files/x.pdf"))
	assert linha.secao == au.CORRECOES
	assert linha.descricao == (
		"Incluiu 07:00 — Esqueceu de bater — por gestor@x.com — aprovado por rh@x.com em 03/11 14:20 — com anexo"
	)
	assert linha.dia == date(2026, 11, 3)
	assert au.rota(linha.doctype, linha.name) == "/app/tratamento-de-ponto/TP-1"


def test_tratamento_relogio_em_destaque():
	linha = au.linha_tratamento(
		_trat(tipo="Desconsiderar marcacao", data_hora="2026-11-03 17:02:00", confirmou_apagar_relogio=1)
	)
	assert linha.secao == au.RELOGIO
	assert linha.descricao.startswith(
		"Desconsiderou 17:02 — batida do relógio; as duas confirmações por gestor@x.com"
	)
	sem_relogio = au.linha_tratamento(_trat(tipo="Desconsiderar marcacao", confirmou_apagar_relogio=0))
	assert sem_relogio.secao == au.CORRECOES


def test_tratamento_atestado_nunca_mostra_o_motivo_nem_cid():
	linha = au.linha_tratamento(
		_trat(
			tipo="Abono do dia",
			justificativa="Atestado médico",
			motivo="CID J11 gripe",
			cid="J11",
			docstatus=0,
		)
	)
	assert "J11" not in linha.descricao and "gripe" not in linha.descricao
	assert linha.descricao == "Abono do dia — Atestado — por gestor@x.com — aguardando aprovação"
	assert (
		"Abono parcial de 30 min"
		in au.linha_tratamento(_trat(tipo="Abono parcial", minutos_abonados=30)).descricao
	)
	cancelado = au.linha_tratamento(
		_trat(tipo="Compensação de feriado", justificativa="Folga", motivo="", docstatus=2)
	)
	assert cancelado.descricao == "Compensação de feriado — Folga — por gestor@x.com — CANCELADO"
	assert "sem motivo" in au.linha_tratamento(_trat(motivo="")).descricao


def test_limpar_tira_chaves_de_saude():
	assert au.limpar({"cid": "J11", "anexo_atestado": "x", "CID_10": "y", "motivo": "ok", "decidir": 1}) == {
		"motivo": "ok",
		"decidir": 1,
	}
	assert au.limpar(None) == {}


def test_mascaras():
	assert au.mascarar_cpf("123.456.789-09") == "***.456.***-09"
	assert au.mascarar_cpf("123") == ""
	assert au.final_celular("(27) 99876-1234") == "final 1234"
	assert au.final_celular(None) == "sem celular"
	assert au.rota(None, "x") == ""
	assert au.quando_br(None) == "-" and au.dia_br("ruim") == "-" and au.hora("") == "-"
	assert au.quando_br(date(2026, 11, 3)) == "03/11 00:00"


def test_resposta_termo_whatsapp_email():
	resp = au.linha_resposta(
		{
			"name": "RWP-1",
			"employee_name": "Ana",
			"confirmado_em": "2026-11-04 09:10:00",
			"resumo": "03/11: informou 12:00 e 13:00",
			"situacao": "Recusada",
			"aprovado_por": "rh@x.com",
			"aprovado_em": "2026-11-04 15:00:00",
			"motivo_recusa": "não confere",
		}
	)
	assert resp.descricao == (
		"Confirmou em 04/11 09:10 (CPF + código) — 03/11: informou 12:00 e 13:00 — situação: Recusada — por rh@x.com "
		"em 04/11 15:00 — motivo da recusa: não confere"
	)
	termo = au.linha_termo(
		{
			"inicio": "2026-10-26",
			"fim": "2026-11-01",
			"emitido_por": "rh@x.com",
			"emitido_em": "2026-11-02 08:00",
			"status": "Assinado (conforme)",
			"confirmado_em": "2026-11-03 10:00",
			"confirmado_por": "Ana",
			"via": "Celular (colaborador)",
			"cancelado_motivo": "",
		}
	)
	assert "Termo de 26/10/2026 a 01/11/2026" in termo.descricao
	assert "confirmado (Celular (colaborador)) por Ana em 03/11 10:00" in termo.descricao
	assert "cancelado: x" in au.linha_termo({"cancelado_motivo": "x"}).descricao
	zap = au.linha_whatsapp(
		{
			"destinatario": "Colaborador",
			"numero": "5527998761234",
			"regra": "D+1",
			"situacao": "Barrada",
			"filtro": "sem aceite do WhatsApp",
			"enviada_em": "2026-11-03 09:00",
			"entregue_em": "2026-11-03 09:01",
			"lida_em": "2026-11-03 09:30",
		}
	)
	assert zap.descricao == (
		"Para Colaborador (final 1234) — D+1 — situação: Barrada — enviada 03/11 09:00 — entregue 03/11 09:01 — "
		"lida 03/11 09:30 — motivo: sem aceite do WhatsApp"
	)
	email = au.linha_email(
		{
			"destinatarios": "a@x.com",
			"reference_doctype": "Termo de Ocorrencias",
			"reference_name": "T1",
			"status": "Sent",
		}
	)
	assert email.descricao == "Para a@x.com — sobre Termo de Ocorrencias T1 — situação: Sent"
	assert "sobre -" in au.linha_email({}).descricao


def test_secullum_inconsistencias_escala():
	envio = au.linha_envio_secullum(
		{
			"descricao": "Folga 07/11",
			"data": "2026-11-07",
			"situacao": "Erro",
			"usuario": "rh@x.com",
			"resposta": "500",
		}
	)
	assert envio.descricao == "Folga 07/11 — dia 07/11/2026 — situação: Erro — por rh@x.com — 500"
	cartao = au.linha_envio_secullum({"data": "2026-11-07", "situacao": "Enviado"}, "Envio Cartao Secullum")
	assert cartao.descricao.startswith("Correção do cartão") and cartao.doctype == "Envio Cartao Secullum"
	retro = au.linha_inconsistencia(
		{"status": "Aberta", "data": "2026-10-10", "descricao": "batida 07:00 nova", "creation": "2026-11-04"}
	)
	assert (
		retro.secao == au.RETROATIVAS
		and retro.descricao == "Dia 10/10/2026 mudou no Secullum — batida 07:00 nova"
	)
	mantida = au.linha_inconsistencia(
		{
			"status": "Mantida",
			"tipo": "atraso",
			"mantida_por": "g@x.com",
			"mantida_em": "2026-11-05 10:00",
			"motivo_manter": "Será tratada no Secullum",
		}
	)
	assert mantida.secao == au.MANTIDAS and "Será tratada no Secullum" in mantida.descricao
	pub = au.linha_publicacao(
		{
			"company": "ES Praia",
			"publicado_por": "g@x.com",
			"publicado_em": "2026-11-02 18:00",
			"inicio": "2026-11-09",
			"fim": "2026-11-15",
			"colaboradores": 12,
			"urgente": 1,
		}
	)
	assert pub.descricao.endswith("12 colaborador(es) — mudança urgente")
	troca = au.linha_troca(
		{"aprovado_por": "rh@x.com", "aprovado_em": "2026-11-03 11:00", "motivo": "pedido"}
	)
	assert troca.descricao == "Troca de escala aprovada por rh@x.com em 03/11 11:00 — motivo: pedido"
	convite = au.linha_convite(
		{
			"parent": "CT-1",
			"data": "2026-11-06",
			"horario": "08:00-12:00",
			"resposta": "Posso",
			"respondido_em": "2026-11-04 08:00",
		}
	)
	assert (
		convite.descricao == 'Convite para turno de 06/11/2026 08:00-12:00 — respondeu "Posso" em 04/11 08:00'
	)
	assert convite.name == "CT-1"


def test_versao_e_aceite():
	dados = json.dumps({"changed": [["tolerancia", 5, 10], ["cid", "A", "B"], ["nome", None, "X"]]})
	assert au.mudancas_da_versao(dados) == [("tolerancia", "5", "10"), ("nome", "", "X")]
	assert au.mudancas_da_versao("não é json") == []
	assert au.mudancas_da_versao(None) == []
	linha = au.linha_versao(
		{
			"ref_doctype": "Regra Sindical CCT",
			"docname": "CCT 2026",
			"owner": "rh@x.com",
			"creation": "2026-11-03 09:00",
			"data": dados,
		}
	)
	assert linha.secao == au.CADASTRO
	assert linha.descricao == (
		"Regra Sindical CCT CCT 2026 — por rh@x.com em 03/11 09:00 — tolerancia: 5 → 10; nome: (vazio) → X"
	)
	muitas = json.dumps({"changed": [[f"c{i}", i, i + 1] for i in range(8)]})
	assert au.linha_versao({"data": muitas}, maximo=2).descricao.endswith("e mais 6")
	assert au.linha_versao({"data": json.dumps({"added": []})}) is None
	aceite = au.linha_aceite(
		{
			"acao": "Aceite",
			"registrado_em": "2026-11-04 08:00",
			"numero": "27998761234",
			"versao_texto": "1",
			"ip": "1.2.3.4",
			"salvou_contato_em": "2026-11-04 08:01",
			"primeira_mensagem_em": "2026-11-04 08:02",
		}
	)
	assert aceite.descricao == (
		"Aceitou em 04/11 08:00 (final 1234, texto versão 1, IP 1.2.3.4) — salvou o contato, tocou em enviar a primeira "
		"mensagem"
	)
	revogado = au.linha_aceite(
		{
			"acao": "Revogação",
			"registrado_por": "g@x.com",
			"registrado_em": "2026-11-05 10:00",
			"motivo": "pediu",
		}
	)
	assert revogado.descricao == "Revogado por g@x.com em 05/11 10:00 — motivo: pediu"


def test_montar_ordena_e_resume():
	linhas = [
		au.linha_tratamento(_trat(name="TP-2", employee_name="Bruno", company="ES Centro")),
		au.linha_tratamento(_trat(name="TP-1", employee_name="Ana")),
		au.linha_tratamento(_trat(name="TP-3", employee_name="Ana", data="2026-11-02")),
		au.linha_tratamento(_trat(name="TP-4", tipo="Desconsiderar marcacao", confirmou_apagar_relogio=1)),
		au.linha_versao(
			{
				"ref_doctype": "Perfil de Jornada",
				"docname": "P1",
				"data": json.dumps({"changed": [["a", 1, 2]]}),
			}
		),
		None,
	]
	rel = au.montar(linhas, INICIO, FIM, "Semanal")
	assert rel.tem_conteudo and rel.total == 5
	assert [e["empresa"] for e in rel.empresas] == ["ES Centro", "ES Praia", au.GERAL]
	praia = rel.empresas[1]["secoes"]
	assert [s["chave"] for s in praia] == [au.CORRECOES, au.RELOGIO]
	assert praia[1]["destaque"] is True
	assert [linha.name for linha in praia[0]["linhas"]] == ["TP-3", "TP-1"]
	assert rel.resumo[au.CORRECOES] == 3 and rel.resumo[au.RELOGIO] == 1 and rel.resumo[au.CADASTRO] == 1
	assert (
		au.resumo_em_texto(rel)
		== "Correções do ponto: 3\nBatidas do relógio desconsideradas: 1\nCadastro e regras: 1"
	)
	assert rel.indice == []


def test_montar_vazio_e_indice():
	vazio = au.montar([], INICIO, FIM, "Semanal")
	assert not vazio.tem_conteudo and vazio.empresas == [] and au.resumo_em_texto(vazio) == ""
	muitas = [
		au.linha_tratamento(
			_trat(name=f"TP-{i}", employee_name=f"Pessoa {i % 3}", creation=datetime(2026, 11, 3))
		)
		for i in range(au.LINHAS_POR_PAGINA * au.PAGINAS_PARA_INDICE + 1)
	]
	rel = au.montar(muitas, INICIO, FIM, "Mensal")
	assert [i["employee_name"] for i in rel.indice] == ["Pessoa 0", "Pessoa 1", "Pessoa 2"]
	assert sum(i["linhas"] for i in rel.indice) == len(muitas)


def test_resumo_dias_resposta():
	dias = [
		{
			"data": "2026-11-03",
			"horarios_antes": "08:00 12:00",
			"horarios_informados": "08:00 12:00 13:00 17:00",
		},
		{"data": "2026-11-04", "nao_reconhece": 1},
		{
			"data": "2026-11-05",
			"horarios_antes": "08:00",
			"horarios_informados": "08:00",
			"explicacao": "treinamento",
		},
		{"horarios_antes": "", "horarios_informados": "09:00"},
	]
	assert au.resumo_dias_resposta(dias) == (
		"03/11: 08:00 12:00 → 08:00 12:00 13:00 17:00; 04/11: não reconhece; 05/11: confirmou (explicou: treinamento); "
		"-: (sem batidas) → 09:00"
	)
	assert au.resumo_dias_resposta(None) == ""
