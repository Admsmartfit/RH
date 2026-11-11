"""Planejador, aba "Modelo da rede" (docs/PRD-modelo-rede.md): a escala de hoje (ou uma simulação) contra o modelo
da rede (ex.: o da Smart), com o que muda para cada instrutor.

Só simulação: lê o cadastro, a escala e o `Modelo de Escala da Rede`; grava no máximo uma nova simulação
(`Planejamento de Escala`, com `criar_simulacao`). Nunca grava Escala Mensal, Rascunho de Escala nem contrato. A regra
é do engine (`engine/planejador/modelo_rede.py`); só o administrador, como o resto do planejador.
"""

from datetime import date

import frappe
from frappe import _
from frappe.utils import cint

from hrms_secullum_brasil.apuracao import planejamento_escala as pe
from hrms_secullum_brasil.engine.planejador import modelo_rede as mr
from hrms_secullum_brasil.engine.planejador import montagem as mo

DOCTYPE = "Modelo de Escala da Rede"


def do_documento(doc) -> dict:
	"""O documento no formato do engine (minutos e dias da semana)."""
	semanas = cint(doc.semanas_ciclo) or 1
	vagas = []
	for linha in doc.vagas:
		vagas.append(
			{
				"vaga": (linha.vaga or "").strip(),
				"inicio": pe.mo_hora(str(linha.inicio or "0:00")),
				"fim": pe.mo_hora(str(linha.fim or "0:00")),
				"folgas": [mr.ler_dias(linha.get(f"folgas_semana_{n}") or "") for n in range(1, semanas + 1)],
			}
		)
	return {"nome": doc.nome_modelo, "inicio_ciclo": str(doc.inicio_ciclo or ""), "vagas": vagas}


def _modelo(nome: str) -> dict:
	if not nome or not frappe.db.exists(DOCTYPE, nome):
		frappe.throw(_("Escolha o modelo da rede."))
	return do_documento(frappe.get_doc(DOCTYPE, nome))


def _grade_real(plano: dict) -> dict:
	"""A escala de hoje de cada pessoa do cadastro no mês (Escala Mensal com as trocas, senão o perfil); quem não é do
	cadastro (estagiário previsto) fica no padrão."""
	from hrms_secullum_brasil.configuracao_ponto.escala import dia_da_escala
	from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente

	grade = {}
	for m in plano["equipe"]:
		if not m.get("employee"):
			grade[m["id"]] = mo.grade_padrao(plano, m)
			continue
		grade[m["id"]] = {}
		for dia in mo.datas_do_plano(plano):
			perfil = get_perfil_vigente(m["employee"], dia)
			turno = None
			if perfil:
				jornada, _repouso = dia_da_escala(m["employee"], dia, perfil)
				if jornada.periodos:
					turno = mo.celula(jornada.periodos[0].inicio, jornada.periodos[-1].fim)
			grade[m["id"]][dia.isoformat()] = turno
	return grade


def plano_atual(company: str, ano: int, mes: int, base: str | None = None) -> dict:
	"""O ponto de partida: a simulação escolhida ou, sem ela, a escala de hoje da unidade."""
	if base:
		doc = pe._doc(base)
		if doc.company not in pe._empresas(company):
			frappe.throw(_("A simulação {0} é de outra unidade.").format(base))
		return pe._plano(doc)
	equipe, _relatorio = pe.montar_equipe(company, ano, mes)
	plano = {
		"ano": ano,
		"mes": mes,
		"parametros": {"feriados": pe._feriados(company, ano, mes)},
		"equipe": equipe,
		"grade": {},
	}
	plano["grade"] = _grade_real(plano)
	return plano


def _fixos(valor) -> dict:
	fixos = pe._json(valor, {}) or {}
	return {k: (None if v in (None, "", "reforco") else cint(v)) for k, v in fixos.items()}


