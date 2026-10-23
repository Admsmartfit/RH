"""Tela única do cargo (docs/PRD-cargo.md): o que vale para todos de um cargo fica no cadastro do Cargo (Designation).

Decisões de 22/10/2026 (Ricardo): todos do cargo ganham o mesmo valor (por hora ou por mês); mudar o tipo de
remuneração no cargo muda todos os colaboradores ativos dele.

Ao salvar o cargo:
- tipo de remuneração → todos os ativos do cargo (horista/intermitente vão para a cópia horista do horário);
- valor e data → uma Atribuição de salário nova para cada ativo cujo salário na data for outro;
- piso, noturno, banco padrão e jornada fragmentada → a linha do cargo em cada CCT vigente (a apuração e a folha
  continuam lendo a CCT, com a vigência e a trava de período fechado dela).
Colaborador admitido ou que muda para o cargo recebe o tipo e o valor do cargo.
"""

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate, getdate, today

from hrms_secullum_brasil.engine import defaults_legais as d

CCT = "Regra Sindical CCT"
CAMPOS_CCT = (
	"tipo_piso",
	"valor_piso",
	"carga_referencia_horas",
	"percentual_noturno",
	"banco_padrao",
	"jornada_fragmentada",
)
CAMPOS_VALOR = ("valor_cargo", "valor_desde")
PAPEIS = ("System Manager", "RH Ponto", "HR Manager", "HR User")


def _mudou(doc, campos) -> bool:
	antes = doc.get_doc_before_save()
	if antes is None:
		return any(doc.get(c) for c in campos)
	return any((antes.get(c) or 0) != (doc.get(c) or 0) for c in campos)


def ativos(designation: str) -> list[str]:
	return frappe.get_all("Employee", filters={"designation": designation, "status": "Active"}, pluck="name")


# ------------------------------------------------------------------ eventos do Cargo


def validate_designation(doc, method=None):
	if flt(doc.get("valor_cargo")) and not doc.get("valor_desde"):
		doc.valor_desde = today()
	noturno = flt(doc.get("percentual_noturno"))
	if noturno and noturno < d.PERCENTUAL_ADICIONAL_NOTURNO:
		frappe.throw(
			_("Adicional noturno do cargo ({0}%) menor que o mínimo de {1}% (CLT, art. 73).").format(
				noturno, d.PERCENTUAL_ADICIONAL_NOTURNO
			)
		)
	if (
		flt(doc.get("valor_piso"))
		and doc.get("tipo_piso") == "Mensalista"
		and not flt(doc.get("carga_referencia_horas"))
	):
		frappe.throw(_("Informe a carga semanal de referência do piso."))


def on_update_designation(doc, method=None):
	resumo = []
	if doc.get("tipo_remuneracao") and _mudou(doc, ("tipo_remuneracao",)):
		n = aplicar_tipo(doc.name, doc.tipo_remuneracao)
		resumo.append(_("Tipo {0} aplicado a {1} colaborador(es).").format(doc.tipo_remuneracao, n))
	if flt(doc.get("valor_cargo")) and _mudou(doc, CAMPOS_VALOR):
		n, avisos = aplicar_valor(doc.name, Decimal(str(flt(doc.valor_cargo))), getdate(doc.valor_desde))
		resumo.append(
			_("Valor de R$ {0} desde {1}: {2} atribuição(ões) de salário nova(s).").format(
				frappe.format_value(flt(doc.valor_cargo), {"fieldtype": "Currency"}),
				formatdate(doc.valor_desde),
				n,
			)
		)
		resumo += avisos
	if _mudou(doc, CAMPOS_CCT):
		alteradas, avisos = sincronizar_ccts(doc)
		resumo.append(_("{0} CCT(s) vigente(s) atualizada(s) com os parâmetros do cargo.").format(alteradas))
		resumo += avisos
	if resumo:
		frappe.msgprint("<br>".join(resumo), title=_("Cargo {0}").format(doc.name), indicator="green")


# ------------------------------------------------------------------ aplicar aos colaboradores


def aplicar_tipo(designation: str, tipo: str) -> int:
	"""Tipo de remuneração do cargo em todos os ativos (o horário vai para a cópia horista, ou volta)."""
	from hrms_secullum_brasil.ingestion.revisao_importacao import perfil_para_o_tipo

	alterados = 0
	frappe.flags.importacao_secullum = True  # o perfil vem do Secullum: só este ajuste o troca (IS-02)
	try:
		for employee in ativos(designation):
			emp = frappe.get_doc("Employee", employee)
			antes = (emp.tipo_remuneracao, emp.perfil_jornada)
			emp.tipo_remuneracao = tipo
			if emp.perfil_jornada:
				emp.perfil_jornada = perfil_para_o_tipo(emp.perfil_jornada, tipo)
			if (emp.tipo_remuneracao, emp.perfil_jornada) != antes:
				emp.save(ignore_permissions=True)
				reapurar_colaborador(employee, f"Tipo de remuneração do cargo: {tipo}")
				alterados += 1
	finally:
		frappe.flags.importacao_secullum = False
	return alterados


