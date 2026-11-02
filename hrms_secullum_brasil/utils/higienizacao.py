"""Higienização de dados duplicados ou órfãos (auditoria de 02/11/2026, docs/auditoria-2026-11.md).

Diagnóstico (só leitura):
	bench --site ponto.localhost execute hrms_secullum_brasil.utils.higienizacao.diagnosticar

Correções (sem `aplicar=1` só mostram o que fariam; faça backup antes):
	bench --site ponto.localhost execute hrms_secullum_brasil.utils.higienizacao.corrigir --kwargs "{'aplicar': 1}"

Fica de fora de propósito: a marcação original (Secullum Checkin Raw) é imutável (AGENTS.md) — batida duplicada só é
listada, e quem resolve é o RH com Tratamento de Ponto ("desconsiderar"). Espelho em Employee Checkin e cadastros
duplicados também só são listados: a decisão é do RH.
"""

import frappe
from frappe.utils import add_days, nowdate

EXEMPLOS = 5

# (nome, explicação, SQL que devolve uma linha por ocorrência)
VERIFICACOES = (
	(
		"batida_duplicada",
		"Duas batidas ativas no mesmo minuto, nenhuma desconsiderada no Secullum (contariam duas vezes).",
		"""select employee, data_hora, count(*) n from `tabSecullum Checkin Raw`
		where status = 'Ativa' and ifnull(tipo_fonte, '') <> 'Desconsiderado'
		group by employee, data_hora having count(*) > 1""",
	),
	(
		"batida_sem_colaborador",
		"Batida ativa sem colaborador (não entra na apuração).",
		"""select name, data_hora, origem_id from `tabSecullum Checkin Raw`
		where status = 'Ativa' and ifnull(employee, '') = ''""",
	),
	(
		"batida_sem_espelho",
		"Batida ativa (não desconsiderada) sem Employee Checkin espelhado (só informativo: a raw é a fonte).",
		"""select name, employee, data_hora from `tabSecullum Checkin Raw`
		where status = 'Ativa' and ifnull(tipo_fonte, '') <> 'Desconsiderado' and ifnull(employee_checkin, '') = ''""",
	),
	(
		"espelho_orfao",
		"Employee Checkin ligado a uma batida substituída ou apagada.",
		"""select ec.name, ec.employee, ec.time from `tabEmployee Checkin` ec
		where ifnull(ec.secullum_checkin_raw, '') <> '' and not exists (
			select 1 from `tabSecullum Checkin Raw` r where r.name = ec.secullum_checkin_raw and r.status = 'Ativa')""",
	),
	(
		"espelho_duplicado",
		"Dois Employee Checkin do mesmo colaborador no mesmo horário.",
		"""select employee, time, count(*) n from `tabEmployee Checkin`
		group by employee, time having count(*) > 1""",
	),
	(
		"inconsistencia_aberta_duplicada",
		"Mesma pendência aberta duas vezes (colaborador, dia e tipo).",
		"""select employee, data, tipo, count(*) n from `tabInconsistencia de Ponto`
		where status = 'Aberta' group by employee, data, tipo having count(*) > 1""",
	),
	(
		"reapuracao_pendente_duplicada",
		"O mesmo dia na fila de reapuração mais de uma vez.",
		"""select employee, data, count(*) n from `tabReapuracao Pendente`
		where status = 'Pendente' group by employee, data having count(*) > 1""",
	),
	(
		"reapuracao_processada_antiga",
		"Linhas já processadas da fila com mais de 30 dias (só ocupam espaço).",
		"""select count(*) n from `tabReapuracao Pendente`
		where status = 'Processada' and modified < date_sub(curdate(), interval 30 day) having count(*) > 0""",
	),
	(
		"cpf_duplicado_na_empresa",
		"Dois cadastros ativos com o mesmo CPF na mesma empresa.",
		"""select company, cpf, group_concat(name) colaboradores from tabEmployee
		where status = 'Active' and ifnull(cpf, '') <> '' group by company, cpf having count(*) > 1""",
	),
	(
		"id_secullum_duplicado",
		"Dois cadastros com o mesmo Id do Secullum.",
		"""select id_secullum, group_concat(name) colaboradores from tabEmployee
		where ifnull(id_secullum, '') <> '' group by id_secullum having count(*) > 1""",
	),
	(
		"tipo_remuneracao_diferente_do_cargo",
		"Ativo com tipo de remuneração diferente do cargo (o cargo propaga o tipo; confira se é exceção).",
		"""select e.name, e.tipo_remuneracao, d.name cargo, d.tipo_remuneracao do_cargo from tabEmployee e
		join tabDesignation d on d.name = e.designation
		where e.status = 'Active' and ifnull(d.tipo_remuneracao, '') <> ''
		and ifnull(e.tipo_remuneracao, '') <> d.tipo_remuneracao""",
	),
	(
		"turno_nativo_em_uso",
		"Turno nativo do HRMS (default_shift / Shift Assignment) em uso: a apuração não lê, só o Perfil de Jornada.",
		"""select 'Employee.default_shift' origem, count(*) n from tabEmployee where ifnull(default_shift, '') <> ''
		having count(*) > 0
		union all
		select 'Shift Assignment', count(*) from `tabShift Assignment` where docstatus = 1 having count(*) > 0""",
	),
	(
		"attendance_nativo",
		"Attendance do HRMS gravado (com skip_auto_attendance ligado deveria ser zero).",
		"select count(*) n from tabAttendance where docstatus < 2 having count(*) > 0",
	),
)


