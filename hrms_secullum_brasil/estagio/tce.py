"""Termo de Compromisso de Estágio vigente e validações do perfil do estagiário (EST-02 e EST-03)."""

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from hrms_secullum_brasil.engine.estagio import TCE

DOCTYPE = "Termo de Compromisso de Estagio"
PERFIS_RECUSADOS = ("Horista", "Professor", "Intermitente")


def get_tce_vigente(employee: str, data):
	"""TCE submetido que cobre a data (o mais recente), no padrão de `get_regra_vigente`."""
	data = getdate(data)
	nome = frappe.db.get_value(
		DOCTYPE,
		{"employee": employee, "docstatus": 1, "vigencia_inicio": ["<=", data], "vigencia_fim": [">=", data]},
		"name",
		order_by="vigencia_inicio desc",
	)
	return frappe.get_doc(DOCTYPE, nome) if nome else None


def cadeia_anterior(doc) -> tuple:
	"""Períodos dos TCEs anteriores (aditivos encadeados por `tce_anterior`)."""
	periodos, atual, vistos = [], doc.tce_anterior, set()
	while atual and atual not in vistos:
		vistos.add(atual)
		anterior = frappe.db.get_value(
			DOCTYPE, atual, ["vigencia_inicio", "vigencia_fim", "tce_anterior"], as_dict=True
		)
		if not anterior:
			break
		periodos.append((getdate(anterior.vigencia_inicio), getdate(anterior.vigencia_fim)))
		atual = anterior.tce_anterior
	return tuple(periodos)


def tce_do_doc(doc) -> TCE:
	return TCE(
		nivel=doc.nivel_ensino,
		inicio=getdate(doc.vigencia_inicio),
		fim=getdate(doc.vigencia_fim),
		carga_diaria=cint(doc.carga_diaria),
		carga_semanal=cint(doc.carga_semanal),
		obrigatorio=bool(cint(doc.obrigatorio)),
		pcd=bool(cint(doc.pcd)),
		bolsa=Decimal(str(flt(doc.bolsa))),
		auxilio_transporte=Decimal(str(flt(doc.auxilio_transporte))),
		seguro_fim=getdate(doc.seguro_fim) if doc.seguro_fim else None,
		cadeia_anterior=cadeia_anterior(doc),
	)


def estagiarios_do_supervisor(doc) -> int:
	"""Outros estagiários com TCE vigente do mesmo supervisor na data de início."""
	return len(
		set(
			frappe.get_all(
				DOCTYPE,
				filters={
					"supervisor": doc.supervisor,
					"docstatus": 1,
					"employee": ["!=", doc.employee],
					"vigencia_inicio": ["<=", doc.vigencia_inicio],
					"vigencia_fim": [">=", doc.vigencia_inicio],
				},
				pluck="employee",
			)
		)
	)


def erros_do_perfil(perfil, carga_diaria: int, carga_semanal: int) -> list[str]:
	"""EST-03: perfil com dia acima da carga diária ou semana acima da semanal do TCE é recusado."""
	if perfil.tipo in PERFIS_RECUSADOS:
		return [_("Perfil do tipo {0} não serve para estagiário.").format(perfil.tipo)]
	erros = []
	for linha in perfil.dias:
		minutos = cint(linha.minutos_previstos)
		if minutos > carga_diaria:
			erros.append(
				_("Perfil {0} tem {1}h{2:02d} na {3}; o TCE permite no máximo {4}h{5:02d}.").format(
					perfil.codigo,
					minutos // 60,
					minutos % 60,
					linha.dia_semana.lower(),
					carga_diaria // 60,
					carga_diaria % 60,
				)
			)
	if cint(perfil.minutos_semana_previstos) > carga_semanal:
		erros.append(
			_("Perfil {0} tem {1}h na semana; o TCE permite no máximo {2}h.").format(
				perfil.codigo, cint(perfil.minutos_semana_previstos) // 60, carga_semanal // 60
			)
		)
	return erros


def validar_perfil_do_estagiario(doc, method=None):
	"""Employee.validate: estagiário com TCE vigente não pode ter perfil acima do TCE."""
	if doc.get("tipo_remuneracao") != "Estagiario" or not doc.get("perfil_jornada") or doc.is_new():
		return
	tce = get_tce_vigente(doc.name, frappe.utils.today())
	if not tce:
		return
	perfil = frappe.get_doc("Perfil de Jornada", doc.perfil_jornada)
	erros = erros_do_perfil(perfil, cint(tce.carga_diaria), cint(tce.carga_semanal))
	if erros:
		frappe.throw(erros, title=_("Perfil incompatível com o TCE"), as_list=True)
