"""Casos de teste do envio ao Secullum, um a um, com qualquer funcionário (docs/PRD-sincronizacao-secullum.md,
seção 10). Não há banco de homologação: o RH abre o caso, vê a prévia, envia, confere na tela do Secullum, marca
"Ficou certo/errado" com o print e desfaz quando o caso pede.
"""

import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from hrms_secullum_brasil.ingestion import envios_secullum as envios
from hrms_secullum_brasil.ingestion import sincronizacao as fila
from hrms_secullum_brasil.integrations.secullum import sincronizacao as s

CASO = "Caso de Teste Secullum"
LICENCA_TESTE = "DOASANG"
AFASTAMENTO_TESTE = ("L-GALA", 3)  # casamento: 3 dias


def _onde_conferir(caso: s.CasoDeTeste, doc) -> list[str]:
	if caso.tipo == s.JUSTIFICATIVA_CADASTRO:
		return ["Secullum → Manutenções → Justificativas: procure a justificativa e abra para ver as opções."]
	if caso.tipo == s.ESTRUTURA:
		return [
			"Secullum → Cadastros → Estruturas: abra a estrutura da empresa e veja responsáveis e funcionários."
		]
	nome = doc.employee_name or doc.employee or "—"
	dia = getdate(doc.data).strftime("%d/%m/%Y") if doc.data else "—"
	return [f"Secullum → Movimentações → Cartão Ponto → {nome} → período com o dia {dia}."]


def preparar(doc) -> None:
	"""Preenche o que o caso testa, a prévia do envio e o passo a passo da conferência."""
	caso = s.POR_CODIGO[doc.caso]
	doc.tipo, doc.descricao = caso.tipo, caso.descricao
	if (
		caso.precisa_colaborador
		and caso.tipo not in (s.HORARIO_FUNCIONARIO, s.CARTAO)
		and not (doc.employee and doc.data)
	):
		frappe.throw(_("Escolha o colaborador e o dia do teste."))
	passos = _onde_conferir(caso, doc)
	passos.append(f"O esperado: {caso.esperado}.")
	if not caso.envia:
		passos.insert(0, _("Este caso não envia nada pelo programa: faça a ação no fluxo normal e confira."))
	passos.append(_('Marque "Ficou certo" ou "Ficou errado" e anexe o print da tela.'))
	doc.o_que_conferir = "\n".join(f"{i}. {p}" for i, p in enumerate(passos, start=1))
	doc.previa = json.dumps([o.como_dict() for o in _operacoes(doc, caso)], ensure_ascii=False, indent=1)


CASOS_COM_CARGA = ("T-Q2", "T-Q3", "T-Q5", "T-Q6")


def _carga(doc, exigir: bool = False) -> int:
	if cint(doc.carga_minutos):
		return cint(doc.carga_minutos)
	previsto = cint(
		frappe.db.get_value("Apuracao Diaria", {"employee": doc.employee, "data": doc.data}, "previsto")
	)
	if exigir and not previsto and doc.caso in CASOS_COM_CARGA:
		frappe.throw(
			_(
				"O dia {0} não tem horas previstas apuradas para este colaborador (folga, dia futuro ou sem escala). "
				'Preencha "Carga do dia (min, horista)" no caso (ex.: 180 para 3h) ou escolha um dia com escala.'
			).format(frappe.utils.formatdate(doc.data))
		)
	return previsto


