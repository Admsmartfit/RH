"""Planejador de escalas 5x2 no Frappe (docs/PRD-planejador-5x2.md, PE-02 a PE-11). É **só simulação** (DP-9):
lê pessoas, escala de hoje, batidas, indisponibilidades, custos e o regime de jornada; roda o otimizador em fila; e
mostra as propostas, o mapa de calor e a lista do que mudar. O gestor lança à mão na tela Escalas (nunca gravamos
escala, rascunho ou alteração de jornada daqui).
"""

import csv
import io
import json
from datetime import date, timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import TRABALHO, DiaEscala, limite_domingos
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.planejador import avaliacao as av
from hrms_secullum_brasil.engine.planejador import demanda as dm
from hrms_secullum_brasil.engine.planejador import indice as ix
from hrms_secullum_brasil.engine.planejador.modelos import (
	ESTAGIARIO,
	FAIXAS,
	HORISTA,
	MENSALISTA,
	Horizonte,
	Indisponivel,
	Pessoa,
	Premissas,
	Regras,
	Turno,
	ler_hora,
)

DOCTYPE = "Simulacao de Escala"
# RH, 04/11/2026: o planejador é só do administrador (System Manager); RH e gestores não o veem
PAPEIS = ("System Manager",)
CARGO_PADRAO = "INSTRUTOR"  # instrutor de musculação (DP-15)


# ------------------------------------------------------------------ apoio


def _checar():
	frappe.only_for(PAPEIS)


def _e_admin() -> bool:
	from hrms_secullum_brasil.utils.acesso import e_administrador

	return e_administrador()


def _empresas_visiveis() -> list[str] | None:
	visiveis = employees_visiveis()
	if visiveis is None:
		return None
	return sorted(
		{
			c
			for c in frappe.get_all("Employee", filters={"name": ["in", visiveis or [""]]}, pluck="company")
			if c
		}
	)


def _checar_empresa(company: str) -> None:
	empresas = _empresas_visiveis()
	if empresas is not None and company not in empresas:
		frappe.throw(_("Sem acesso à empresa {0}.").format(company), frappe.PermissionError)


def _json(texto, padrao):
	if not texto:
		return padrao
	return frappe.parse_json(texto) if isinstance(texto, str) else texto


def _turno_de_periodos(periodos) -> Turno | None:
	if not periodos:
		return None
	inicio, fim = periodos[0].inicio, periodos[-1].fim
	trabalho = sum(p.fim - p.inicio for p in periodos)
	return Turno(inicio, fim, (fim - inicio) - trabalho)


def _turno_json(t) -> Turno | None:
	return Turno(*t) if t else None


# ------------------------------------------------------------------ premissas (PE-05)


def premissas_de(dados: dict) -> Premissas:
	dados = dados or {}
	travas = tuple(
		(t["pessoa"], cint(t["dia"]), _turno_json(t.get("turno"))) for t in dados.get("travas") or []
	)
	return Premissas(
		teto_horista=cint(dados.get("teto_horista") or 240),
		ampliar=dados.get("ampliar") or "indice",
		indice_minimo=cint(dados.get("indice_minimo") if dados.get("indice_minimo") is not None else 70),
		lista_ampliar=tuple(dados.get("lista_ampliar") or ()),
		max_ampliacoes=cint(dados.get("max_ampliacoes") if dados.get("max_ampliacoes") is not None else 99),
		usar_estagiarios=bool(dados.get("usar_estagiarios", True)),
		cota_estagiario_pct=cint(dados.get("cota_estagiario_pct") or 30),
		budget_pct=None if dados.get("budget_pct") in (None, "") else flt(dados.get("budget_pct")),
		peso_cobertura=cint(dados.get("peso_cobertura") or 5),
		peso_custo=cint(dados.get("peso_custo") or 5),
		peso_estabilidade=cint(
			dados.get("peso_estabilidade") if dados.get("peso_estabilidade") is not None else 3
		),
		contratar=bool(dados.get("contratar")),
		custo_vaga_hora=Decimal(str(flt(dados.get("custo_vaga_hora")))),
		max_vagas=cint(dados.get("max_vagas") or 3),
		nao_mexer=tuple(dados.get("nao_mexer") or ()),
		travas=travas,
		usar_compensacao=bool(dados.get("usar_compensacao")),
		teto_semanal_horista=round(flt(dados.get("teto_semanal_horista") or 40) * 60),
	)


