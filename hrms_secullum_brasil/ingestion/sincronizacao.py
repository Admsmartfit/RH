"""Fila única de envio ao Secullum (docs/PRD-sincronizacao-secullum.md, SS-1). O que enviar fica em
integrations/secullum/sincronizacao.py (puro); aqui ficam as travas, a fila (Envio Secullum), a execução e a
conferência depois do envio.

- Cada tipo tem uma trava na Configuração Secullum: Bloqueado → Teste (só quem tem Caso de Teste aberto) → Ligado
  (todos, nas empresas liberadas). "Suspender todos os envios" vence tudo.
- Um envio pendente por chave (tipo + colaborador + dia + nome): o último prevalece.
- Batida original nunca é coberta: justificativa num dia em que a pessoa bateu ponto é cancelada com aviso.
- Depois de enviar, o programa relê o Secullum: Confirmado (ficou como esperado) ou Divergente.
- Falha nunca desfaz o programa: vira Erro (e pendência do colaborador), com Reenviar.
"""

import json
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.ingestion.secullum import get_client, id_banco_da_empresa
from hrms_secullum_brasil.integrations.secullum import sincronizacao as s
from hrms_secullum_brasil.integrations.secullum.erros import SecullumError

CONFIG = "Configuracao Secullum"
ENVIO = "Envio Secullum"
CASO = "Caso de Teste Secullum"
PAPEIS = ("System Manager", "RH Ponto")
TIPO_PENDENCIA = "envio_cartao_secullum"  # "envio ao Secullum não feito" (mesma pendência do cartão)
METODO = "hrms_secullum_brasil.ingestion.sincronizacao.processar"
TRAVAS = {
	s.FOLGA_ESCALA: "envio_folgas",
	s.HORISTA: "envio_horista",
	s.JUSTIFICATIVA_DIA: "envio_licencas",
	s.AFASTAMENTO: "envio_afastamentos",
	s.JUSTIFICATIVA_CADASTRO: "envio_justificativas",
	s.ESTRUTURA: "envio_estrutura",
	s.CARTAO: "envio_correcoes",
	s.HORARIO_FUNCIONARIO: "envio_horarios",
}
# travas antigas (cartão e horários) têm outros nomes para "ligado"
EQUIVALENTES = {"Sempre enviar": s.LIGADO, "Perguntar ao salvar": s.LIGADO}
DIA_A_DIA = (s.FOLGA_ESCALA, s.JUSTIFICATIVA_DIA, s.HORISTA)


# ------------------------------------------------------------------ travas


def modo(tipo: str) -> str:
	valor = frappe.db.get_single_value(CONFIG, TRAVAS[tipo]) or s.BLOQUEADO
	return EQUIVALENTES.get(valor, valor)


def caso_aberto(tipo: str, employee: str | None = None, data=None) -> str | None:
	"""Caso de Teste aberto do tipo para o colaborador (e o dia, quando o caso tem dia)."""
	filtros = {"tipo": tipo, "situacao": ["in", ["Aberto", "Enviado"]]}
	for nome in frappe.get_all(
		CASO, filters=filtros, fields=["name", "employee", "data"], order_by="creation desc"
	):
		if employee and nome.employee and nome.employee != employee:
			continue
		if data and nome.data and getdate(nome.data) != getdate(data):
			continue
		return nome.name
	return None


def empresa_liberada(company: str | None) -> bool:
	liberadas = [
		x.company for x in frappe.get_cached_doc(CONFIG).get("empresas_liberadas") or [] if x.company
	]
	return not liberadas or not company or company in liberadas


def liberado(
	tipo: str, employee: str | None = None, data=None, company: str | None = None
) -> tuple[bool, str]:
	if tipo in s.DESATIVADOS:
		return False, s.DESATIVADOS[tipo]
	if not cint(frappe.db.get_single_value(CONFIG, "ativo")):
		return False, _("Integração com o Secullum desativada.")
	if company is None and employee:
		company = frappe.db.get_value("Employee", employee, "company")
	return s.pode_enviar(
		modo(tipo),
		caso_aberto=bool(caso_aberto(tipo, employee, data)),
		empresa_liberada=empresa_liberada(company),
		suspenso=bool(cint(frappe.db.get_single_value(CONFIG, "envio_suspenso"))),
	)


