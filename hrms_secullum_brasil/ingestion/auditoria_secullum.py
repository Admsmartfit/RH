"""Auditoria dos horários do Secullum (docs/PRD-sincronizacao-secullum.md, SS-2). A regra pura fica em
integrations/secullum/auditoria_horarios.py; aqui: ler os horários em uso (GET), abrir/atualizar as Tarefas
Secullum com o passo a passo e conferir quando o RH marca "Feita".
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from hrms_secullum_brasil.ingestion.coleta_batidas import bancos_configurados
from hrms_secullum_brasil.ingestion.secullum import get_client, id_banco_da_empresa, integracao_ativa
from hrms_secullum_brasil.integrations.secullum import auditoria_horarios as au

CONFIG = "Configuracao Secullum"
TAREFA = "Tarefa Secullum"
PAPEIS = ("System Manager", "RH Ponto")
ABERTAS = ("Pendente", "Feita (RH)", "Divergente")


def horarios_em_uso() -> dict[tuple[str, int], bool]:
	"""(banco, nº do horário) usados por colaboradores ativos → é horário de horista?"""
	saida: dict[tuple[str, int], bool] = {}
	for linha in frappe.db.sql(
		"""select e.company, p.numero_horario_secullum n, p.tipo
		from tabEmployee e join `tabPerfil de Jornada` p on p.name = e.perfil_jornada
		where e.status = 'Active' and ifnull(p.numero_horario_secullum, 0) > 0""",
		as_dict=True,
	):
		chave = (id_banco_da_empresa(linha.company), cint(linha.n))
		saida[chave] = saida.get(chave, False) or linha.tipo == "Horista"
	return saida


def _upsert(achado: au.Achado, banco: str, numero: int) -> str:
	codigo = f"{banco}-{achado.codigo}"
	nome = frappe.db.get_value(TAREFA, {"codigo": codigo})
	doc = frappe.get_doc(TAREFA, nome) if nome else frappe.new_doc(TAREFA)
	if nome and doc.situacao in ("Verificada", "Não verificável", "Dispensada"):
		doc.situacao = "Divergente" if doc.situacao == "Verificada" else doc.situacao
	doc.update(
		{
			"titulo": f"Horário {numero}: {achado.titulo}"[:140],
			"tipo": "ajustar_horario",
			"codigo": codigo,
			"horario_numero": numero,
			"id_banco": banco,
			"atual": achado.atual[:140],
			"esperado": achado.esperado[:140],
			"passos": "\n".join(f"{i}. {p}" for i, p in enumerate(achado.passos, start=1)),
			"valores_esperados": json.dumps(achado.esperados, ensure_ascii=False, indent=1),
			"bloqueia_fechamento": int(achado.bloqueia_fechamento),
			"verificavel": int(achado.verificavel),
		}
	)
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


def auditar() -> dict | None:
	"""Job noturno: tarefas novas para cada diferença; as que sumiram no Secullum viram Verificada."""
	if not integracao_ativa():
		return None
	em_uso = horarios_em_uso()
	vistos, abertas, erros = set(), 0, []
	for banco in {b for b, _n in em_uso} or set(bancos_configurados()):
		try:
			horarios = {cint(h.get("Numero")): h for h in get_client(banco).listar_horarios()}
		except Exception as exc:  # erro operacional não derruba o job
			erros.append(f"banco {banco}: {exc}")
			continue
		for (b, numero), horista in em_uso.items():
			if b != banco or numero not in horarios:
				continue
			for achado in au.auditar(horarios[numero], au.Esperado(horista=horista)):
				vistos.add(f"{banco}-{achado.codigo}")
				_upsert(achado, banco, numero)
				abertas += 1
	for t in frappe.get_all(
		TAREFA, filters={"tipo": "ajustar_horario", "situacao": ["in", ABERTAS]}, fields=["name", "codigo"]
	):
		if t.codigo not in vistos and not erros:
			frappe.db.set_value(
				TAREFA,
				t.name,
				{"situacao": "Verificada", "divergencia": _("Corrigido no Secullum (auditoria).")},
			)
	resumo = _("{0} horário(s) em uso; {1} ajuste(s) pendente(s).").format(len(em_uso), abertas)
	if erros:
		resumo += " " + "; ".join(erros)[:500]
	frappe.db.set_single_value(
		CONFIG, {"ultima_auditoria": now_datetime(), "ultima_auditoria_resumo": resumo}
	)
	return {"horarios": len(em_uso), "ajustes": abertas, "erros": erros}


@frappe.whitelist()
def auditar_agora() -> str:
	frappe.only_for(PAPEIS)
	r = auditar()
	if r is None:
		return _("Integração com o Secullum desativada.")
	return frappe.db.get_single_value(CONFIG, "ultima_auditoria_resumo")


@frappe.whitelist()
def marcar_feita(tarefa: str) -> str:
	"""RH fez no Secullum: o programa relê e confirma (ou pede o print, quando a API não lê)."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(TAREFA, tarefa)
	doc.update({"confirmado_por": frappe.session.user, "confirmado_em": now_datetime()})
	esperados = json.loads(doc.valores_esperados or "[]")
	if not cint(doc.verificavel) or not esperados:
		if not doc.evidencia:
			frappe.throw(
				_("Esta alteração o programa não consegue ler pela API: anexe o print da tela do Secullum.")
			)
		doc.situacao = "Não verificável"
		doc.divergencia = None
	else:
		banco = doc.id_banco or id_banco_da_empresa(None)
		horario = next(
			(
				h
				for h in get_client(banco).listar_horarios()
				if cint(h.get("Numero")) == cint(doc.horario_numero)
			),
			None,
		)
		faltas = au.divergencias(horario, esperados)
		doc.situacao = "Divergente" if faltas else "Verificada"
		doc.divergencia = "\n".join(faltas) or None
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.situacao


@frappe.whitelist()
def dispensar(tarefa: str, motivo: str) -> str:
	"""RH decide não fazer (ex.: aviso que não muda valor): fica registrado com o motivo."""
	frappe.only_for(PAPEIS)
	if not (motivo or "").strip():
		frappe.throw(_("Informe o motivo."))
	frappe.db.set_value(
		TAREFA,
		tarefa,
		{
			"situacao": "Dispensada",
			"observacao": motivo,
			"confirmado_por": frappe.session.user,
			"confirmado_em": now_datetime(),
		},
	)
	return "Dispensada"
