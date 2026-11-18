"""Cartões automáticos do quadro de tarefas (docs/PRD-quadro-tarefas.md, seção 3.5).

Cada fonte tem liga/desliga na Configuracao Tarefas (todas começam desligadas). Um cartão aberto por caso (chave da
origem); o caso resolvido conclui o cartão sozinho ("Resolvido no sistema em dd/mm"). O cartão descartado ou concluído
à mão não renasce para a mesma chave. Um erro numa fonte vira Error Log e não para as outras.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate

from hrms_secullum_brasil.apuracao import tarefas as tf
from hrms_secullum_brasil.engine import tarefas as t

SECULLUM, FECHAMENTO, INCONSISTENCIA = "tarefa_secullum", "fechamento_bloqueado", "inconsistencia_alta"
SITUACOES_SECULLUM_ABERTAS = ("Pendente", "Feita (RH)", "Divergente")


def garantir(tipo: str, chave: str, titulo: str, **campos) -> str | None:
	"""Cria o cartão do caso (ou atualiza o título/descrição do que já está aberto). Devolve o nome, ou None quando o
	caso já teve um cartão encerrado (concluído ou descartado)."""
	existentes = frappe.get_all(
		tf.DOCTYPE,
		filters={"origem_tipo": tipo, "origem_chave": chave},
		fields=["name", "coluna", "titulo", "descricao"],
		order_by="creation desc",
	)
	aberto = next((x for x in existentes if x.coluna in t.ABERTAS), None)
	if aberto:
		novos = {"titulo": titulo[:200], "descricao": campos.get("descricao")}
		if any((aberto.get(k) or "") != (v or "") for k, v in novos.items()):
			frappe.db.set_value(tf.DOCTYPE, aberto.name, novos)
		return aberto.name
	if existentes:
		return None
	doc = frappe.get_doc(
		{
			"doctype": tf.DOCTYPE,
			"titulo": titulo[:200],
			"origem": t.AUTOMATICA,
			"origem_tipo": tipo,
			"origem_chave": chave,
			"coluna": t.A_FAZER,
			"prioridade": campos.pop("prioridade", t.NORMAL),
			**campos,
		}
	)
	doc.insert(ignore_permissions=True)
	tf.ao_atribuir(doc, "Administrator")
	return doc.name


def fechar_resolvidos(tipo: str, chaves_abertas: set[str]) -> int:
	"""Conclui os cartões abertos do tipo cujo caso não está mais aberto."""
	fechados = 0
	for row in frappe.get_all(
		tf.DOCTYPE,
		filters={"origem_tipo": tipo, "coluna": ["in", list(t.ABERTAS)], "origem": t.AUTOMATICA},
		fields=["name", "origem_chave"],
	):
		if row.origem_chave in chaves_abertas:
			continue
		doc = frappe.get_doc(tf.DOCTYPE, row.name)
		tf.concluir(
			doc, None, comentario=_("Resolvido no sistema em {0}.").format(getdate().strftime("%d/%m"))
		)
		fechados += 1
	return fechados


# ------------------------------------------------------------------ fontes


def _tarefas_secullum() -> set[str]:
	abertas = set()
	for x in frappe.get_all(
		"Tarefa Secullum",
		filters={"situacao": ["in", list(SITUACOES_SECULLUM_ABERTAS)]},
		fields=["name", "titulo", "passos", "situacao", "bloqueia_fechamento"],
	):
		garantir(
			SECULLUM,
			x.name,
			_("Fazer no Secullum: {0}").format(x.titulo or x.name),
			descricao=x.passos,
			responsavel_tipo=t.GRUPO_RH,
			prioridade=t.ALTA if cint(x.bloqueia_fechamento) else t.NORMAL,
			origem_doctype="Tarefa Secullum",
			origem_nome=x.name,
			link_origem=f"/app/tarefa-secullum/{x.name}",
		)
		abertas.add(x.name)
	return abertas


def _fechamentos() -> set[str]:
	abertos = set()
	for x in frappe.get_all("Fechamento de Ponto", filters={"docstatus": 0}, fields=["name"]):
		doc = frappe.get_doc("Fechamento de Ponto", x.name)
		bloqueios = doc.bloqueios()
		if not bloqueios:
			continue
		competencia = f"{getdate(doc.periodo_fim):%m/%Y}"
		garantir(
			FECHAMENTO,
			doc.name,
			_("Destravar o fechamento de {0} ({1}): {2} pendência(s)").format(
				competencia, doc.company, len(bloqueios)
			),
			descricao="\n".join(f"• {strip}" for strip in (frappe.utils.strip_html(b) for b in bloqueios)),
			responsavel_tipo=t.GRUPO_RH,
			prioridade=t.ALTA,
			company=doc.company,
			origem_doctype="Fechamento de Ponto",
			origem_nome=doc.name,
			link_origem=f"/app/fechamento-de-ponto/{doc.name}",
		)
		abertos.add(doc.name)
	return abertos


def _inconsistencias_alta(dias: int) -> set[str]:
	"""Um cartão por colaborador com inconsistência Alta aberta há `dias` dias úteis (contados da criação)."""
	hoje = getdate()
	por_colaborador: dict[str, list] = {}
	for x in frappe.get_all(
		"Inconsistencia de Ponto",
		filters={"status": "Aberta", "severidade": "Alta"},
		fields=["name", "employee", "employee_name", "company", "data", "creation"],
	):
		if x.employee:
			por_colaborador.setdefault(x.employee, []).append(x)
	abertas = set()
	for employee, linhas in por_colaborador.items():
		mais_antiga = min(getdate(x.creation) for x in linhas)
		if t.dias_uteis_entre(mais_antiga, hoje) < dias:
			continue
		primeira = min(linhas, key=lambda x: getdate(x.data))
		company = primeira.company
		chave = f"{employee}:{mais_antiga}"
		datas = sorted({getdate(x.data) for x in linhas})
		garantir(
			INCONSISTENCIA,
			chave,
			_("Tratar o ponto de {0} ({1} dia(s) com pendência Alta)").format(
				primeira.employee_name, len(datas)
			),
			descricao=_("Dias: {0}.").format(", ".join(f"{d:%d/%m}" for d in datas[:15])),
			responsavel_tipo=t.GRUPO_GESTORES if tf.gestores_da_unidade(company) else t.GRUPO_RH,
			company=company,
			employee=employee,
			link_origem=f"/ponto/cartao/{employee}",
		)
		abertas.add(chave)
	return abertas


def sincronizar() -> dict:
	"""Job de hora em hora: cria e fecha os cartões das fontes ligadas."""
	cfg = frappe.get_cached_doc(tf.CONFIG)
	fontes = []
	if cint(cfg.auto_tarefa_secullum):
		fontes.append((SECULLUM, _tarefas_secullum))
	if cint(cfg.auto_fechamento):
		fontes.append((FECHAMENTO, _fechamentos))
	if cint(cfg.auto_inconsistencia_alta):
		dias = cint(cfg.dias_inconsistencia) if cfg.dias_inconsistencia is not None else 2
		fontes.append((INCONSISTENCIA, lambda: _inconsistencias_alta(dias)))
	resultado = {}
	for tipo, ler in fontes:
		frappe.db.savepoint(f"tarefas_{tipo}")
		try:
			abertas = ler()
			resultado[tipo] = {"abertas": len(abertas), "fechadas": fechar_resolvidos(tipo, abertas)}
		except Exception:
			frappe.db.rollback(save_point=f"tarefas_{tipo}")
			frappe.log_error(title=f"Quadro de tarefas: {tipo}")
	return resultado
