"""Escala do mês e repouso semanal no Frappe (AJ-02 e AJ-09 do docs/PRD-alteracoes.md).

Ordem do que vale para um dia: Escala Mensal do colaborador (que recebe as Trocas de Escala aprovadas) e,
sem escala, o Perfil de Jornada vigente, com o repouso padrão do perfil.
"""

from datetime import date, timedelta

import frappe
from frappe.utils import cint, getdate

from hrms_secullum_brasil.apuracao.lote import documento, memo
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.escala import (
	DIAS_SEMANA,
	FOLGA_COMPENSADA,
	REPOUSO,
	TRABALHO,
	DiaEscala,
	inconsistencia_domingos,
	limite_domingos,
	repouso_padrao,
	segunda_da_semana,
)
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia, montar_periodos
from hrms_secullum_brasil.engine.models import JornadaPrevista

ESCALA = "Escala Mensal"
CAMPOS_HORARIO = [f"{tipo}{n}" for n in (1, 2, 3) for tipo in ("entrada", "saida")]


def nome_escala(employee: str, ano: int, mes: int) -> str:
	return f"ESC-{employee}-{int(ano)}-{int(mes):02d}"


def periodos_da_linha(linha) -> tuple:
	periodos, _ = montar_periodos(
		[
			(minutos_do_dia(linha.get(f"entrada{n}")), minutos_do_dia(linha.get(f"saida{n}")))
			for n in (1, 2, 3)
		]
	)
	return tuple(periodos)


def linha_do_perfil(perfil, data: date):
	return next((linha for linha in perfil.dias if linha.dia_semana == DIAS_SEMANA[data.weekday()]), None)


def jornada_do_perfil(perfil, data: date) -> JornadaPrevista:
	linha = linha_do_perfil(perfil, data)
	return JornadaPrevista(
		periodos_da_linha(linha) if linha else (), bool(cint(perfil.permite_intervalo_estendido))
	)


def repouso_do_perfil(perfil, data: date) -> bool:
	"""Sem escala: a folga é o repouso se for o repouso padrão da semana (domingo ou primeira folga)."""
	segunda = segunda_da_semana(data)
	folgas = [
		segunda + timedelta(days=i)
		for i in range(7)
		if jornada_do_perfil(perfil, segunda + timedelta(days=i)).folga
	]
	return repouso_padrao(folgas, perfil.get("repouso_semanal_padrao") or d.REPOUSO_PADRAO) == data


def escala_do_mes(employee: str, ano: int, mes: int):
	nome = nome_escala(employee, ano, mes)
	existe = memo(("escala_existe", nome), lambda: bool(frappe.db.exists(ESCALA, nome)))
	return documento(ESCALA, nome) if existe else None


def dia_da_escala(employee: str, data: date, perfil) -> tuple[JornadaPrevista, bool]:
	"""(jornada prevista, é o repouso semanal?) do dia. Dia de trabalho: repouso False."""
	escala = escala_do_mes(employee, data.year, data.month)
	linha = next((x for x in escala.dias if getdate(x.data) == data), None) if escala else None
	estendido = bool(cint(perfil.permite_intervalo_estendido))
	if linha:
		periodos = periodos_da_linha(linha) if linha.situacao == TRABALHO else ()
		return JornadaPrevista(periodos, estendido), linha.situacao == REPOUSO
	jornada = jornada_do_perfil(perfil, data)
	return jornada, (jornada.folga and repouso_do_perfil(perfil, data))


def horista_escalado(employee: str, data: date, perfil) -> bool:
	"""AJ-14: horista com Escala do Mês no mês ou com semana padrão no perfil (regra nova de HE e falta)."""
	if escala_do_mes(employee, data.year, data.month):
		return True
	return any(periodos_da_linha(linha) for linha in perfil.dias)


def dia_para_conferencia(employee: str, data: date, perfil) -> DiaEscala:
	jornada, repouso = dia_da_escala(employee, data, perfil)
	if jornada.folga:
		return DiaEscala(data, REPOUSO if repouso else FOLGA_COMPENSADA)
	return DiaEscala(data, TRABALHO, jornada.periodos)