@frappe.whitelist()
def opcoes() -> dict:
	"""Empresas, cargos, regimes e as premissas padrão da tela."""
	_checar()
	empresas = _empresas_visiveis()
	filtros = {"status": "Active"}
	if empresas is not None:
		filtros["company"] = ["in", empresas or [""]]
	cargos = sorted({c for c in frappe.get_all("Employee", filters=filtros, pluck="designation") if c})
	regimes = (
		frappe.get_all(
			"Regime de Jornada Legal",
			fields=["name", "situacao", "carga_semanal_horas", "inicio", "inicio_previsto"],
			order_by="carga_semanal_horas desc",
		)
		if frappe.db.table_exists("Regime de Jornada Legal")
		else []
	)
	hoje = getdate(today())
	return {
		"empresas": empresas if empresas is not None else sorted(frappe.get_all("Company", pluck="name")),
		"cargos": cargos,
		"cargo_padrao": CARGO_PADRAO if CARGO_PADRAO in cargos else (cargos[0] if cargos else None),
		"regimes": regimes,
		"inicio_padrao": str(hoje + timedelta(days=7 - hoje.weekday())),
		"premissas": {
			"teto_horista": 240,
			"ampliar": "indice",
			"indice_minimo": 70,
			"lista_ampliar": [],
			"max_ampliacoes": 99,
			"usar_estagiarios": True,
			"cota_estagiario_pct": 30,
			"budget_pct": 15,
			"peso_cobertura": 5,
			"peso_custo": 5,
			"peso_estabilidade": 3,
			"contratar": False,
			"custo_vaga_hora": 0,
			"max_vagas": 3,
			"nao_mexer": [],
			"travas": [],
			"usar_compensacao": False,
			"teto_semanal_horista": 40,
		},
		"otimizador": _tem_otimizador(),
	}


def _tem_otimizador() -> bool:
	from hrms_secullum_brasil import otimizacao

	return otimizacao.tem_otimizador()


# ------------------------------------------------------------------ leitura dos dados (PE-02, PE-03)


def regras_da_simulacao(sim, employee_referencia: str | None = None) -> Regras:
	"""O regime escolhido na simulação (mesmo só preparado) ou o ativo no início; a compensação vem da CCT (DP-11)."""
	from hrms_secullum_brasil.configuracao_ponto import regime_jornada as rg
	from hrms_secullum_brasil.configuracao_ponto.regras import RegraAmbiguaError, get_regra_vigente

	inicio = getdate(sim.inicio)
	if sim.regime:
		r = rg._para_engine(frappe.get_doc("Regime de Jornada Legal", sim.regime))
	else:
		r = rg.regime_na_data(inicio)
	compensada = 0
	if employee_referencia:
		try:
			cct = get_regra_vigente(employee_referencia, inicio)
		except RegraAmbiguaError:
			cct = None
		if cct and cint(cct.get("compensacao_jornada")):
			compensada = cint(cct.get("jornada_diaria_compensada_min"))
	return Regras(
		teto_semanal=r.semanal_min,
		folgas_semana=r.folgas_semana,
		repousos=r.repousos_remunerados,
		diaria_legal=r.diaria_min,
		diaria_compensada=compensada,
		regime=r.nome,
	)


def _colaboradores(company: str, designation: str, inicio: date) -> list:
	filtros = {"status": "Active", "company": company}
	instrutores = frappe.get_all(
		"Employee",
		filters={**filtros, "designation": designation},
		fields=[
			"name",
			"employee_name",
			"tipo_remuneracao",
			"gender",
			"cref_numero",
			"cref_validade",
			"minimo_horas",
			"minimo_periodo",
		],
		order_by="employee_name asc",
	)
	estagiarios = frappe.get_all(
		"Employee",
		filters={**filtros, "tipo_remuneracao": "Estagiario", "designation": ["!=", designation]},
		fields=[
			"name",
			"employee_name",
			"tipo_remuneracao",
			"gender",
			"cref_numero",
			"cref_validade",
			"minimo_horas",
			"minimo_periodo",
		],
		order_by="employee_name asc",
	)
	visiveis = employees_visiveis()
	todos = instrutores + estagiarios
	return [e for e in todos if visiveis is None or e.name in visiveis]