def _montar(company, ano, mes, modelo, base=None, fixos=None, vagas_previstas=0):
	pe._checar()
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Escolha a unidade."))
	ano, mes = cint(ano), cint(mes)
	if not (1 <= mes <= 12) or ano < 2020:
		frappe.throw(_("Mês inválido."))
	dados = _modelo(modelo)
	erros = mr.erros_do_modelo(dados)
	if erros:
		frappe.throw("<br>".join(erros))
	atual = plano_atual(company, ano, mes, base)
	encaixe = mr.encaixar(dados, atual["equipe"], _fixos(fixos))
	no_modelo = mr.aplicar(atual, dados, encaixe, bool(cint(vagas_previstas)))
	return dados, atual, encaixe, no_modelo


@frappe.whitelist()
def modelos() -> list[dict]:
	pe._checar()
	return frappe.get_all(
		DOCTYPE,
		filters={"ativo": 1},
		fields=["name", "nome_modelo", "semanas_ciclo", "inicio_ciclo"],
		order_by="nome_modelo asc",
	)


@frappe.whitelist()
def comparar(company: str, ano, mes, modelo: str, base=None, fixos=None, vagas_previstas=0) -> dict:
	"""A escala de hoje (ou a simulação `base`) contra o modelo: encaixe pelo horário mais perto (ou o que o gestor
	escolheu em `fixos`), as duas grades, o que muda por pessoa e dia e os totais. Só leitura."""
	dados, atual, encaixe, no_modelo = _montar(company, ano, mes, modelo, base, fixos, vagas_previstas)
	comparacao = mr.comparar(atual, no_modelo, dados, encaixe)
	return {
		"modelo": {
			**dados,
			"vagas": [
				{
					**v,
					"horario": f"{mo.hhmm(v['inicio'])} às {mo.hhmm(v['fim'])}",
					"folgas_texto": [mr.texto_dias(f) for f in v["folgas"]],
				}
				for v in dados["vagas"]
			],
			"avisos": mr.avisos_do_modelo(dados),
		},
		"ciclo": mr.ciclo_no_mes(dados, cint(ano), cint(mes)),
		"semanas": [[dia.isoformat() for dia in s] for s in mo.semanas_do_mes(cint(ano), cint(mes))],
		"encaixe": encaixe,
		"atual": atual,
		"no_modelo": no_modelo,
		**comparacao,
	}


@frappe.whitelist()
def criar_simulacao(
	company: str, ano, mes, modelo: str, base=None, fixos=None, vagas_previstas=0, titulo: str | None = None
) -> dict:
	"""Grava a escala no modelo como uma nova simulação (aba Montar escala), para ajustar e imprimir."""
	_dados, _atual, _encaixe, no_modelo = _montar(company, ano, mes, modelo, base, fixos, vagas_previstas)
	doc = frappe.get_doc(
		{
			"doctype": pe.DOCTYPE,
			"titulo": titulo or _("{0} - {1:02d}/{2}").format(modelo, cint(mes), cint(ano)),
			"company": company,
			"empresas": " + ".join(pe._empresas(company)),
			"ano": cint(ano),
			"mes": cint(mes),
			"origem": base or None,
		}
	)
	pe._gravar(doc, no_modelo)
	doc.insert()
	return {"name": doc.name}


def criar_modelo_smart() -> str:
	"""O modelo dos slides da Smart (patch `modelo_smart`); não mexe se já existir (o RH pode ter editado)."""
	nome = mr.MODELO_SMART["nome"]
	if frappe.db.exists(DOCTYPE, nome):
		return nome
	vagas = []
	for v in mr.MODELO_SMART["vagas"]:
		linha = {"vaga": v["vaga"], "inicio": mo.hhmm(v["inicio"]), "fim": mo.hhmm(v["fim"])}
		for n, folgas in enumerate(v["folgas"], 1):
			linha[f"folgas_semana_{n}"] = mr.texto_dias(folgas)
		vagas.append(linha)
	frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"nome_modelo": nome,
			"semanas_ciclo": mr.ciclo(mr.MODELO_SMART),
			"inicio_ciclo": date.fromisoformat(mr.MODELO_SMART["inicio_ciclo"]),
			"vagas": vagas,
			"descricao": _("Slides 'Análise de cenários' da Smart: 7 professores, folgas em 3 semanas."),
		}
	).insert(ignore_permissions=True)
	return nome