def aprovados() -> set[str]:
	return set(frappe.get_all(CASO, filters={"situacao": "Aprovado"}, pluck="caso"))


def validar_travas(doc) -> None:
	"""Configuração Secullum.validate: só vai a Ligado o tipo com os casos obrigatórios aprovados."""
	ok = aprovados()
	erros = []
	for tipo, campo in TRAVAS.items():
		valor = EQUIVALENTES.get(doc.get(campo), doc.get(campo))
		antes = doc.get_doc_before_save()
		valor_antes = EQUIVALENTES.get(antes.get(campo), antes.get(campo)) if antes else s.BLOQUEADO
		if tipo in s.DESATIVADOS and (valor or s.BLOQUEADO) != s.BLOQUEADO:
			erros.append(s.DESATIVADOS[tipo])
			continue
		if valor == s.LIGADO and valor_antes != s.LIGADO:
			faltando = s.faltando_para_ligar(tipo, ok)
			if faltando:
				erros.append(
					_("{0}: para ligar, aprove antes os casos de teste {1}.").format(
						s.NOMES_TIPOS[tipo], ", ".join(faltando)
					)
				)
	if erros:
		frappe.throw(erros, title=_("Envio ao Secullum"), as_list=True)


# ------------------------------------------------------------------ fila


def cpf_de(employee: str) -> str:
	return "".join(c for c in str(frappe.db.get_value("Employee", employee, "cpf") or "") if c.isdigit())


def agendar(
	tipo: str,
	operacoes: list[s.Operacao],
	*,
	descricao: str,
	chave: str,
	employee: str | None = None,
	data=None,
	data_fim=None,
	company: str | None = None,
	desfazer: bool = False,
	origem: tuple[str, str] | None = None,
	caso: str | None = None,
	agora: bool = False,
) -> str | None:
	"""Põe na fila (substituindo o pendente da mesma chave). None se a trava não deixa (e não há caso)."""
	if not caso:
		pode, _motivo = liberado(tipo, employee, data, company)
		if not pode:
			return None
		caso = caso_aberto(tipo, employee, data)
	nome = frappe.db.get_value(ENVIO, {"chave": chave, "situacao": ["in", ["Na fila", "Erro", "Bloqueado"]]})
	doc = frappe.get_doc(ENVIO, nome) if nome else frappe.new_doc(ENVIO)
	doc.update(
		{
			"tipo": tipo,
			"situacao": "Na fila",
			"descricao": descricao[:140],
			"chave": chave,
			"employee": employee,
			"company": company
			or (frappe.db.get_value("Employee", employee, "company") if employee else None),
			"data": getdate(data) if data else None,
			"data_fim": getdate(data_fim) if data_fim else None,
			"desfazer": int(desfazer),
			"caso_teste": caso,
			"operacoes": json.dumps([o.como_dict() for o in operacoes], ensure_ascii=False, indent=1),
			"usuario": frappe.session.user,
			"origem_doctype": origem[0] if origem else None,
			"origem_name": origem[1] if origem else None,
		}
	)
	doc.flags.ignore_links = True  # a origem é só referência (a licença pode ser apagada depois)
	doc.save(ignore_permissions=True)
	if agora:
		processar(doc.name)
	else:
		frappe.enqueue(
			METODO,
			queue="short",
			nome=doc.name,
			job_id=f"envio-secullum-{doc.name}",
			deduplicate=True,
			enqueue_after_commit=True,
		)
	return doc.name


def _cliente(doc):
	company = doc.get("company") or (  # Envio Secullum tem a empresa; o Caso de Teste, só o colaborador
		frappe.db.get_value("Employee", doc.employee, "company") if doc.employee else None
	)
	return get_client(id_banco_da_empresa(company))


def executar(client, op: dict) -> None:
	rota, metodo = op["rota"], op["metodo"]
	if rota.startswith("CartaoPonto"):
		client.editar_cartao(metodo, rota, op["corpo"])
	elif rota == "Justificativas":
		client.salvar_justificativa(op["corpo"])
	elif rota == "FuncionariosAfastamentos":
		client.salvar_afastamento(op["corpo"])
	elif rota == "FuncionariosAfastamentos/Cpf":
		client.excluir_afastamento(op["params"])
	elif rota == "Estruturas":
		client.salvar_estrutura(op["corpo"])
	else:
		raise ValueError(_("Rota de envio desconhecida: {0}").format(rota))