def _historico_indice(employee: str, hoje: date) -> ix.Historico:
	inicio = hoje - timedelta(days=90)
	apuracoes = frappe.get_all(
		"Apuracao Diaria",
		filters={"employee": employee, "data": ["between", [inicio, hoje]]},
		fields=["previsto", "falta", "atraso"],
	)
	respostas = frappe.get_all(
		"Convite de Turno Resposta",
		filters={"employee": employee, "respondido_em": [">=", inicio]},
		pluck="resposta",
	)
	return ix.Historico(
		dias_previstos=sum(1 for a in apuracoes if cint(a.previsto)),
		faltas=sum(1 for a in apuracoes if cint(a.falta)),
		atraso_minutos=sum(cint(a.atraso) for a in apuracoes),
		inconsistencias=frappe.db.count(
			"Inconsistencia de Ponto", {"employee": employee, "data": ["between", [inicio, hoje]]}
		),
		convites_respondidos=sum(1 for r in respostas if r in ("Posso", "Não posso")),
		convites_aceitos=sum(1 for r in respostas if r == "Posso"),
		informou_disponibilidade=bool(
			frappe.db.exists(
				"Indisponibilidade",
				{"employee": employee, "origem": "Colaborador", "creation": [">=", inicio]},
			)
		),
	)


def _domingos_antes(employee: str, inicio: date, hoje: date) -> int:
	"""Domingos trabalhados seguidos logo antes do horizonte (realizado no passado, escala no futuro)."""
	from hrms_secullum_brasil.apuracao.cockpit_escala import dias_do_colaborador, realizados

	ini = inicio - timedelta(days=42)
	fim = inicio - timedelta(days=1)
	escala = {d.data: d for d in dias_do_colaborador(employee, ini, fim)}
	escala.update(realizados(employee, ini, fim, hoje))
	seguidos = 0
	for domingo in sorted((d for d in escala if d.weekday() == 6), reverse=True):
		if not escala[domingo].trabalho:
			break
		seguidos += 1
	return seguidos


def base_do_realizado(inicio: date, semanas: int, hoje: date) -> date:
	"""Segunda-feira da 1ª das últimas `semanas` semanas inteiras já passadas: o que os instrutores fizeram de fato vira
	a "escala de hoje" do planejador (a escala do horista é flexível; o real é o ponto — RH, 30/10/2026)."""
	fim = min(inicio, hoje) - timedelta(days=1)
	ultimo_domingo = fim - timedelta(days=(fim.weekday() + 1) % 7)
	return ultimo_domingo - timedelta(days=6 + 7 * (semanas - 1))


def pessoas_da_simulacao(sim, horizonte: Horizonte, regras: Regras, premissas: Premissas) -> list[Pessoa]:
	from hrms_secullum_brasil.apuracao.cockpit_escala import realizados
	from hrms_secullum_brasil.configuracao_ponto.turnos import indisponibilidades
	from hrms_secullum_brasil.estagio.tce import get_tce_vigente
	from hrms_secullum_brasil.payroll_handoff.fechamento import base_para_custo, salario_vigente

	inicio, fim = horizonte.datas[0], horizonte.datas[-1]
	hoje = getdate(today())
	empresa = frappe.get_cached_value(
		"Company", sim.company, ["domingos_seguidos_mulher", "domingos_seguidos_homem"], as_dict=True
	)
	from hrms_secullum_brasil.engine import defaults_legais as d

	saida = []
	for e in _colaboradores(sim.company, sim.designation, inicio):
		tipo = {"Mensalista": MENSALISTA, "Estagiario": ESTAGIARIO}.get(e.tipo_remuneracao, HORISTA)
		base = base_do_realizado(inicio, horizonte.n_semanas, hoje)
		feitos = realizados(e.name, base, base + timedelta(days=len(horizonte.datas) - 1), hoje)
		atual = tuple(
			_turno_de_periodos(feitos[d].periodos) if d in feitos and feitos[d].trabalho else None
			for d in (base + timedelta(days=i) for i in horizonte.dias)
		)
		maiores = [t.minutos for t in atual if t]
		custo = base_para_custo(e.name, inicio)
		indisponivel = []
		for ind in indisponibilidades(e.name, inicio, fim):
			for i, data in enumerate(horizonte.datas):
				if ind.inicio <= data <= ind.fim:
					p = ind.periodo
					indisponivel.append(Indisponivel(i, p.inicio if p else 0, p.fim if p else 1440))
		diaria_max, semanal_max, salario = 24 * 60, 7 * 24 * 60, Decimal(0)
		if tipo == ESTAGIARIO:
			tce = get_tce_vigente(e.name, inicio)
			if not tce:
				continue  # sem TCE vigente o estagiário não pode ser escalado
			diaria_max, semanal_max = cint(tce.carga_diaria) or 360, cint(tce.carga_semanal) or 1800
			salario = Decimal(str(flt(tce.bolsa)))
		elif tipo == MENSALISTA:
			salario = salario_vigente(e.name, inicio) or Decimal(0)
		semanal_min = 0
		if tipo == HORISTA and flt(e.minimo_horas) and e.minimo_periodo == "Semana":
			semanal_min = round(flt(e.minimo_horas) * 60)
		if tipo == HORISTA:
			semanal_max = min(semanal_max, premissas.teto_semanal_horista)
		cref = bool(e.cref_numero) and (not e.cref_validade or getdate(e.cref_validade) >= inicio)
		saida.append(
			Pessoa(
				id=e.name,
				nome=e.employee_name,
				tipo=tipo,
				genero=e.gender or "",
				cref=cref and tipo != ESTAGIARIO,
				custo_hora=custo.valor_hora,
				salario_mensal=salario,
				diaria_atual=max(maiores)
				if maiores
				else (240 if tipo == HORISTA else d.JORNADA_DIARIA_MAXIMA_MIN),
				diaria_max=diaria_max,
				semanal_max=semanal_max,
				semanal_min=semanal_min,
				indisponivel=tuple(indisponivel),
				atual=atual,
				limite_domingos=limite_domingos(
					e.gender,
					cint(empresa.domingos_seguidos_mulher) or d.DOMINGOS_SEGUIDOS_MULHER,
					cint(empresa.domingos_seguidos_homem) or d.DOMINGOS_SEGUIDOS_HOMEM,
				),
				domingos_seguidos_antes=_domingos_antes(e.name, inicio, hoje),
				indice=ix.indice(_historico_indice(e.name, hoje)),
				fixa=e.name in premissas.nao_mexer,
			)
		)
	return saida


