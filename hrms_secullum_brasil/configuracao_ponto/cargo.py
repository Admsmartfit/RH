"""Parâmetros do cargo na CCT vigente: piso (AJ-01), adicional noturno (AJ-04) e banco padrão (AJ-05)."""

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	get_perfil_vigente,
	get_regra_vigente,
	regra_vigente_para,
)
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.banco_horas import nova_vigencia_banco
from hrms_secullum_brasil.engine.piso import aviso_piso, piso_proporcional


def _cct(employee: str, data):
	try:
		return get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		return None


def parametro_do_cargo(cct, designation: str | None):
	if not cct or not designation:
		return None
	return next((p for p in cct.get("parametros_cargo") or [] if p.designation == designation), None)


def percentual_noturno(cct, designation: str | None) -> float:
	"""AJ-04: o do cargo, se preenchido; senão o da CCT; sem CCT, o mínimo legal."""
	if not cct:
		return d.PERCENTUAL_ADICIONAL_NOTURNO
	linha = parametro_do_cargo(cct, designation)
	if linha and linha.percentual_noturno not in (None, "") and flt(linha.percentual_noturno):
		return flt(linha.percentual_noturno)
	return flt(cct.percentual_adicional_noturno)


def _piso(employee: str, data):
	"""(linha de parâmetro do cargo, carga semanal do perfil em minutos) ou (None, None)."""
	designation = frappe.db.get_value("Employee", employee, "designation")
	linha = parametro_do_cargo(_cct(employee, data), designation)
	if not linha or not flt(linha.valor_piso):
		return None, None
	perfil = get_perfil_vigente(employee, data)
	return linha, cint(perfil.carga_semanal_minutos) if perfil else None


def piso_do_colaborador(employee: str, data) -> Decimal | None:
	linha, carga = _piso(employee, data)
	if not linha:
		return None
	return piso_proporcional(
		linha.tipo_piso,
		Decimal(str(flt(linha.valor_piso))),
		round(flt(linha.carga_referencia_horas) * 60),
		carga,
	)


def aviso_piso_colaborador(employee: str, salario, data) -> str | None:
	"""AJ-01: alerta (não bloqueio) se o salário ficar abaixo do piso proporcional do cargo."""
	linha, carga = _piso(employee, data)
	if not linha or salario in (None, ""):
		return None
	return aviso_piso(
		Decimal(str(flt(salario))),
		linha.tipo_piso,
		Decimal(str(flt(linha.valor_piso))),
		round(flt(linha.carga_referencia_horas) * 60),
		carga,
	)


def validate_salary_structure_assignment(doc, method=None):
	aviso = aviso_piso_colaborador(doc.employee, doc.base, doc.from_date or today())
	if aviso:
		frappe.msgprint(
			f"{doc.employee_name or doc.employee}: {aviso}", title=_("Piso do cargo"), indicator="orange"
		)


@frappe.whitelist()
def salario_e_piso(employee: str) -> dict:
	"""Para o cadastro do colaborador: salário vigente e piso do cargo, lado a lado."""
	from hrms_secullum_brasil.payroll_handoff.fechamento import salario_vigente

	frappe.has_permission("Employee", "read", employee, throw=True)
	hoje = getdate(today())
	salario = salario_vigente(employee, hoje)
	piso = piso_do_colaborador(employee, hoje)
	return {
		"salario": flt(salario) if salario is not None else None,
		"piso": flt(piso) if piso is not None else None,
		"aviso": aviso_piso_colaborador(employee, salario, hoje) if salario is not None else None,
	}


# ------------------------------------------------------------------ banco de horas padrão (AJ-05)


def aplicar_banco_padrao(doc) -> None:
	"""Admissão ou troca de cargo: recebe o banco padrão do cargo. Toda mudança da opção grava a data a partir
	da qual vale (no meio do mês, o mês seguinte)."""
	anterior = None if doc.is_new() else doc.get_doc_before_save()
	novo_cargo = doc.is_new() or (anterior and anterior.designation != doc.designation)
	if novo_cargo and doc.designation and doc.company:
		# CCT vigente hoje (na admissão retroativa, a CCT da data de admissão pode nem existir no cadastro)
		linha = parametro_do_cargo(_cct_do_cadastro(doc, getdate(today())), doc.designation)
		if linha:
			doc.participa_banco_horas = cint(linha.banco_padrao)
	if doc.is_new():
		doc.banco_horas_desde = nova_vigencia_banco(False, None, True, getdate(today()), admissao=True)
		return
	if anterior is None:
		return
	participava, participa = bool(cint(anterior.participa_banco_horas)), bool(cint(doc.participa_banco_horas))
	if participava != participa:
		doc.banco_horas_desde = nova_vigencia_banco(
			participava,
			getdate(anterior.banco_horas_desde) if anterior.banco_horas_desde else None,
			participa,
			getdate(today()),
		)


def _cct_do_cadastro(doc, data):
	"""CCT vigente para o cadastro em edição, com o cargo novo (o Employee pode ainda não existir no banco)."""
	dados = frappe._dict(
		name=doc.name, company=doc.company, designation=doc.designation, regra_cct=doc.get("regra_cct")
	)
	try:
		return regra_vigente_para(dados, data)
	except RegraAmbiguaError:
		return None