def _registro_do_dia(client, cpf: str, dia: date) -> dict | None:
	return next(
		(
			r
			for r in client.listar_cartao(dia, dia, cpf)
			if "".join(c for c in str(r.get("FuncionarioCpf") or cpf) if c.isdigit()) == cpf
		),
		None,
	)


def _conferir(doc, client, ops: list[dict]) -> tuple[str, str]:
	"""(situação, texto) relendo o Secullum."""
	if doc.tipo in DIA_A_DIA:
		cpf = cpf_de(doc.employee)
		registro = _registro_do_dia(client, cpf, getdate(doc.data))
		nome = next(
			(o["corpo"].get("Justificativa") for o in ops if o["corpo"] and o["corpo"].get("Justificativa")),
			None,
		)
		if doc.desfazer:
			sobrou = [
				valor
				for g in range(1, 6)
				if (valor := str((registro or {}).get(f"Entrada{g}") or "")) and ":" not in valor
			]
			if not sobrou:
				return "Confirmado", _("Justificativa retirada do cartão.")
			return "Divergente", _("O cartão ainda tem justificativa: {0}").format(_colunas(registro))
		grupo = next(
			(int(o["corpo"].get("Grupo") or 1) for o in ops if o["corpo"] and o["corpo"].get("Grupo")), 1
		)
		if s.justificativa_no_cartao(registro, nome or "", grupo):
			return "Confirmado", _("Cartão do dia com {0}.").format(nome)
		return "Divergente", _("O cartão do dia não mostra {0}: {1}").format(nome, _colunas(registro))
	if doc.tipo == s.AFASTAMENTO:
		cpf = cpf_de(doc.employee)
		inicio, fim = getdate(doc.data), getdate(doc.data_fim or doc.data)
		presente = s.afastamento_presente(client.listar_afastamentos(inicio, fim), cpf, inicio, fim)
		if presente != bool(not doc.desfazer):
			return "Divergente", _("O afastamento não ficou como esperado no Secullum.")
		return "Confirmado", _("Afastamento {0} no Secullum.").format(
			_("retirado") if doc.desfazer else _("lançado")
		)
	if doc.tipo == s.JUSTIFICATIVA_CADASTRO:
		atuais = {j.get("NomeAbreviado"): j for j in client.listar_justificativas()}
		faltas = []
		for o in ops:
			nome = o["corpo"]["nomeAbreviado"]
			regra = next((j for j in s.todas_as_justificativas() if j.nome == nome), None)
			if regra:
				faltas += [f"{nome}: {f}" for f in s.justificativa_diverge(regra, atuais.get(nome))]
		return (
			("Divergente", "; ".join(faltas)) if faltas else ("Confirmado", _("Justificativas conferidas."))
		)
	if doc.tipo == s.ESTRUTURA:
		descricao = ops[0]["corpo"]["descricao"]
		ok = any(e.get("Descricao") == descricao for e in client.listar_estruturas())
		return (
			("Confirmado", _("Estrutura {0} no Secullum.").format(descricao))
			if ok
			else (
				"Divergente",
				_("A estrutura {0} não apareceu no Secullum.").format(descricao),
			)
		)
	return "Enviado", ""


def _colunas(registro: dict | None) -> str:
	if not registro:
		return _("dia sem registro no Secullum")
	return ", ".join(
		f"{t}{n}={registro.get(f'{t}{n}')}"
		for n in range(1, 6)
		for t in ("Entrada", "Saida")
		if registro.get(f"{t}{n}")
	)