def _com_teto(p: Pessoa, regras: Regras) -> Pessoa:
	from dataclasses import replace

	return replace(p, semanal_max=min(p.semanal_max, regras.teto_semanal))


def demanda_da_simulacao(sim, pessoas: list[Pessoa]) -> tuple:
	"""PE-03/DP-14: presença histórica dos instrutores (só quem não é estagiário) + mínimos do gestor."""
	from hrms_secullum_brasil.apuracao.cockpit_escala import realizados

	hoje = getdate(today())
	fim = min(getdate(sim.inicio), hoje) - timedelta(days=1)
	inicio = fim - timedelta(days=7 * max(1, cint(sim.historico_semanas) or 8) - 1)
	presencas: dict[date, list] = {}
	for p in pessoas:
		if p.estagiario:
			continue
		for data, dia in realizados(p.id, inicio, fim, hoje).items():
			if dia.trabalho:
				presencas.setdefault(data, []).extend((x.inicio, x.fim) for x in dia.periodos)
	datas = [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]
	minimos = [
		dm.MinimoGestor(
			tuple(cint(x) for x in m["dias"]),
			ler_hora(m["inicio"]),
			ler_hora(m["fim"]),
			cint(m["quantidade"]),
		)
		for m in _json(sim.minimos, [])
		if m.get("dias") and m.get("inicio") and m.get("fim")
	]
	return dm.curva(presencas, datas, minimos), (str(inicio), str(fim))


def padroes_da_empresa(company: str, designation: str) -> list[Turno]:
	from hrms_secullum_brasil.configuracao_ponto.turnos import turnos_da_empresa

	saida = []
	for t in turnos_da_empresa(company, designation):
		saida.append(_turno_de_periodos(t["periodos"]))
	return [t for t in saida if t]


# ------------------------------------------------------------------ simulação em fila (PE-04)


@frappe.whitelist()
def criar(
	company: str,
	inicio: str,
	designation: str | None = None,
	semanas: int = 4,
	regime=None,
	premissas=None,
	minimos=None,
	historico_semanas: int = 8,
	limite_segundos: int = 30,
) -> dict:
	_checar()
	_checar_empresa(company)
	inicio_d = getdate(inicio)
	inicio_d -= timedelta(days=inicio_d.weekday())
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"company": company,
			"designation": designation or CARGO_PADRAO,
			"inicio": inicio_d,
			"semanas": min(max(1, cint(semanas)), 8),
			"regime": regime or None,
			"historico_semanas": min(max(1, cint(historico_semanas) or 8), 26),
			"limite_segundos": min(max(2, cint(limite_segundos) or 30), 120),
			"premissas": json.dumps(_json(premissas, {}), ensure_ascii=False),
			"minimos": json.dumps(_json(minimos, []), ensure_ascii=False),
		}
	).insert()
	_enfileirar(doc)
	return estado(doc.name)


