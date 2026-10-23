"""Revisão pós-importação do Secullum (docs/PRD-importacao-secullum.md, IS-11 passo 4; Etapa 12).

O que o Secullum não tem e o RH completa: tipo de remuneração e banco de horas por cargo (em lote), além dos avisos
(horários com intervalo longo, CCT, nascimento, chefe, salário, feriados municipais).
"""

from collections import Counter, defaultdict

import frappe
from frappe import _
from frappe.utils import escape_html

from hrms_secullum_brasil.ingestion.importacao_secullum import CCT, PERFIL, SINDICATO_IMPORTADO

PAPEIS = ("System Manager", "RH Ponto")
TIPOS = ("Mensalista", "Horista", "Professor", "Intermitente", "Estagiario")
HORISTAS = ("Horista", "Intermitente")
SUFIXO_HORISTA = "-H"  # cópia Horista do perfil de um horário (mesmos dias, divisor 1)


def _importados(filtros: dict | None = None) -> list:
	return frappe.get_all(
		"Employee",
		filters={"id_secullum": ["is", "set"], "status": "Active", **(filtros or {})},
		fields=[
			"name",
			"employee_name",
			"company",
			"designation",
			"tipo_remuneracao",
			"participa_banco_horas",
			"perfil_jornada",
			"reports_to",
		],
	)


# ------------------------------------------------------------------ ações em lote


@frappe.whitelist()
def aplicar_tipo_por_cargo(designation: str, tipo: str, company: str | None = None) -> int:
	"""Muda o tipo de remuneração de todos os colaboradores ativos do cargo. Horista/Intermitente passam para a
	cópia Horista do perfil (`<código>-H`: mesmos dias, divisor 1); a volta para outro tipo religa o perfil
	original. Devolve quantos mudaram."""
	from hrms_secullum_brasil.configuracao_ponto.cargo_padrao import reapurar_colaborador

	frappe.only_for(PAPEIS)
	if tipo not in TIPOS:
		frappe.throw(_("Tipo de remuneração inválido: {0}").format(tipo))
	filtros = {"designation": designation, **({"company": company} if company else {})}
	alterados = 0
	frappe.flags.importacao_secullum = True  # o perfil vem do Secullum: só este ajuste o troca (IS-02)
	try:
		for e in _importados(filtros):
			doc = frappe.get_doc("Employee", e.name)
			antes = (doc.tipo_remuneracao, doc.perfil_jornada)
			doc.tipo_remuneracao = tipo
			if doc.perfil_jornada:
				doc.perfil_jornada = perfil_para_o_tipo(doc.perfil_jornada, tipo)
			if (doc.tipo_remuneracao, doc.perfil_jornada) != antes:
				doc.save(ignore_permissions=True)
				reapurar_colaborador(doc.name, f"Tipo de remuneração por cargo: {tipo}")
				alterados += 1
	finally:
		frappe.flags.importacao_secullum = False
	return alterados


def perfil_para_o_tipo(perfil: str, tipo: str) -> str:
	"""Perfil que combina com o tipo: a cópia Horista (criada se faltar) ou o perfil original do horário."""
	atual = frappe.db.get_value(PERFIL, perfil, ["codigo", "tipo"], as_dict=True)
	horista = tipo in HORISTAS
	if horista == (atual.tipo == "Horista"):
		return perfil
	if horista:
		codigo = f"{atual.codigo}{SUFIXO_HORISTA}"
		existente = frappe.db.get_value(PERFIL, {"codigo": codigo}, "name", order_by="vigencia_inicio desc")
		if existente:
			return existente
		original = frappe.get_doc(PERFIL, perfil)
		copia = frappe.copy_doc(original)
		copia.update(
			{
				"codigo": codigo,
				"tipo": "Horista",
				"divisor": 1,  # convenção do programa: salário-base = valor da hora (docs/regras_por_cargo.md)
				"descricao": f"{original.descricao} (horista)"[:140],
				"vigencia_inicio": original.vigencia_inicio,
				"vigencia_fim": original.vigencia_fim,
			}
		)
		copia.insert(ignore_permissions=True)
		return copia.name
	if atual.codigo.endswith(SUFIXO_HORISTA):
		original = frappe.db.get_value(
			PERFIL, {"codigo": atual.codigo[: -len(SUFIXO_HORISTA)]}, "name", order_by="vigencia_inicio desc"
		)
		return original or perfil
	return perfil


@frappe.whitelist()
def aplicar_banco_por_cargo(designation: str, participa, company: str | None = None) -> int:
	"""Liga/desliga o banco de horas dos colaboradores ativos do cargo e grava o padrão do cargo na CCT importada
	de cada empresa (as próximas admissões herdam). Devolve quantos colaboradores mudaram."""
	frappe.only_for(PAPEIS)
	participa = int(bool(int(participa)))
	alterados = 0
	empresas = set()
	for e in _importados({"designation": designation, **({"company": company} if company else {})}):
		empresas.add(e.company)
		if int(e.participa_banco_horas or 0) != participa:
			doc = frappe.get_doc("Employee", e.name)
			doc.participa_banco_horas = participa
			doc.save(ignore_permissions=True)
			alterados += 1
	for empresa in empresas:
		nome = frappe.db.get_value(CCT, {"company": empresa, "sindicato": SINDICATO_IMPORTADO}, "name")
		if not nome:
			continue
		cct = frappe.get_doc(CCT, nome)
		linha = next((p for p in cct.parametros_cargo if p.designation == designation), None)
		if linha is None:
			linha = cct.append("parametros_cargo", {"designation": designation})
		if int(linha.banco_padrao or 0) != participa:
			linha.banco_padrao = participa
			cct.save(ignore_permissions=True)
	return alterados