def reapurar_colaborador(employee: str, motivo: str) -> None:
	"""Mudou o tipo ou o horário: os dias já apurados (fora de período fechado) vão para a fila de reapuração."""
	from hrms_secullum_brasil.ingestion.importacao_secullum import reapurar_dias_apurados

	reapurar_dias_apurados(employee, "2000-01-01", today(), motivo)


def _gravar_salario(employee: str, valor: Decimal, inicio, avisos: list) -> bool:
	"""Atribuição de salário nova se o salário vigente na data for outro. Devolve se criou."""
	from hrms_secullum_brasil.engine.planilha_salarios import LinhaSalario
	from hrms_secullum_brasil.payroll_handoff.fechamento import salario_vigente
	from hrms_secullum_brasil.payroll_handoff.planilha_salarios import _gravar

	admissao = frappe.db.get_value("Employee", employee, "date_of_joining")
	data = max(getdate(inicio), getdate(admissao)) if admissao else getdate(inicio)
	atual = salario_vigente(employee, data)
	if atual is not None and Decimal(str(atual)) == valor:
		return False
	return _gravar(employee, LinhaSalario(0, "", valor, data), avisos, False) != "sem_mudanca"


def aplicar_valor(designation: str, valor: Decimal, inicio) -> tuple[int, list[str]]:
	criadas, avisos = 0, []
	for employee in ativos(designation):
		try:
			criadas += int(_gravar_salario(employee, valor, inicio, avisos))
		except frappe.ValidationError as exc:
			nome = frappe.db.get_value("Employee", employee, "employee_name")
			avisos.append(f"{nome}: {frappe.utils.strip_html(str(exc))}")
			frappe.clear_last_message()
	return criadas, [a.replace("Linha 0: ", "") for a in avisos]


# ------------------------------------------------------------------ CCTs


def _valores_cct(doc) -> dict:
	return {c: doc.get(c) for c in CAMPOS_CCT}


def _ccts_vigentes() -> list[str]:
	hoje = getdate(today())
	return frappe.get_all(
		CCT,
		filters={"vigencia_inicio": ["<=", hoje]},
		or_filters=[["vigencia_fim", "is", "not set"], ["vigencia_fim", ">=", hoje]],
		pluck="name",
	)


def _aceita(cct, designation: str) -> bool:
	escopo = {c.designation for c in cct.get("cargos") or []}
	return not escopo or designation in escopo


def sincronizar_ccts(cargo) -> tuple[int, list[str]]:
	"""Grava os parâmetros do cargo na linha dele em cada CCT vigente (cria a linha se faltar)."""
	alteradas, avisos = 0, []
	valores = _valores_cct(cargo)
	for nome in _ccts_vigentes():
		cct = frappe.get_doc(CCT, nome)
		if not _aceita(cct, cargo.name):
			continue
		linha = next((p for p in cct.parametros_cargo if p.designation == cargo.name), None)
		if linha is None:
			linha = cct.append("parametros_cargo", {"designation": cargo.name})
		if all((linha.get(c) or 0) == (valores[c] or 0) for c in CAMPOS_CCT):
			continue
		linha.update(valores)
		ponto = f"cargo_cct_{alteradas}_{len(avisos)}"
		frappe.db.savepoint(ponto)
		try:
			cct.save(ignore_permissions=True)
			alteradas += 1
		except frappe.ValidationError as exc:
			frappe.db.rollback(save_point=ponto)
			frappe.clear_last_message()
			avisos.append(
				_("CCT {0} não foi alterada: {1}").format(
					cct.get("titulo") or nome, frappe.utils.strip_html(str(exc))
				)
			)
	return alteradas, avisos


def preencher_cct_nova(cct) -> None:
	"""CCT nova (do RH ou da importação) já nasce com os parâmetros dos cargos que têm algum definido."""
	existentes = {p.designation for p in cct.get("parametros_cargo") or []}
	campos = ["name", *CAMPOS_CCT]
	for cargo in frappe.get_all("Designation", fields=campos):
		if cargo.name in existentes or not _aceita(cct, cargo.name):
			continue
		if not (
			flt(cargo.valor_piso)
			or flt(cargo.percentual_noturno)
			or cint(cargo.banco_padrao)
			or cint(cargo.jornada_fragmentada)
		):
			continue
		cct.append("parametros_cargo", {"designation": cargo.name, **{c: cargo.get(c) for c in CAMPOS_CCT}})


# ------------------------------------------------------------------ colaborador admitido ou que muda de cargo


def _cargo_mudou(doc) -> bool:
	if doc.is_new():
		return bool(doc.designation)
	antes = doc.get_doc_before_save()
	return bool(antes and antes.designation != doc.designation and doc.designation)


def validate_employee(doc, method=None):
	"""Tipo de remuneração do cargo para quem entra no cargo."""
	if not _cargo_mudou(doc):
		return
	tipo = frappe.db.get_value("Designation", doc.designation, "tipo_remuneracao")
	if tipo and doc.get("tipo_remuneracao") != tipo:
		from hrms_secullum_brasil.ingestion.revisao_importacao import perfil_para_o_tipo

		doc.tipo_remuneracao = tipo
		if doc.get("perfil_jornada"):
			doc.perfil_jornada = perfil_para_o_tipo(doc.perfil_jornada, tipo)
	doc.flags.cargo_mudou = True
	doc.flags.cargo_admissao = doc.is_new()


