"""Quando enviar ao Secullum (docs/PRD-sincronizacao-secullum.md, SS-3 a SS-8). Cada função monta as operações
(integrations/secullum/sincronizacao.py) e põe na fila (ingestion/sincronizacao.py), que respeita as travas.

- Folgas da Escala do Mês → justificativa "FOLGA" no dia (SS-5).
- Horista: falta e atestado com a quantidade do dia ("FT0300", "AT0130") — SS-4.
- Licenças (Leave Application): dia a dia (justificativa) ou afastamento (SS-3, SS-6).
- Cadastro das justificativas da regra (SS-3) e estrutura da unidade (SS-8).
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, getdate, today

from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.ingestion import sincronizacao as fila
from hrms_secullum_brasil.integrations.secullum import sincronizacao as s

CONFIG = "Configuracao Secullum"
FOLGAS = ("Repouso semanal", "Folga compensada")
HORISTAS = ("Horista",)


def _grupos_folga(employee: str, data) -> int:
	"""Grupos do cartão em que a "FOLGA" é lançada: só o 1º (padrão) ou um por período previsto (caso T-F2)."""
	if not cint(frappe.db.get_single_value(CONFIG, "folga_em_todos_os_grupos")):
		return 1
	from hrms_secullum_brasil.ingestion.envio_cartao import horarios_do_programa

	return max(horarios_do_programa(employee, data)[1], 1)


# ------------------------------------------------------------------ folgas da escala (SS-5)


def folga(employee: str, data, *, desfazer: bool = False, caso: str | None = None, grupos: int | None = None):
	data = getdate(data)
	cpf = fila.cpf_de(employee)
	grupos = grupos or _grupos_folga(employee, data)
	if desfazer:
		ops = s.op_retirar_justificativa_dia(
			cpf, data, _("Escala mudou: o dia voltou a ser de trabalho."), grupos
		)
	else:
		ops = s.op_justificativa_dia(cpf, data, "FOLGA", grupos)
	return fila.agendar(
		s.FOLGA_ESCALA,
		ops,
		descricao=_("{0} folga de {1}").format(
			_("Retirar") if desfazer else _("Lançar"), data.strftime("%d/%m/%Y")
		),
		chave=f"{s.FOLGA_ESCALA}|{employee}|{data}",
		employee=employee,
		data=data,
		desfazer=desfazer,
		caso=caso,
		agora=bool(caso),
	)


def on_update_escala(doc, method=None) -> None:
	"""Escala Mensal salva (publicação, troca aprovada, mudança urgente): folgas novas vão; folga desfeita volta."""
	antes = doc.get_doc_before_save()
	anteriores = {getdate(d.data): d.situacao for d in (antes.dias if antes else [])}
	hoje = getdate(today())
	for dia in doc.dias:
		data = getdate(dia.data)
		if data < hoje or periodo_fechado(doc.employee, data):
			continue
		era, agora = anteriores.get(data), dia.situacao
		if agora in FOLGAS and era not in FOLGAS:
			folga(doc.employee, data)
		elif era in FOLGAS and agora not in FOLGAS:
			folga(doc.employee, data, desfazer=True)


# ------------------------------------------------------------------ horista (SS-4)


def horista(employee: str, data, tipo: str, minutos: int, *, desfazer_nome: str | None = None, caso=None):
	"""Lança "AT<qtde>"/"FT<qtde>" no dia; com `desfazer_nome`, retira a justificativa enviada antes."""
	data = getdate(data)
	cpf = fila.cpf_de(employee)
	if desfazer_nome:
		ops = s.op_retirar_justificativa_dia(cpf, data, _("A batida do dia chegou: a falta foi retirada."))
		descricao = _("Retirar {0} de {1}").format(desfazer_nome, data.strftime("%d/%m/%Y"))
		chave = f"{s.HORISTA}|{employee}|{data}"
	else:
		if minutos <= 0:
			return None  # sem horas no dia não há o que justificar (nunca "AT0000"/"FT0000")
		nome, enviado, arredondou = s.justificativa_horista(tipo, minutos)
		ops = s.op_justificativa_dia(cpf, data, nome)
		descricao = _("{0} em {1}").format(nome, data.strftime("%d/%m/%Y"))
		if arredondou:
			descricao += _(" (carga {0} arredondada para {1})").format(s.hhmm(minutos), s.hhmm(enviado))
		chave = f"{s.HORISTA}|{employee}|{data}"
	return fila.agendar(
		s.HORISTA,
		ops,
		descricao=descricao,
		chave=chave,
		employee=employee,
		data=data,
		desfazer=bool(desfazer_nome),
		caso=caso,
		agora=bool(caso),
	)


def _ultimo_envio_horista(employee: str, data) -> dict | None:
	return frappe.db.get_value(
		fila.ENVIO,
		{
			"tipo": s.HORISTA,
			"employee": employee,
			"data": data,
			"situacao": ["in", ["Enviado", "Confirmado"]],
		},
		["name", "descricao", "desfazer"],
		as_dict=True,
		order_by="creation desc",
	)


def preparar_horistas(data=None) -> int:
	"""Job diário (D+1 e D+2): falta (dia previsto sem batida) e atestado dos horistas, com a carga do dia.
	Se a batida apareceu depois de a falta ter ido, retira a falta."""
	feitos = 0
	dias = [getdate(data)] if data else [add_days(getdate(today()), -1), add_days(getdate(today()), -2)]
	for dia in dias:
		apuracoes = frappe.get_all(
			"Apuracao Diaria",
			filters={"data": dia, "previsto": [">", 0]},
			fields=["employee", "data", "previsto", "falta", "trabalhado", "abonado"],
		)
		tipos = dict(
			frappe.get_all(
				"Employee",
				filters={"name": ["in", [a.employee for a in apuracoes] or [""]]},
				fields=["name", "tipo_remuneracao"],
				as_list=True,
			)
		)
		for a in apuracoes:
			if tipos.get(a.employee) not in HORISTAS or periodo_fechado(a.employee, dia):
				continue
			ultimo = _ultimo_envio_horista(a.employee, dia)
			ja_enviado = ultimo and not ultimo.desfazer and ultimo.descricao[:2] in ("AT", "FT")
			if cint(a.trabalhado) > 0:
				if ja_enviado and ultimo.descricao.startswith("FT"):
					horista(a.employee, dia, "falta", 0, desfazer_nome=ultimo.descricao.split(" ")[0])
					feitos += 1
				continue
			if ja_enviado:
				continue
			atestado = cint(a.abonado) and frappe.db.exists(
				"Atestado Medico",
				{"employee": a.employee, "docstatus": 1, "data_inicio": ["<=", dia], "data_fim": [">=", dia]},
			)
			if atestado:
				horista(a.employee, dia, "atestado", cint(a.previsto))
				feitos += 1
			elif cint(a.falta) > 0:
				horista(a.employee, dia, "falta", cint(a.falta))
				feitos += 1
	return feitos


# ------------------------------------------------------------------ licenças e afastamentos (SS-3, SS-6)


def _justificativa_da_licenca(leave_type: str) -> str | None:
	return s.LICENCAS.get(leave_type)


def licenca(doc, *, desfazer: bool = False, caso: str | None = None) -> list[str]:
	"""Leave Application aprovada: afastamento (longa ou férias/maternidade) ou justificativa dia a dia."""
	nome = _justificativa_da_licenca(doc.leave_type)
	if not nome or doc.leave_type == "Atestado Médico":  # atestado segue o fluxo do cartão/horista
		return []
	inicio, fim = getdate(doc.from_date), getdate(doc.to_date)
	cpf = fila.cpf_de(doc.employee)
	dias = date_diff(fim, inicio) + 1
	saida = []
	if dias > s.DIAS_PARA_AFASTAMENTO or doc.leave_type in ("Férias", "Licença-maternidade"):
		op = (
			s.op_retirar_afastamento(cpf, inicio, fim)
			if desfazer
			else s.op_afastamento(cpf, inicio, fim, nome, f"{doc.leave_type} ({doc.name})")
		)
		saida.append(
			fila.agendar(
				s.AFASTAMENTO,
				[op],
				descricao=_("{0} {1}: {2} a {3}").format(
					_("Retirar") if desfazer else _("Afastamento"),
					nome,
					inicio.strftime("%d/%m"),
					fim.strftime("%d/%m/%Y"),
				),
				chave=f"{s.AFASTAMENTO}|{doc.employee}|{inicio}|{fim}",
				employee=doc.employee,
				data=inicio,
				data_fim=fim,
				desfazer=desfazer,
				origem=("Leave Application", doc.name),
				caso=caso,
				agora=bool(caso),
			)
		)
		return [n for n in saida if n]
	dia = inicio
	while dia <= fim:
		if not periodo_fechado(doc.employee, dia):
			ops = (
				s.op_retirar_justificativa_dia(cpf, dia, _("Licença cancelada."))
				if desfazer
				else s.op_justificativa_dia(cpf, dia, nome)
			)
			saida.append(
				fila.agendar(
					s.JUSTIFICATIVA_DIA,
					ops,
					descricao=_("{0} {1} em {2}")
					.format(_("Retirar") if desfazer else "", nome, dia.strftime("%d/%m/%Y"))
					.strip(),
					chave=f"{s.JUSTIFICATIVA_DIA}|{doc.employee}|{dia}",
					employee=doc.employee,
					data=dia,
					desfazer=desfazer,
					origem=("Leave Application", doc.name),
					caso=caso,
					agora=bool(caso),
				)
			)
		dia += timedelta(days=1)
	return [n for n in saida if n]


def on_update_licenca(doc, method=None) -> None:
	if doc.docstatus == 1 and doc.status == "Approved":
		licenca(doc)


def on_cancel_licenca(doc, method=None) -> None:
	licenca(doc, desfazer=True)


# ------------------------------------------------------------------ cadastro de justificativas (SS-3) e estrutura


def _justificativas_atuais(company: str | None = None) -> dict:
	from hrms_secullum_brasil.ingestion.secullum import get_client, id_banco_da_empresa

	return {
		j.get("NomeAbreviado"): j for j in get_client(id_banco_da_empresa(company)).listar_justificativas()
	}


def justificativa_cadastro(nomes: list[str], *, caso: str | None = None) -> list[str]:
	atuais = _justificativas_atuais()
	regras = {j.nome: j for j in s.todas_as_justificativas()}
	saida = []
	for nome in nomes:
		regra = regras[nome]
		if not caso and not s.justificativa_diverge(regra, atuais.get(nome)):
			continue
		saida.append(
			fila.agendar(
				s.JUSTIFICATIVA_CADASTRO,
				[s.op_justificativa_cadastro(regra, atuais.get(nome))],
				descricao=_("Justificativa {0}").format(nome),
				chave=f"{s.JUSTIFICATIVA_CADASTRO}|{nome}",
				caso=caso,
				agora=bool(caso),
			)
		)
	return [n for n in saida if n]


@frappe.whitelist()
def preparar_justificativas() -> str:
	"""Botão: põe na fila as justificativas da regra que faltam ou estão diferentes no Secullum."""
	frappe.only_for(fila.PAPEIS)
	regras = s.todas_as_justificativas()
	atuais = _justificativas_atuais()
	if not any(s.justificativa_diverge(j, atuais.get(j.nome)) for j in regras):
		return _("Nada a enviar: as {0} justificativas do programa já estão iguais no Secullum.").format(
			len(regras)
		)
	nomes = justificativa_cadastro([j.nome for j in regras])
	if not nomes:
		return _(
			"Nada foi para a fila: a trava do cadastro de justificativas está em {0}. Em Teste, abra antes um caso de "
			"justificativa (T-J1, T-J2 ou T-J3) na Matriz de testes; Ligado envia sempre."
		).format(fila.modo(s.JUSTIFICATIVA_CADASTRO))
	return _("{0} justificativa(s) na fila de envio.").format(len(nomes))


def estrutura(company: str, *, caso: str | None = None) -> str | None:
	"""Estrutura da unidade: responsáveis = gestores da unidade com CPF (funcionários); vinculados = ativos.
	Desativada no código (s.DESATIVADOS): nem o caso de teste envia."""
	from hrms_secullum_brasil.configuracao_ponto.gestores import linhas

	if s.ESTRUTURA in s.DESATIVADOS:
		frappe.throw(s.DESATIVADOS[s.ESTRUTURA])
	responsaveis = [
		fila.cpf_de(linha.employee) for linha in linhas(company, "ve_ponto") if linha.get("employee")
	]
	funcionarios = [
		"".join(c for c in str(cpf or "") if c.isdigit())
		for cpf in frappe.get_all("Employee", filters={"company": company, "status": "Active"}, pluck="cpf")
	]
	descricao = frappe.get_cached_value("Company", company, "abbr") or company
	return fila.agendar(
		s.ESTRUTURA,
		[s.op_estrutura(descricao, [c for c in responsaveis if c], [c for c in funcionarios if c])],
		descricao=_("Estrutura {0}").format(descricao),
		chave=f"{s.ESTRUTURA}|{company}",
		company=company,
		caso=caso,
		agora=bool(caso),
	)


@frappe.whitelist()
def enviar_estruturas() -> str:
	frappe.only_for(fila.PAPEIS)
	nomes = [n for c in frappe.get_all("Company", pluck="name") if (n := estrutura(c))]
	return _("{0} estrutura(s) na fila de envio.").format(len(nomes))