def processar(nome: str) -> str | None:
	if not frappe.db.exists(ENVIO, nome):
		return None
	doc = frappe.get_doc(ENVIO, nome)
	doc.flags.ignore_links = True
	if doc.situacao in ("Enviado", "Confirmado", "Cancelado"):
		return doc.situacao
	if doc.tipo in s.DESATIVADOS:
		doc.db_set({"situacao": "Bloqueado", "resposta": s.DESATIVADOS[doc.tipo]})
		return doc.situacao
	if not doc.caso_teste:
		pode, motivo = liberado(doc.tipo, doc.employee, doc.data, doc.company)
		if not pode:
			doc.db_set({"situacao": "Bloqueado", "resposta": motivo})
			return doc.situacao
	ops = json.loads(doc.operacoes or "[]")
	try:
		client = _cliente(doc)
		if doc.tipo in DIA_A_DIA and doc.employee:
			registro = _registro_do_dia(client, cpf_de(doc.employee), getdate(doc.data))
			doc.antes = json.dumps(registro or {}, ensure_ascii=False, default=str)
			cabe, motivo = s.cabe_no_dia(registro, ops)
			if not doc.desfazer and not cabe:
				doc.update(
					{
						"situacao": "Cancelado",
						"resposta": _("A justificativa não foi enviada: {0} ({1}).").format(
							motivo, _colunas(registro)
						),
					}
				)
				doc.save(ignore_permissions=True)
				return doc.situacao
			ops, puladas = s.sem_apagar_batida(registro, ops)
			if puladas and not ops:
				doc.update(
					{
						"situacao": "Cancelado",
						"resposta": _(
							"Nada enviado: a coluna tem batida e o programa nunca apaga batida ({0})."
						).format(", ".join(puladas)),
					}
				)
				doc.save(ignore_permissions=True)
				return doc.situacao
		for op in ops:
			executar(client, op)
		situacao, texto = _conferir(doc, client, ops)
	except (SecullumError, ValueError, NotImplementedError) as exc:
		mensagem = str(exc) or type(exc).__name__
		doc.update({"situacao": "Erro", "resposta": mensagem[:1000]})
		if doc.employee:
			registrar_inconsistencia(
				doc.employee,
				TIPO_PENDENCIA,
				_("Envio ao Secullum não feito ({0}): {1}").format(doc.descricao, mensagem),
				"Média",
				getdate(doc.data) if doc.data else getdate(today()),
				ENVIO,
				doc.name,
			)
	else:
		doc.update({"situacao": situacao, "resposta": texto, "enviado_em": now_datetime()})
		if doc.employee and doc.data:
			resolver_inconsistencias(doc.employee, TIPO_PENDENCIA, getdate(doc.data))
	doc.tentativas = cint(doc.tentativas) + 1
	doc.save(ignore_permissions=True)
	return doc.situacao


def processar_fila() -> int:
	"""Cron: o que ficou na fila (job perdido, trava que abriu depois)."""
	limite = add_to_date(now_datetime(), minutes=-5)
	nomes = frappe.get_all(
		ENVIO, filters={"situacao": ["in", ["Na fila", "Bloqueado"]], "modified": ["<", limite]}, pluck="name"
	)
	for nome in nomes[:200]:
		processar(nome)
	return len(nomes)


@frappe.whitelist()
def reenviar(nome: str) -> str | None:
	frappe.only_for(PAPEIS)
	frappe.db.set_value(ENVIO, nome, "situacao", "Na fila")
	return processar(nome)


def bloqueios_do_fechamento(doc) -> list[str]:
	"""Fechamento de Ponto: envios com erro/divergência no período e tarefas do Secullum que bloqueiam."""
	saida = []
	ruins = frappe.get_all(
		ENVIO,
		filters={
			"company": doc.company,
			"situacao": ["in", ["Erro", "Divergente"]],
			"data": ["between", [doc.periodo_inicio, doc.periodo_fim]],
		},
		pluck="name",
	)
	if ruins:
		saida.append(
			_("{0} envio(s) ao Secullum com erro ou divergência no período: {1}.").format(
				len(ruins), ", ".join(ruins[:5])
			)
		)
	tarefas = frappe.get_all(
		"Tarefa Secullum",
		filters={"bloqueia_fechamento": 1, "situacao": ["in", ["Pendente", "Feita (RH)", "Divergente"]]},
		pluck="titulo",
	)
	if tarefas:
		saida.append(
			_("{0} tarefa(s) no Secullum pendente(s) (Tarefa Secullum): {1}.").format(
				len(tarefas), "; ".join(tarefas[:3])
			)
		)
	return saida