@frappe.whitelist()
def refazer(nome: str, premissas=None, minimos=None) -> dict:
	"""Roda de novo a mesma simulação (ex.: com células travadas na grade, PE-08)."""
	doc = _doc(nome)
	if premissas is not None:
		doc.db_set("premissas", json.dumps(_json(premissas, {}), ensure_ascii=False))
	if minimos is not None:
		doc.db_set("minimos", json.dumps(_json(minimos, []), ensure_ascii=False))
	_enfileirar(doc)
	return estado(nome)


def _doc(nome: str):
	_checar()
	doc = frappe.get_doc(DOCTYPE, nome)
	_checar_empresa(doc.company)
	return doc


def _chave_parar(nome: str) -> str:
	return f"planejador_parar:{nome}"


def _enfileirar(doc) -> None:
	presa = frappe.utils.time_diff_in_seconds(now_datetime(), doc.modified) > 30 * 60
	if doc.situacao in ("Na fila", "Rodando") and not presa:  # presa = o worker caiu no meio
		frappe.throw(_("A simulação já está rodando."))
	frappe.cache.delete_value(_chave_parar(doc.name))
	doc.db_set({"situacao": "Na fila", "progresso": 0, "etapa": _("Na fila"), "erro": None})
	frappe.enqueue(
		"hrms_secullum_brasil.apuracao.planejador.rodar",
		queue="long",
		timeout=1800,
		now=bool(frappe.in_test),
		nome=doc.name,
	)


def _parada(nome: str):
	"""O "parar" é consultado pelas threads do CP-SAT, onde o `frappe.local` não existe: Redis direto, com a chave
	montada aqui."""
	import redis

	chave = frappe.cache.make_key(_chave_parar(nome))
	cliente = redis.Redis.from_url(frappe.conf.redis_cache)
	return lambda: bool(cliente.exists(chave))


@frappe.whitelist()
def parar(nome: str) -> dict:
	"""O otimizador devolve a melhor solução até aqui (PE-04)."""
	_doc(nome)
	frappe.cache.set_value(_chave_parar(nome), 1, expires_in_sec=3600)
	return estado(nome)


def rodar(nome: str) -> None:
	from hrms_secullum_brasil import otimizacao

	doc = frappe.get_doc(DOCTYPE, nome)
	doc.db_set({"situacao": "Rodando", "etapa": _("Lendo o ponto e a escala"), "progresso": 5})
	frappe.db.commit()
	frappe.db.savepoint("planejador_rodar")
	try:
		horizonte = Horizonte.semanas(getdate(doc.inicio), cint(doc.semanas) or 4)
		premissas = premissas_de(_json(doc.premissas, {}))
		regras = regras_da_simulacao(doc)
		pessoas = pessoas_da_simulacao(doc, horizonte, regras, premissas)
		if not pessoas:
			frappe.throw(_("Nenhum colaborador do cargo {0} na empresa.").format(doc.designation))
		regras = regras_da_simulacao(doc, pessoas[0].id)
		pessoas = [p if p.estagiario else _com_teto(p, regras) for p in pessoas]
		demanda, historico = demanda_da_simulacao(doc, pessoas)
		padroes = padroes_da_empresa(doc.company, doc.designation)

		def progresso(feitas, total, titulo):
			doc.db_set(
				{
					"progresso": 10 + int(85 * feitas / max(1, total)),
					"etapa": _("Proposta: {0}").format(titulo) if titulo else _("Conferindo"),
				},
				update_modified=False,
			)
			frappe.db.commit()

		resultado = otimizacao.gerar_propostas(
			pessoas,
			horizonte,
			regras,
			demanda,
			premissas,
			padroes,
			limite_s=cint(doc.limite_segundos) or 30,
			parar=_parada(nome),
			progresso=progresso,
		)
		_conferir_no_cockpit(resultado, pessoas, horizonte)
		resultado.update(
			{
				"regras": {
					"regime": regras.regime,
					"teto_semanal_h": round(regras.teto_semanal / 60, 2),
					"folgas_semana": regras.folgas_semana,
					"repousos": regras.repousos,
					"diaria_compensada": regras.diaria_compensada,
				},
				"historico": historico,
				"base_hoje": [
					str(base_do_realizado(horizonte.datas[0], horizonte.n_semanas, getdate(today()))),
					str(
						base_do_realizado(horizonte.datas[0], horizonte.n_semanas, getdate(today()))
						+ timedelta(days=len(horizonte.datas) - 1)
					),
				],
				"faixas": [{"faixa": f, "texto": f"{f * 30 // 60:02d}:{f * 30 % 60:02d}"} for f in FAIXAS],
				"indices": {p.id: p.indice for p in pessoas},
				"premissas": _json(doc.premissas, {}),
			}
		)
		parado = bool(frappe.cache.get_value(_chave_parar(nome)))
		doc.db_set(
			{
				"resultado": json.dumps(resultado, ensure_ascii=False, default=str),
				"situacao": "Parada" if parado else "Pronta",
				"progresso": 100,
				"etapa": _("Parada: melhores soluções até aqui") if parado else _("Pronta"),
				"rodada_em": now_datetime(),
			}
		)
	except Exception as exc:
		frappe.db.rollback(save_point="planejador_rodar")
		frappe.log_error(title=f"Planejador {nome}")
		doc.db_set({"situacao": "Erro", "erro": frappe.utils.strip_html(str(exc))[:1000], "etapa": _("Erro")})
	frappe.db.commit()