def _operacoes(doc, caso: s.CasoDeTeste) -> list[s.Operacao]:
	"""Só para a prévia (o envio de verdade usa as funções de envios_secullum, as mesmas da produção)."""
	if not caso.envia:
		return []
	cpf = fila.cpf_de(doc.employee) if doc.employee else ""
	dia = getdate(doc.data) if doc.data else None
	regras = {j.nome: j for j in s.todas_as_justificativas()}
	codigo = doc.caso
	if codigo == "T-J1":
		return [s.op_justificativa_cadastro(regras["FOLGA"])]
	if codigo == "T-J2":
		return [s.op_justificativa_cadastro(regras[LICENCA_TESTE])]
	if codigo == "T-J3":
		return [s.op_justificativa_cadastro(regras["ATESTAD"])]
	if codigo == "T-P1":
		return [s.op_justificativa_cadastro(s.PAUSA_PAGA)]
	if codigo == "T-P2":
		return [s.op_justificativa_grupo(cpf, dia, s.PAUSA_PAGA.nome, _grupo_da_pausa(doc))]
	if codigo == "T-P3":  # prévia pelas batidas do programa; o envio relê o cartão do Secullum
		from hrms_secullum_brasil.apuracao.cartao_ponto import batidas_atuais

		horas = batidas_atuais(doc.employee, dia)
		try:
			return s.ops_pausa_paga(cpf, dia, dict(zip(("Entrada1", "Saida1"), horas[:2], strict=False)))[0]
		except ValueError:
			return []
	if codigo == "T-Q1":
		return [s.op_justificativa_cadastro(regras["AT0130"]), s.op_justificativa_cadastro(regras["FT0130"])]
	if codigo in ("T-F1", "T-F4", "T-F5"):
		return s.op_justificativa_dia(cpf, dia, "FOLGA")
	if codigo == "T-F2":
		return s.op_justificativa_dia(cpf, dia, "FOLGA", 1)
	if codigo == "T-F3":
		return s.op_retirar_justificativa_dia(cpf, dia, "Teste: desfazer a folga")
	if codigo == "T-L1":
		return s.op_justificativa_dia(cpf, dia, LICENCA_TESTE)
	if codigo == "T-A1":
		return [
			s.op_afastamento(
				cpf, dia, dia + timedelta(days=AFASTAMENTO_TESTE[1] - 1), AFASTAMENTO_TESTE[0], "Teste"
			)
		]
	if codigo == "T-A2":
		return [s.op_retirar_afastamento(cpf, dia, dia + timedelta(days=AFASTAMENTO_TESTE[1] - 1))]
	if codigo in ("T-Q2", "T-Q5", "T-Q6"):
		nome, _q, _a = s.justificativa_horista("atestado", _carga(doc))
		return s.op_justificativa_dia(cpf, dia, nome)
	if codigo == "T-Q3":
		nome, _q, _a = s.justificativa_horista("falta", _carga(doc))
		return s.op_justificativa_dia(cpf, dia, nome)
	if codigo == "T-Q4":
		return s.op_retirar_justificativa_dia(cpf, dia, "Teste: a batida chegou")
	if codigo == "T-E1":
		return []  # montada na hora (gestores e ativos da empresa do colaborador)
	return []