def diagnosticar() -> dict:
	"""Contagem e exemplos de cada verificação. Não grava nada."""
	saida = {}
	for nome, explicacao, sql in VERIFICACOES:
		linhas = frappe.db.sql(sql, as_dict=True)
		# as verificações de contagem devolvem o total na coluna "n" (uma linha por origem)
		contagem = bool(linhas) and set(linhas[0]) <= {"n", "origem"}
		ocorrencias = sum(int(x.n) for x in linhas) if contagem else len(linhas)
		saida[nome] = {"ocorrencias": ocorrencias, "o_que_e": explicacao, "exemplos": linhas[:EXEMPLOS]}
	resumo = {k: v["ocorrencias"] for k, v in saida.items()}
	print(frappe.as_json(resumo))
	return saida


def corrigir(aplicar: int = 0, dias_fila: int = 30) -> dict:
	"""Corrige só o que é seguro e reversível pelo próprio sistema:

	- pendência aberta duplicada: fica a mais antiga; as outras viram "Resolvida" (com comentário);
	- dia repetido na fila de reapuração: fica um;
	- fila de reapuração: apaga as linhas "Processada" com mais de `dias_fila` dias.
	"""
	aplicar = int(aplicar)
	feito = {"inconsistencias_resolvidas": 0, "fila_duplicada_removida": 0, "fila_processada_removida": 0}

	for grupo in frappe.db.sql(
		"""select employee, data, tipo from `tabInconsistencia de Ponto`
		where status = 'Aberta' group by employee, data, tipo having count(*) > 1""",
		as_dict=True,
	):
		nomes = frappe.get_all(
			"Inconsistencia de Ponto",
			filters={"employee": grupo.employee, "data": grupo.data, "tipo": grupo.tipo, "status": "Aberta"},
			order_by="creation asc",
			pluck="name",
		)
		for nome in nomes[1:]:
			feito["inconsistencias_resolvidas"] += 1
			if aplicar:
				frappe.db.set_value("Inconsistencia de Ponto", nome, "status", "Resolvida")
				frappe.get_doc("Inconsistencia de Ponto", nome).add_comment(
					"Comment", f"Higienização: duplicada de {nomes[0]}."
				)

	for grupo in frappe.db.sql(
		"""select employee, data from `tabReapuracao Pendente`
		where status = 'Pendente' group by employee, data having count(*) > 1""",
		as_dict=True,
	):
		nomes = frappe.get_all(
			"Reapuracao Pendente",
			filters={"employee": grupo.employee, "data": grupo.data, "status": "Pendente"},
			order_by="creation asc",
			pluck="name",
		)
		feito["fila_duplicada_removida"] += len(nomes) - 1
		if aplicar and len(nomes) > 1:
			frappe.db.delete("Reapuracao Pendente", {"name": ["in", nomes[1:]]})

	filtro = {"status": "Processada", "modified": ["<", add_days(nowdate(), -int(dias_fila))]}
	feito["fila_processada_removida"] = frappe.db.count("Reapuracao Pendente", filtro)
	if aplicar and feito["fila_processada_removida"]:
		frappe.db.delete("Reapuracao Pendente", filtro)

	if aplicar:
		frappe.db.commit()
	print(("Aplicado: " if aplicar else "Simulação (use aplicar=1): ") + frappe.as_json(feito))
	return feito