def _conferir_no_cockpit(resultado: dict, pessoas: list[Pessoa], horizonte: Horizonte) -> None:
	"""DP-5: cada proposta também passa pela validação de sempre do cockpit (as quebras que bloqueiam e as que
	pedem justificativa), com os parâmetros de cada colaborador (CCT, domingos, feriados, indisponibilidades)."""
	from hrms_secullum_brasil.apuracao.cockpit_escala import parametros

	inicio, fim = horizonte.datas[0], horizonte.datas[-1]
	params = {p.id: parametros(p.id, inicio, fim) for p in pessoas}
	for proposta in resultado["propostas"]:
		quebras = []
		for pid, turnos in proposta["escala"].items():
			if pid not in params:
				continue  # vaga sugerida
			dias = []
			for i, t in enumerate(turnos):
				turno = _turno_json(t)
				dias.append(
					DiaEscala(horizonte.datas[i], TRABALHO, tuple(Periodo(a, b) for a, b in turno.periodos()))
					if turno
					else DiaEscala(horizonte.datas[i], "Folga")
				)
			nome = next(p.nome for p in pessoas if p.id == pid)
			for q in ev.quebras_da_escala(dias, params[pid]):
				quebras.append(
					{
						"pessoa": nome,
						"data": str(q.data),
						"tipo": q.tipo,
						"mensagem": q.mensagem,
						"gravidade": q.gravidade,
					}
				)
		proposta["quebras_cockpit"] = quebras
		if any(q["gravidade"] == ev.BLOQUEIA for q in quebras):
			proposta["valida"] = False


@frappe.whitelist()
def estado(nome: str) -> dict:
	doc = _doc(nome)
	return {
		"name": doc.name,
		"situacao": doc.situacao,
		"progresso": cint(doc.progresso),
		"etapa": doc.etapa,
		"erro": doc.erro,
	}


@frappe.whitelist()
def resultado(nome: str) -> dict:
	doc = _doc(nome)
	return {
		"name": doc.name,
		"company": doc.company,
		"designation": doc.designation,
		"inicio": str(doc.inicio),
		"semanas": cint(doc.semanas),
		"regime": doc.regime,
		"situacao": doc.situacao,
		"rodada_em": str(doc.rodada_em)[:16] if doc.rodada_em else None,
		"proposta_escolhida": doc.proposta_escolhida,
		"premissas": _json(doc.premissas, {}),
		"minimos": _json(doc.minimos, []),
		"lancados": _json(doc.lancados, []),
		"resultado": _json(doc.resultado, None),
	}


@frappe.whitelist()
def simulacoes(company: str | None = None) -> list[dict]:
	_checar()
	filtros = {}
	if company:
		_checar_empresa(company)
		filtros["company"] = company
	else:
		empresas = _empresas_visiveis()
		if empresas is not None:
			filtros["company"] = ["in", empresas or [""]]
	return frappe.get_all(
		DOCTYPE,
		filters=filtros,
		fields=[
			"name",
			"company",
			"designation",
			"inicio",
			"semanas",
			"situacao",
			"proposta_escolhida",
			"rodada_em",
		],
		order_by="creation desc",
		limit=20,
	)


