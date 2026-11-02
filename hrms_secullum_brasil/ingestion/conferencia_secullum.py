"""Conferência com o Secullum (pedido do RH, 30/10/2026). As regras puras ficam em engine/conferencia_secullum.py.

- `conferir_periodo_aberto`: job de madrugada; a cada N dias (padrão 3) relê no Secullum todo o período aberto de cada
  banco (batidas, cartão e afastamentos), reapura o que mudou e avisa o RH das mudanças retroativas.
- `conferir_fechamento`: botão do Fechamento de Ponto; relê o período no Secullum, reapura, compara os totais e grava
  o resultado no fechamento — que só pode ser concluído com a conferência recente (a trava fica no fechamento).
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, today

from hrms_secullum_brasil.engine import conferencia_secullum as cs
from hrms_secullum_brasil.ingestion.secullum import id_banco_da_empresa, integracao_ativa, origem_secullum

CONFIG = "Configuracao Secullum"
FECHAMENTO = "Fechamento de Ponto"
PAPEIS = ("System Manager", "RH Ponto")


def _cfg_int(campo: str, padrao: int) -> int:
	"""Parâmetro da Configuração Secullum; vazio ou 0 (campo novo em configuração já existente) = o padrão."""
	return cint(frappe.db.get_single_value(CONFIG, campo)) or padrao


def _empresas_do_banco() -> dict[str, list[str]]:
	por_banco: dict[str, list[str]] = {}
	for company in frappe.get_all("Company", pluck="name"):
		banco = id_banco_da_empresa(company)
		if banco:
			por_banco.setdefault(banco, []).append(company)
	return por_banco


def _afastamentos() -> str | None:
	"""Atestados e afastamentos lançados no Secullum (passo da importação)."""
	if not origem_secullum():
		return None
	from hrms_secullum_brasil.ingestion.importacao_secullum import ImportacaoSecullum

	try:
		ImportacaoSecullum().executar(["afastamentos"])
	except Exception as exc:
		frappe.log_error(title="Conferência: afastamentos do Secullum")
		return str(exc)[:300]
	return None


def _avisar_rh(texto: str) -> None:
	from hrms_secullum_brasil.apuracao import whatsapp

	cfg = frappe.get_cached_doc("Configuracao Apuracao")
	if cfg.get("termo_celular_rh"):
		whatsapp.enviar(whatsapp.criar(None, "RH", cfg.termo_celular_rh, texto))
	if cfg.get("termo_email_rh") and frappe.db.exists(
		"Email Account", {"enable_outgoing": 1, "default_outgoing": 1}
	):
		try:
			frappe.sendmail(
				recipients=[cfg.termo_email_rh],
				subject=_("Conferência com o Secullum"),
				message=f"<p>{texto}</p>",
			)
		except Exception:
			frappe.log_error(title="Conferência: e-mail ao RH")


def _texto_retroativas(retroativas: list[dict]) -> str:
	dias = ", ".join(f"{r['nome']} {r['data']:%d/%m}" for r in retroativas[:10])
	conflitos = sum(1 for r in retroativas if r["conflito"])
	texto = _("RH: o Secullum mudou {0} dia(s) já passados ({1}{2}). Os dias foram reapurados.").format(
		len(retroativas), dias, "…" if len(retroativas) > 10 else ""
	)
	if conflitos:
		texto += " " + _(
			"{0} deles têm termo ou correção do programa: confira na central de inconsistências."
		).format(conflitos)
	return texto


def conferir_periodo_aberto(forcar: bool = False) -> dict | None:
	"""Job diário (madrugada): a cada `conferencia_intervalo_dias`, relê todo o período aberto de cada banco."""
	from hrms_secullum_brasil.apuracao.periodos import fechado_ate
	from hrms_secullum_brasil.ingestion.coleta_batidas import coletar_batidas

	if not integracao_ativa():
		return None
	agora = now_datetime()
	ultima = frappe.db.get_single_value(CONFIG, "ultima_conferencia")
	if not forcar and not cs.deve_conferir(
		frappe.utils.get_datetime(ultima) if ultima else None,
		agora,
		_cfg_int("conferencia_intervalo_dias", cs.INTERVALO_DIAS),
	):
		return None
	hoje = getdate(today())
	maximo = _cfg_int("conferencia_dias_maximo", cs.MAXIMO_DIAS)
	resumos, retroativas, erros, inicios = [], [], [], []
	for banco, empresas in _empresas_do_banco().items():
		inicio = cs.inicio_da_conferencia(hoje, [fechado_ate(c) for c in empresas], maximo)
		inicios.append(inicio)
		r = coletar_batidas(hoje=hoje, inicio=inicio, bancos=[banco], gravar_saude=False)
		resumos.append(
			f"banco {banco} desde {inicio:%d/%m}: {r.get('novas', 0)} nova(s), {r.get('substituidas', 0)} mudada(s)"
		)
		retroativas += r.get("retroativas_itens", [])
		erros += r.get("erros", [])
	erro_afastamentos = _afastamentos()
	if erro_afastamentos:
		erros.append(f"afastamentos: {erro_afastamentos}")
	status = "Erro" if erros else "Sucesso"
	frappe.db.set_single_value(
		CONFIG,
		{
			"ultima_conferencia": agora,
			"ultima_conferencia_status": status,
			"ultima_conferencia_resumo": "\n".join(
				[*resumos, _("Mudanças retroativas: {0}").format(len(retroativas)), *erros[:10]]
			),
		},
	)
	if retroativas:
		_avisar_rh(_texto_retroativas(retroativas))
	frappe.db.commit()
	return {
		"status": status,
		"retroativas": len(retroativas),
		"desde": str(min(inicios)) if inicios else None,
	}


@frappe.whitelist()
def conferir_agora() -> str:
	"""Botão da Configuração Secullum: a conferência completa agora, em segundo plano."""
	frappe.only_for(PAPEIS)
	frappe.enqueue(
		"hrms_secullum_brasil.ingestion.conferencia_secullum.conferir_periodo_aberto",
		queue="long",
		timeout=7200,
		job_id="secullum-conferencia",
		deduplicate=True,
		forcar=True,
	)
	return _("Conferência com o Secullum enfileirada: o resultado aparece nesta tela em alguns minutos.")


# ------------------------------------------------------------------ conferência do fechamento (trava)


@frappe.whitelist()
def conferir_fechamento(fechamento: str) -> str:
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(FECHAMENTO, fechamento)
	doc.check_permission("write")
	if doc.docstatus != 0:
		frappe.throw(_("O fechamento já foi concluído."))
	if not integracao_ativa():
		frappe.throw(_("Ative a integração na Configuracao Secullum."))
	doc.db_set({"conferencia_situacao": "Na fila", "conferencia_erro": None})
	frappe.enqueue(
		"hrms_secullum_brasil.ingestion.conferencia_secullum.executar_conferencia_do_fechamento",
		queue="long",
		timeout=7200,
		now=bool(frappe.in_test),
		fechamento=fechamento,
	)
	return _("Conferência com o Secullum em andamento: relê o período, reapura e compara os totais.")


def executar_conferencia_do_fechamento(fechamento: str) -> None:
	from hrms_secullum_brasil.apuracao.servico import processar_reapuracoes_pendentes
	from hrms_secullum_brasil.ingestion.coleta_batidas import coletar_batidas
	from hrms_secullum_brasil.ingestion.divergencia_totais import DIVERGENCIA, comparar_totais

	doc = frappe.get_doc(FECHAMENTO, fechamento)
	doc.db_set({"conferencia_situacao": "Conferindo"})
	frappe.db.commit()
	frappe.db.savepoint("conferencia_fechamento")
	try:
		inicio, fim = getdate(doc.periodo_inicio), getdate(doc.periodo_fim)
		hoje = min(fim, getdate(today()))
		r = coletar_batidas(
			hoje=hoje, inicio=inicio, bancos=[id_banco_da_empresa(doc.company)], gravar_saude=False
		)
		if r.get("erros"):
			raise frappe.ValidationError("; ".join(r["erros"][:5]))
		colaboradores = frappe.get_all("Employee", filters={"company": doc.company}, pluck="name")
		processar_reapuracoes_pendentes(employees=colaboradores)
		comparar_totais(doc.company, inicio, fim)
		diferencas = frappe.get_all(
			DIVERGENCIA,
			filters={"company": doc.company, "periodo_inicio": inicio, "periodo_fim": fim},
			pluck="diferenca",
		)
		divergencias = cs.divergentes(diferencas, _cfg_int("conferencia_tolerancia_min", cs.TOLERANCIA_MIN))
		resumo = _(
			"{0} batida(s) nova(s), {1} mudada(s), {2} mudança(s) retroativa(s); {3} divergência(s) de totais acima de {4} min."
		).format(
			r.get("novas", 0),
			r.get("substituidas", 0),
			len(r.get("retroativas_itens", [])),
			divergencias,
			_cfg_int("conferencia_tolerancia_min", cs.TOLERANCIA_MIN),
		)
		doc.db_set(
			{
				"conferido_em": now_datetime(),
				"conferencia_situacao": "Concluída",
				"conferencia_resumo": resumo,
				"divergencias": divergencias,
			}
		)
	except Exception as exc:
		frappe.db.rollback(save_point="conferencia_fechamento")
		frappe.log_error(title=f"Conferência do fechamento {fechamento}")
		doc.db_set(
			{"conferencia_situacao": "Erro", "conferencia_erro": frappe.utils.strip_html(str(exc))[:500]}
		)
	frappe.db.commit()


def bloqueios_do_fechamento(doc) -> list[str]:
	"""A trava (usada no before_submit do Fechamento de Ponto). Sem integração ativa, não há o que conferir."""
	if not integracao_ativa():
		return []
	conferido = frappe.utils.get_datetime(doc.conferido_em) if doc.get("conferido_em") else None
	batidas_depois = 0
	if conferido:
		colaboradores = frappe.get_all("Employee", filters={"company": doc.company}, pluck="name")
		batidas_depois = frappe.db.count(
			"Secullum Checkin Raw",
			{
				"employee": ["in", colaboradores or [""]],
				"data": ["between", [doc.periodo_inicio, doc.periodo_fim]],
				"importado_em": [">", conferido],
			},
		)
	return cs.bloqueios_do_fechamento(
		conferido,
		now_datetime(),
		cint(doc.get("divergencias")),
		doc.get("justificativa_divergencias"),
		batidas_depois,
		_cfg_int("conferencia_validade_horas", cs.VALIDADE_HORAS),
	)