def on_update_employee(doc, method=None):
	"""Valor do cargo para quem entra no cargo (atribuição de salário a partir da entrada no cargo)."""
	if not doc.flags.get("cargo_mudou") or doc.status != "Active":
		return
	doc.flags.cargo_mudou = False
	valor, desde = frappe.db.get_value("Designation", doc.designation, ["valor_cargo", "valor_desde"]) or (
		None,
		None,
	)
	if not flt(valor):
		return
	# admissão: desde o valor do cargo (no mínimo a admissão); troca de cargo: a partir de hoje
	inicio = getdate(desde or today())
	if not doc.flags.get("cargo_admissao"):
		inicio = max(inicio, getdate(today()))
	avisos = []
	try:
		_gravar_salario(doc.name, Decimal(str(flt(valor))), inicio, avisos)
	except frappe.ValidationError as exc:
		frappe.clear_last_message()
		frappe.msgprint(
			_("Valor do cargo não aplicado a {0}: {1}").format(
				doc.employee_name, frappe.utils.strip_html(str(exc))
			),
			indicator="orange",
		)


# ------------------------------------------------------------------ resumo na tela do cargo


@frappe.whitelist()
def resumo_do_cargo(designation: str) -> dict:
	"""Colaboradores ativos (tipo, salário vigente, empresa) e as CCTs vigentes com a linha do cargo."""
	from hrms_secullum_brasil.payroll_handoff.fechamento import salario_vigente

	frappe.has_permission("Designation", "read", designation, throw=True)
	hoje = getdate(today())
	colaboradores = []
	for e in frappe.get_all(
		"Employee",
		filters={"designation": designation, "status": "Active"},
		fields=["name", "employee_name", "company", "tipo_remuneracao", "perfil_jornada"],
		order_by="employee_name asc",
	):
		salario = salario_vigente(e.name, hoje)
		colaboradores.append({**e, "salario": flt(salario) if salario is not None else None})
	ccts = []
	for nome in _ccts_vigentes():
		cct = frappe.get_doc(CCT, nome)
		if not _aceita(cct, designation):
			continue
		linha = next((p for p in cct.parametros_cargo if p.designation == designation), None)
		ccts.append(
			{
				"name": nome,
				"titulo": cct.get("titulo") or nome,
				"company": cct.company,
				"tem_linha": bool(linha),
				"igual": bool(linha)
				and all(
					(linha.get(c) or 0) == (frappe.db.get_value("Designation", designation, c) or 0)
					for c in CAMPOS_CCT
				),
			}
		)
	return {"colaboradores": colaboradores, "ccts": ccts}


@frappe.whitelist()
def reaplicar(designation: str) -> str:
	"""Aplica de novo tudo do cargo (tipo, valor e CCTs) a todos — para quem ficou diferente."""
	frappe.only_for(PAPEIS)
	cargo = frappe.get_doc("Designation", designation)
	partes = []
	if cargo.get("tipo_remuneracao"):
		partes.append(
			_("tipo em {0} colaborador(es)").format(aplicar_tipo(designation, cargo.tipo_remuneracao))
		)
	avisos = []
	if flt(cargo.get("valor_cargo")):
		n, avisos = aplicar_valor(
			designation, Decimal(str(flt(cargo.valor_cargo))), getdate(cargo.valor_desde or today())
		)
		partes.append(_("{0} atribuição(ões) de salário").format(n))
	alteradas, avisos_cct = sincronizar_ccts(cargo)
	partes.append(_("{0} CCT(s)").format(alteradas))
	return "; ".join(partes) + ("<br>" + "<br>".join(avisos + avisos_cct) if avisos or avisos_cct else "")


def copiar_das_ccts() -> int:
	"""after_migrate: cargo ainda sem parâmetros recebe os da linha dele numa CCT vigente (ex.: a jornada
	fragmentada que a importação ligou), para salvar o cargo depois não apagar o que já vale. Nunca sobrescreve."""
	if not frappe.get_meta("Designation").has_field("jornada_fragmentada"):
		return 0
	copiados = 0
	for cargo in frappe.get_all("Designation", fields=["name", *CAMPOS_CCT]):
		if (
			flt(cargo.valor_piso)
			or flt(cargo.percentual_noturno)
			or cint(cargo.banco_padrao)
			or cint(cargo.jornada_fragmentada)
		):
			continue
		linhas = frappe.get_all(
			"Regra CCT Parametro Cargo",
			filters={
				"parenttype": CCT,
				"parent": ["in", _ccts_vigentes() or [""]],
				"designation": cargo.name,
			},
			fields=list(CAMPOS_CCT),
			limit=1,
		)
		if linhas:
			frappe.db.set_value("Designation", cargo.name, dict(linhas[0]), update_modified=False)
			copiados += 1
	return copiados