# ------------------------------------------------------------------ da simulação à escala (PE-10, manual)


def _proposta(doc, codigo: str) -> dict:
	dados = _json(doc.resultado, None)
	proposta = next((p for p in (dados or {}).get("propostas", []) if p["codigo"] == codigo), None)
	if not proposta:
		frappe.throw(_("Proposta {0} não encontrada nesta simulação.").format(codigo))
	return proposta


@frappe.whitelist()
def escolher(nome: str, codigo: str) -> dict:
	"""Guarda qual proposta o gestor escolheu (histórico). Nada é gravado na escala (DP-9)."""
	doc = _doc(nome)
	_proposta(doc, codigo)
	doc.db_set(
		{"proposta_escolhida": codigo, "escolhida_por": frappe.session.user, "escolhida_em": now_datetime()}
	)
	doc.add_comment(
		"Info", _("Proposta {0} escolhida. As mudanças são lançadas à mão na tela Escalas.").format(codigo)
	)
	return resultado(nome)


@frappe.whitelist()
def marcar(nome: str, chave: str, feito: int | str = 1) -> list[str]:
	"""Marca (ou desmarca) uma mudança como já lançada na escala pelo gestor."""
	doc = _doc(nome)
	lancados = set(_json(doc.lancados, []))
	if cint(feito):
		lancados.add(chave)
	else:
		lancados.discard(chave)
	doc.db_set("lancados", json.dumps(sorted(lancados), ensure_ascii=False))
	return sorted(lancados)


@frappe.whitelist()
def exportar(nome: str, codigo: str):
	"""CSV (abre no Excel) com o resumo da proposta e a lista do que mudar."""
	doc = _doc(nome)
	proposta = _proposta(doc, codigo)
	saida = io.StringIO()
	w = csv.writer(saida, delimiter=";")
	w.writerow([f"Simulação {doc.name}", doc.company, f"Proposta {codigo} - {proposta['titulo']}"])
	w.writerow([proposta["resumo"]])
	ind = proposta["indicadores"]
	w.writerow(
		[
			"Custo mensal",
			ind["custo_mensal"],
			"Diferença",
			ind["delta"],
			"Cobertura (%)",
			ind["cobertura_pct"],
			"Déficit (h)",
			ind["deficit_horas"],
		]
	)
	if ind["vagas"]:
		w.writerow(["Vagas sugeridas", ", ".join(ind["vagas"])])
	w.writerow([])
	w.writerow(["Colaborador", "Data", "Dia", "De", "Para", "Motivo", "Lançado"])
	lancados = set(_json(doc.lancados, []))
	for m in proposta["mudancas"]:
		w.writerow(
			[
				m["nome"],
				m["data"],
				m["dia_semana"],
				m["de"],
				m["para"],
				m["motivo"],
				"sim" if m["chave"] in lancados else "",
			]
		)
	frappe.local.response.filename = f"{doc.name}-proposta-{codigo}.csv"
	frappe.local.response.filecontent = "﻿" + saida.getvalue()
	frappe.local.response.type = "download"


@frappe.whitelist()
def consulta_escalas(company: str, inicio: str, fim: str) -> list[dict]:
	"""Painel de consulta da tela Escalas (PE-10): as mudanças das propostas escolhidas que caem no período. Quem
	não é administrador não usa o planejador: nada a consultar."""
	if not _e_admin():
		return []
	_checar_empresa(company)
	ini, fim_d = getdate(inicio), getdate(fim)
	saida = []
	for sim in frappe.get_all(
		DOCTYPE,
		filters={"company": company, "proposta_escolhida": ["is", "set"]},
		fields=["name", "inicio", "semanas", "proposta_escolhida", "resultado", "lancados"],
		order_by="escolhida_em desc",
		limit=5,
	):
		ultimo = getdate(sim.inicio) + timedelta(days=7 * cint(sim.semanas) - 1)
		if ultimo < ini or getdate(sim.inicio) > fim_d:
			continue
		proposta = next(
			(
				p
				for p in (_json(sim.resultado, {}) or {}).get("propostas", [])
				if p["codigo"] == sim.proposta_escolhida
			),
			None,
		)
		if not proposta:
			continue
		lancados = set(_json(sim.lancados, []))
		itens = [
			{**m, "lancado": m["chave"] in lancados}
			for m in proposta["mudancas"]
			if ini <= getdate(m["data"]) <= fim_d
		]
		saida.append(
			{
				"simulacao": sim.name,
				"proposta": sim.proposta_escolhida,
				"titulo": proposta["titulo"],
				"mudancas": itens,
			}
		)
	return saida