def _grupo_da_pausa(doc) -> int:
	"""O grupo logo depois das batidas do dia (a fila confere no Secullum, antes de enviar, se ele está vazio)."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import batidas_atuais

	return min(len(batidas_atuais(doc.employee, getdate(doc.data))) // 2 + 1, 5)


def _enviar_caso(doc) -> str | None:
	codigo, dia = doc.caso, getdate(doc.data) if doc.data else None
	if codigo == "T-P1":
		return (envios.justificativa_cadastro([s.PAUSA_PAGA.nome], caso=doc.name) or [None])[0]
	if codigo == "T-P2":
		return fila.agendar(
			s.JUSTIFICATIVA_DIA,
			[
				s.op_justificativa_grupo(
					fila.cpf_de(doc.employee), dia, s.PAUSA_PAGA.nome, _grupo_da_pausa(doc)
				)
			],
			descricao=f"{s.PAUSA_PAGA.nome} em {dia:%d/%m/%Y} (teste)",
			chave=f"{s.JUSTIFICATIVA_DIA}|{doc.employee}|{dia}|pausa",
			employee=doc.employee,
			data=dia,
			caso=doc.name,
			agora=True,
		)
	if codigo == "T-P3":
		cpf = fila.cpf_de(doc.employee)
		registro = fila._registro_do_dia(fila._cliente(doc), cpf, dia)
		try:
			ops, pausa = s.ops_pausa_paga(cpf, dia, registro)
		except ValueError as exc:
			frappe.throw(str(exc))
		return fila.agendar(
			s.JUSTIFICATIVA_DIA,
			ops,
			descricao=f"Pausa paga {pausa[0]}-{pausa[1]} e {s.PAUSA_PAGA.nome} em {dia:%d/%m/%Y} (teste)",
			chave=f"{s.JUSTIFICATIVA_DIA}|{doc.employee}|{dia}|pausa-completa",
			employee=doc.employee,
			data=dia,
			caso=doc.name,
			agora=True,
		)
	if codigo == "T-J1":
		return (envios.justificativa_cadastro(["FOLGA"], caso=doc.name) or [None])[0]
	if codigo == "T-J2":
		return (envios.justificativa_cadastro([LICENCA_TESTE], caso=doc.name) or [None])[0]
	if codigo == "T-J3":
		return (envios.justificativa_cadastro(["ATESTAD"], caso=doc.name) or [None])[0]
	if codigo == "T-Q1":
		nomes = envios.justificativa_cadastro(["AT0130", "FT0130"], caso=doc.name)
		return nomes[-1] if nomes else None
	if codigo in ("T-F1", "T-F4", "T-F5"):
		return envios.folga(doc.employee, dia, caso=doc.name)
	if codigo == "T-F2":
		return envios.folga(doc.employee, dia, caso=doc.name, grupos=1)
	if codigo == "T-F3":
		return envios.folga(doc.employee, dia, desfazer=True, caso=doc.name)
	if codigo == "T-L1":
		return fila.agendar(
			s.JUSTIFICATIVA_DIA,
			s.op_justificativa_dia(fila.cpf_de(doc.employee), dia, LICENCA_TESTE),
			descricao=f"{LICENCA_TESTE} em {dia:%d/%m/%Y} (teste)",
			chave=f"{s.JUSTIFICATIVA_DIA}|{doc.employee}|{dia}",
			employee=doc.employee,
			data=dia,
			caso=doc.name,
			agora=True,
		)
	if codigo in ("T-A1", "T-A2"):
		fim = dia + timedelta(days=AFASTAMENTO_TESTE[1] - 1)
		cpf = fila.cpf_de(doc.employee)
		desfazer = codigo == "T-A2"
		op = (
			s.op_retirar_afastamento(cpf, dia, fim)
			if desfazer
			else s.op_afastamento(cpf, dia, fim, AFASTAMENTO_TESTE[0], "Teste")
		)
		return fila.agendar(
			s.AFASTAMENTO,
			[op],
			descricao=f"{'Retirar' if desfazer else 'Afastamento'} {AFASTAMENTO_TESTE[0]} (teste)",
			chave=f"{s.AFASTAMENTO}|{doc.employee}|{dia}|{fim}",
			employee=doc.employee,
			data=dia,
			data_fim=fim,
			desfazer=desfazer,
			caso=doc.name,
			agora=True,
		)
	if codigo in ("T-Q2", "T-Q5", "T-Q6"):
		return envios.horista(doc.employee, dia, "atestado", _carga(doc, exigir=True), caso=doc.name)
	if codigo == "T-Q3":
		return envios.horista(doc.employee, dia, "falta", _carga(doc, exigir=True), caso=doc.name)
	if codigo == "T-Q4":
		return envios.horista(doc.employee, dia, "falta", 0, desfazer_nome="FT", caso=doc.name)
	if codigo == "T-E1":
		company = frappe.db.get_value("Employee", doc.employee, "company") if doc.employee else None
		if not company:
			frappe.throw(_("Escolha um colaborador da empresa cuja estrutura será enviada."))
		return envios.estrutura(company, caso=doc.name)
	return None


@frappe.whitelist()
def enviar(caso: str) -> dict:
	frappe.only_for(fila.PAPEIS)
	doc = frappe.get_doc(CASO, caso)
	definicao = s.POR_CODIGO[doc.caso]
	if not definicao.envia:
		frappe.throw(_("Este caso não envia nada pelo programa: confira e marque o resultado."))
	if doc.situacao not in ("Aberto", "Enviado"):
		frappe.throw(_("O caso já foi avaliado."))
	if not cint(frappe.db.get_single_value("Configuracao Secullum", "ativo")):
		frappe.throw(_("Ative a integração com o Secullum."))
	envio = _enviar_caso(doc)
	if not envio:
		frappe.throw(_("Nada foi enviado (já estava igual no Secullum ou faltam dados do caso)."))
	e = frappe.db.get_value(fila.ENVIO, envio, ["situacao", "resposta", "antes"], as_dict=True)
	leitura = {"situacao": e.situacao, "resposta": e.resposta}
	resposta = e.resposta
	if doc.caso == "T-P3" and e.situacao == "Confirmado":
		leitura.update(_leitura_da_pausa(doc))
		resposta = f"{e.resposta} {leitura['resumo']}"
	doc.db_set(
		{
			"envio": envio,
			"situacao": "Enviado",
			"leitura": json.dumps(leitura, ensure_ascii=False, indent=1),
		}
	)
	return {"envio": envio, "situacao": e.situacao, "resposta": resposta}


def _leitura_da_pausa(doc) -> dict:
	"""T-P3: relê o cartão e os totais calculados pelo Secullum no dia (o Ajuste tem de vir 00:15)."""
	client = fila._cliente(doc)
	cpf, dia = fila.cpf_de(doc.employee), getdate(doc.data)
	registro = fila._registro_do_dia(client, cpf, dia) or {}
	totais = client.calcular_totais(cpf, dia, dia) or {}
	por_coluna = dict(zip(totais.get("Colunas") or [], totais.get("Totais") or [], strict=False))
	ajuste = por_coluna.get("Ajuste") or "00:00"
	return {
		"cartao": fila._colunas(registro),
		"totais": {
			c: v for c, v in por_coluna.items() if c in ("Normais", "Horas Ad.", "Ajuste", "HTrab", "Faltas")
		},
		"ajuste": ajuste,
		"resumo": _("Totais do Secullum no dia: Ajuste {0} ({1}).").format(
			ajuste, _("certo") if ajuste == "00:15" else _("o esperado é 00:15")
		),
	}


@frappe.whitelist()
def desfazer(caso: str) -> dict:
	"""Volta o Secullum ao que estava antes do envio do caso (justificativa do dia, afastamento)."""
	frappe.only_for(fila.PAPEIS)
	doc = frappe.get_doc(CASO, caso)
	if not doc.envio:
		frappe.throw(_("Nada foi enviado neste caso."))
	envio = frappe.get_doc(fila.ENVIO, doc.envio)
	dia = getdate(envio.data) if envio.data else None
	if envio.tipo == s.FOLGA_ESCALA:
		nome = envios.folga(doc.employee, dia, desfazer=not envio.desfazer, caso=doc.name)
	elif doc.caso == "T-P3":
		# tira só o que o caso pôs (as duas batidas do intervalo e a PAUSA15) e devolve a saída à Saída 1
		pausa = tuple(
			(o.get("corpo") or {}).get("Hora")
			for o in json.loads(envio.operacoes or "[]")
			if o.get("rota") == "CartaoPonto/Manual"
		)
		cpf = fila.cpf_de(doc.employee)
		registro = fila._registro_do_dia(fila._cliente(doc), cpf, dia)
		try:
			operacoes = s.ops_desfazer_pausa(cpf, dia, registro, pausa)
		except ValueError as exc:
			frappe.throw(str(exc))
		nome = fila.agendar(
			s.JUSTIFICATIVA_DIA,
			operacoes,
			descricao=f"Desfazer {envio.descricao}"[:140],
			chave=f"{s.JUSTIFICATIVA_DIA}|{doc.employee}|{dia}|pausa-completa",
			employee=doc.employee,
			data=dia,
			desfazer=True,
			caso=doc.name,
			agora=True,
		)
	elif envio.tipo in (s.JUSTIFICATIVA_DIA, s.HORISTA):
		cpf = fila.cpf_de(doc.employee)
		# retira só o grupo que o caso lançou (a PAUSA15 fica depois das batidas: nunca mexer no grupo 1)
		grupos = [int((o.get("corpo") or {}).get("Grupo") or 1) for o in json.loads(envio.operacoes or "[]")]
		grupo = max(grupos or [1])
		operacoes = s.op_retirar_justificativa_dia(cpf, dia, "Teste: desfazer", grupo)[grupo - 1 :]
		nome = fila.agendar(
			envio.tipo,
			operacoes,
			descricao=f"Desfazer {envio.descricao}"[:140],
			chave=f"{envio.tipo}|{doc.employee}|{dia}",
			employee=doc.employee,
			data=dia,
			desfazer=True,
			caso=doc.name,
			agora=True,
		)
	elif envio.tipo == s.AFASTAMENTO:
		fim = getdate(envio.data_fim or envio.data)
		nome = fila.agendar(
			s.AFASTAMENTO,
			[s.op_retirar_afastamento(fila.cpf_de(doc.employee), dia, fim)],
			descricao=f"Desfazer {envio.descricao}"[:140],
			chave=f"{s.AFASTAMENTO}|{doc.employee}|{dia}|{fim}",
			employee=doc.employee,
			data=dia,
			data_fim=fim,
			desfazer=True,
			caso=doc.name,
			agora=True,
		)
	else:
		frappe.throw(_("Este tipo não tem desfazer automático: ajuste na tela do Secullum."))
	e = frappe.db.get_value(fila.ENVIO, nome, ["situacao", "resposta"], as_dict=True)
	doc.db_set("envio_desfazer", nome)
	return {"envio": nome, "situacao": e.situacao, "resposta": e.resposta}


@frappe.whitelist()
def avaliar(caso: str, resultado: str, observacao: str | None = None) -> str:
	"""RH conferiu na tela: "Ficou certo" (Aprovado) ou "Ficou errado" (Reprovado). Exige o print."""
	frappe.only_for(fila.PAPEIS)
	if resultado not in ("Ficou certo", "Ficou errado"):
		frappe.throw(_("Resultado inválido."))
	doc = frappe.get_doc(CASO, caso)
	if not doc.evidencia:
		frappe.throw(_("Anexe o print da tela do Secullum antes de marcar o resultado."))
	definicao = s.POR_CODIGO[doc.caso]
	if resultado == "Ficou certo" and definicao.envia and doc.envio:
		situacao = frappe.db.get_value(fila.ENVIO, doc.envio, "situacao")
		esperado_cancelado = doc.caso == "T-F4"
		if situacao in ("Erro", "Divergente") or (situacao == "Cancelado") != esperado_cancelado:
			frappe.throw(
				_(
					"O programa leu o Secullum e o envio ficou {0}: confira de novo ou marque Ficou errado."
				).format(situacao)
			)
	doc.db_set(
		{
			"resultado": resultado,
			"observacao": observacao or doc.observacao,
			"situacao": "Aprovado" if resultado == "Ficou certo" else "Reprovado",
			"avaliado_por": frappe.session.user,
			"avaliado_em": now_datetime(),
		}
	)
	return doc.situacao


@frappe.whitelist()
def matriz() -> list[dict]:
	"""Matriz de cobertura: cada caso do catálogo com o último resultado."""
	frappe.only_for(fila.PAPEIS)
	ultimos = {}
	for c in frappe.get_all(
		CASO, fields=["name", "caso", "situacao", "employee_name", "data"], order_by="creation asc"
	):
		ultimos[c.caso] = c
	return [
		{
			"caso": c.codigo,
			"tipo": s.NOMES_TIPOS[c.tipo],
			"descricao": c.descricao,
			"obrigatorio": c.obrigatorio,
			"situacao": (ultimos.get(c.codigo) or {}).get("situacao") or "Sem teste",
			"ultimo": (ultimos.get(c.codigo) or {}).get("name"),
		}
		for c in s.CATALOGO
	]