def horarios_do_dia(employee: str, data: date) -> dict | None:
	"""Horários (entrada1..saida3) que o colaborador cumpre no dia, pela escala do mês ou pelo perfil."""
	from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente

	escala = escala_do_mes(employee, data.year, data.month)
	linha = next((x for x in escala.dias if getdate(x.data) == data), None) if escala else None
	if linha is None:
		perfil = get_perfil_vigente(employee, data)
		linha = linha_do_perfil(perfil, data) if perfil else None
	elif linha.situacao != TRABALHO:
		return None
	if not linha or not periodos_da_linha(linha):
		return None
	return {c: linha.get(c) for c in CAMPOS_HORARIO}


# ------------------------------------------------------------------ gerar a escala do mês


def linhas_do_perfil(employee: str, ano: int, mes: int) -> list[dict]:
	"""Dias do mês pelo Perfil de Jornada vigente em cada dia, com o repouso padrão marcado."""
	from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente

	inicio = date(ano, mes, 1)
	fim = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
	linhas = []
	dia = inicio
	while dia <= fim:
		perfil = get_perfil_vigente(employee, dia)
		linha = {"data": dia, "dia_semana": DIAS_SEMANA[dia.weekday()], "situacao": FOLGA_COMPENSADA}
		if perfil:
			jornada = jornada_do_perfil(perfil, dia)
			if not jornada.folga:
				origem = linha_do_perfil(perfil, dia)
				linha.update({"situacao": TRABALHO, **{c: origem.get(c) for c in CAMPOS_HORARIO}})
			elif repouso_do_perfil(perfil, dia):
				linha["situacao"] = REPOUSO
		linhas.append(linha)
		dia += timedelta(days=1)
	return linhas


def obter_ou_criar_escala(employee: str, ano: int, mes: int):
	nome = nome_escala(employee, ano, mes)
	if frappe.db.exists(ESCALA, nome):
		return frappe.get_doc(ESCALA, nome)
	return frappe.get_doc(
		{
			"doctype": ESCALA,
			"employee": employee,
			"ano": ano,
			"mes": str(mes),
			"dias": linhas_do_perfil(employee, ano, mes),
		}
	)


# ------------------------------------------------------------------ domingos (pelas batidas)


def conferir_domingos(employee: str, segunda) -> None:
	"""AJ-09: inconsistência Média no domingo da semana se os domingos trabalhados seguidos chegam ao limite
	(mulher 2, homem 3 — configurável na empresa); resolve quando a pessoa folgou."""
	from hrms_secullum_brasil.apuracao.inconsistencias import (
		registrar_inconsistencia,
		resolver_inconsistencias,
	)

	domingo = getdate(segunda) + timedelta(days=6)
	emp = documento("Employee", employee)
	empresa = memo(
		("domingos", emp.company),
		lambda: frappe.db.get_value(
			"Company", emp.company, ["domingos_seguidos_mulher", "domingos_seguidos_homem"], as_dict=True
		),
	)
	limite = limite_domingos(
		emp.gender,
		cint(empresa.domingos_seguidos_mulher) or d.DOMINGOS_SEGUIDOS_MULHER,
		cint(empresa.domingos_seguidos_homem) or d.DOMINGOS_SEGUIDOS_HOMEM,
	)
	domingos = [domingo - timedelta(weeks=i) for i in range(limite - 1, -1, -1)]
	trabalhados = {
		getdate(a.data)
		for a in frappe.db.get_values(
			"Apuracao Diaria",
			{"employee": employee, "data": ["in", domingos], "trabalhado": [">", 0]},
			["data"],
			as_dict=True,
		)
	}
	inconsistencia = inconsistencia_domingos([dia in trabalhados for dia in domingos], limite)
	if inconsistencia:
		registrar_inconsistencia(
			employee,
			inconsistencia.tipo,
			inconsistencia.mensagem,
			severidade=inconsistencia.severidade,
			data=domingo,
		)
	else:
		resolver_inconsistencias(employee, "domingos_sem_folga", domingo)