# ------------------------------------------------------------------ revisão (tela)


def dados_revisao() -> dict:
	ativos = _importados()
	por_cargo = defaultdict(lambda: {"total": 0, "tipos": Counter(), "banco": 0})
	for e in ativos:
		cargo = por_cargo[e.designation or _("Sem cargo")]
		cargo["total"] += 1
		cargo["tipos"][e.tipo_remuneracao or "Mensalista"] += 1
		cargo["banco"] += int(e.participa_banco_horas or 0)
	com_salario = set(
		frappe.get_all(
			"Salary Structure Assignment", filters={"docstatus": 1}, pluck="employee", distinct=True
		)
	)
	perfis_atencao = frappe.get_all(
		PERFIL,
		filters={"numero_horario_secullum": ["is", "set"], "permite_intervalo_estendido": 1},
		fields=["name", "codigo", "descricao"],
	)
	fragmentadas = sorted(
		set(
			frappe.get_all(
				"Regra CCT Parametro Cargo",
				filters={"parenttype": CCT, "jornada_fragmentada": 1},
				pluck="designation",
			)
		)
	)
	ultimo_log = frappe.db.get_value(
		"Log de Importacao Secullum",
		{"execucao": ["like", "IMPORTACAO-%"]},
		"execucao",
		order_by="creation desc",
	)
	avisos_log = (
		frappe.get_all(
			"Log de Importacao Secullum",
			filters={
				"execucao": ultimo_log,
				"passo": ["in", ["Horários", "CCT padrão", "Feriados"]],
				"mensagem": ["is", "set"],
			},
			fields=["passo", "chave", "mensagem", "resultado"],
		)
		if ultimo_log
		else []
	)
	return {
		"cargos": [
			{"cargo": cargo, **{**dados, "tipos": dict(dados["tipos"])}}
			for cargo, dados in sorted(por_cargo.items())
		],
		"sem_nascimento": frappe.db.count(
			"Inconsistencia de Ponto", {"tipo": "nascimento_ausente", "status": ["!=", "Resolvida"]}
		),
		"sem_chefe": sum(1 for e in ativos if not e.reports_to),
		"sem_salario": sum(1 for e in ativos if e.name not in com_salario),
		"ativos": len(ativos),
		"perfis_intervalo_longo": perfis_atencao,
		"cargos_jornada_fragmentada": fragmentadas,
		"avisos_horarios": [a for a in avisos_log if a.passo == "Horários" and "períodos" in a.mensagem],
		"avisos_cct": [a for a in avisos_log if a.passo == "CCT padrão" and a.resultado == "Criado"],
		"feriados_municipais": [a for a in avisos_log if a.passo == "Feriados" and a.resultado == "Aviso"],
	}


def html_revisao(dados: dict | None = None) -> str:
	dados = dados or dados_revisao()
	if not dados["ativos"]:
		return ""
	e = escape_html
	cargos = "".join(
		f"<tr><td>{e(c['cargo'])}</td><td class='text-right'>{c['total']}</td>"
		f"<td>{e(', '.join(f'{t}: {n}' for t, n in c['tipos'].items()))}</td>"
		f"<td class='text-right'>{c['banco']}</td></tr>"
		for c in dados["cargos"]
	)
	pendencias = [
		(_("Colaboradores sem data de nascimento (corrigir no Secullum)"), dados["sem_nascimento"]),
		(_("Colaboradores ativos sem chefe (campo Reporta a)"), dados["sem_chefe"]),
		(_("Colaboradores ativos sem salário (planilha de salários)"), dados["sem_salario"]),
	]
	lista = "".join(f"<li>{e(t)}: <b>{n}</b></li>" for t, n in pendencias)
	perfis = "".join(
		f"<li><a href='/app/perfil-de-jornada/{e(p.name)}'>{e(p.codigo)}</a> — {e(p.descricao)}</li>"
		for p in dados["perfis_intervalo_longo"]
	)
	fragmentadas = ", ".join(e(c) for c in dados.get("cargos_jornada_fragmentada") or [])
	avisos = "".join(
		f"<li>{e(a.passo)} — {e(a.chave)}: {e(a.mensagem)}</li>"
		for a in dados["avisos_horarios"] + dados["avisos_cct"] + dados["feriados_municipais"]
	)
	return f"""
		<h6>{_("Cargos")} <small class="text-muted">({_("use os botões Tipo de remuneração por cargo e Banco de horas por cargo")})</small></h6>
		<table class="table table-bordered table-sm">
			<tr><th>{_("Cargo")}</th><th>{_("Ativos")}</th><th>{_("Tipo de remuneração")}</th><th>{_("No banco de horas")}</th></tr>
			{cargos}
		</table>
		<h6>{_("Pendências")}</h6><ul>{lista}</ul>
		{f"<h6>{_('Horários com intervalo maior que 2h (confira o acordo/CCT)')}</h6><ul>{perfis}</ul>" if perfis else ""}
		{f"<h6>{_('Cargos com jornada fragmentada (intervalo maior que 2h permitido; confira o acordo/CCT)')}</h6><p>{fragmentadas}</p>" if fragmentadas else ""}
		{f"<h6>{_('Horários, CCT padrão e feriados')}</h6><ul>{avisos}</ul>" if avisos else ""}
	"""