# ------------------------------------------------------------------ acompanhamento (PE-11)


@frappe.whitelist()
def acompanhamento(nome: str) -> dict:
	"""Planejado (proposta escolhida) x realizado (batidas) nos dias que já passaram, com os alertas."""
	from hrms_secullum_brasil.apuracao.cockpit_escala import realizados
	from hrms_secullum_brasil.configuracao_ponto import regime_jornada as rg

	doc = _doc(nome)
	if not doc.proposta_escolhida:
		return {"dias": [], "alertas": [], "mensagem": _("Escolha uma proposta para acompanhar.")}
	proposta = _proposta(doc, doc.proposta_escolhida)
	horizonte = Horizonte.semanas(getdate(doc.inicio), cint(doc.semanas) or 4)
	hoje = getdate(today())
	passados = [i for i, d in enumerate(horizonte.datas) if d < hoje]
	if not passados:
		return {"dias": [], "alertas": [], "mensagem": _("O período ainda não começou.")}
	pessoas = {p["id"]: p for p in _json(doc.resultado, {})["pessoas"]}
	planejado = {
		pid: tuple(_turno_json(t) for t in turnos)
		for pid, turnos in proposta["escala"].items()
		if pid in pessoas and not pessoas[pid]["vaga"]
	}
	real: dict[str, list] = {}
	fim = horizonte.datas[passados[-1]]
	for pid in planejado:
		feitos = realizados(pid, horizonte.datas[0], fim, hoje)
		real[pid] = [
			_turno_de_periodos(feitos[d].periodos) if d in feitos and feitos[d].trabalho else None
			for d in horizonte.datas
		]
	dados = _json(doc.resultado, {})
	mapa_plan = {m["data"]: m for m in proposta["mapa"]}
	cob_real = av.cobertura({k: tuple(v) for k, v in real.items()}, horizonte)
	dias, alertas = [], []
	for i in passados:
		data = str(horizonte.datas[i])
		faixas = mapa_plan[data]["faixas"]
		minimo_total = sum(1 for f in faixas if f["minimo"])
		atendidas_plan = sum(1 for f in faixas if f["minimo"] and f["cobertura"] >= f["minimo"])
		atendidas_real = sum(
			1 for f in faixas if f["minimo"] and cob_real.get((i, f["faixa"]), 0) >= f["minimo"]
		)
		dias.append(
			{
				"data": data,
				"planejado_pct": round(100 * atendidas_plan / minimo_total, 1) if minimo_total else 100,
				"realizado_pct": round(100 * atendidas_real / minimo_total, 1) if minimo_total else 100,
			}
		)
	for semana in range(horizonte.n_semanas):
		dias_semana = [i for i in horizonte.dias_da_semana(semana) if i in passados]
		if not dias_semana:
			continue
		teto = rg.teto_semanal(horizonte.datas[7 * semana])
		for pid, turnos in real.items():
			minutos = sum(t.minutos for i in dias_semana if (t := turnos[i]))
			if minutos > teto:
				alertas.append(
					_("{0}: {1}h na semana de {2}, acima do teto do regime.").format(
						pessoas[pid]["nome"],
						round(minutos / 60, 1),
						horizonte.datas[7 * semana].strftime("%d/%m"),
					)
				)
	for pid, turnos in real.items():
		if pessoas[pid]["tipo"] != ESTAGIARIO:
			continue
		for i in passados:
			t = turnos[i]
			if not t:
				continue
			for f in t.faixas():
				supervisores = [
					q
					for q, ts in real.items()
					if q != pid and pessoas[q]["tipo"] != ESTAGIARIO and ts[i] and f in ts[i].faixas()
				]
				if not supervisores:
					alertas.append(
						_("{0}: estagiário sem profissional no salão em {1}.").format(
							pessoas[pid]["nome"], horizonte.datas[i].strftime("%d/%m")
						)
					)
					break
	return {
		"dias": dias,
		"alertas": alertas,
		"planejado_pct": round(sum(d["planejado_pct"] for d in dias) / len(dias), 1),
		"realizado_pct": round(sum(d["realizado_pct"] for d in dias) / len(dias), 1),
		"proposta": doc.proposta_escolhida,
		"regime": (dados.get("regras") or {}).get("regime"),
	}
