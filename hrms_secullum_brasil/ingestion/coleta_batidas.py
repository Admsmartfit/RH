"""Coleta de batidas Secullum -> Frappe (PRD, 6.3).

A cada execução, por banco Secullum, busca as marcações originais (FonteDados) da janela
[hoje - dias_reprocessamento, hoje], um dia por chamada, e:
- grava as novas em Secullum Checkin Raw (idempotente: mesmo Id e mesmo hash não é regravado);
- marca como "Substituida" a raw cujo registro mudou ou sumiu do Secullum (nunca apaga);
- espelha as marcações válidas em Employee Checkin (melhor esforço; a raw é a fonte da verdade);
- marca o dia para reapuração;
- nunca altera dias de período fechado: a divergência vira Inconsistencia de Ponto.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass, field

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, now_datetime, time_diff_in_seconds, today

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia
from hrms_secullum_brasil.apuracao.periodos import fechado_ate
from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.ingestion.secullum import (
	get_client,
	id_banco_da_empresa,
	integracao_ativa,
	origem_secullum,
	registrar_evento,
)
from hrms_secullum_brasil.integrations.secullum.batidas import (
	BatidaSecullum,
	RawExistente,
	Vinculo,
	escolher_vinculo,
	parse_fonte_dados,
	planejar_sincronizacao,
)
from hrms_secullum_brasil.integrations.secullum.erros import SecullumError
from hrms_secullum_brasil.integrations.secullum.mapeamento import resumir_payload

RAW = "Secullum Checkin Raw"
CONFIG = "Configuracao Secullum"
METODO_COLETA = "hrms_secullum_brasil.ingestion.coleta_batidas.coletar_batidas"
JOB_ID = "secullum-coleta-batidas"


@dataclass
class Resumo:
	novas: int = 0
	substituidas: int = 0
	inalteradas: int = 0
	sem_colaborador: int = 0
	bloqueadas_periodo_fechado: int = 0
	espelho_nao_criado: int = 0
	erros: list[str] = field(default_factory=list)

	def texto(self) -> str:
		linhas = [
			f"Novas: {self.novas}",
			f"Substituídas: {self.substituidas}",
			f"Inalteradas: {self.inalteradas}",
			f"Sem colaborador no Frappe: {self.sem_colaborador}",
			f"Bloqueadas (período fechado): {self.bloqueadas_periodo_fechado}",
			f"Sem espelho em Employee Checkin: {self.espelho_nao_criado}",
		]
		return "\n".join(linhas + [f"Erro: {e}" for e in self.erros[:20]])


# ------------------------------------------------------------------ agendamento


def tick():
	"""Roda a cada 5 min (scheduler) e dispara a coleta quando o intervalo configurado venceu."""
	if not integracao_ativa():
		return
	ultima = frappe.db.get_single_value(CONFIG, "ultima_coleta")
	intervalo_min = cint(frappe.db.get_single_value(CONFIG, "intervalo_coleta")) or 60
	if ultima and time_diff_in_seconds(now_datetime(), ultima) < intervalo_min * 60:
		return
	enfileirar_coleta()


def enfileirar_coleta():
	frappe.enqueue(METODO_COLETA, queue="long", timeout=3600, job_id=JOB_ID, deduplicate=True)


@frappe.whitelist()
def coletar_agora():
	frappe.only_for(("System Manager", "RH Ponto"))
	if not integracao_ativa():
		frappe.throw(_("Ative a integração na Configuracao Secullum antes de coletar."))
	enfileirar_coleta()


# ------------------------------------------------------------------ coleta


def bancos_configurados() -> list[str]:
	bancos = {id_banco_da_empresa(c) for c in frappe.get_all("Company", pluck="name")}
	bancos.add(id_banco_da_empresa(None))
	return sorted(b for b in bancos if b)


def coletar_batidas(hoje=None) -> dict:
	if not integracao_ativa():
		return {}
	hoje = getdate(hoje or today())
	inicio = add_days(hoje, -max(cint(frappe.db.get_single_value(CONFIG, "dias_reprocessamento")), 0))
	resumo = Resumo()
	for banco in bancos_configurados():
		_Coleta(banco, getdate(inicio), hoje, resumo).executar()
		if origem_secullum():
			# folgas e justificativas lançadas no cartão do Secullum (Cartao Secullum Dia)
			from hrms_secullum_brasil.ingestion.cartao_secullum import sincronizar_cartao

			resumo.erros += sincronizar_cartao(get_client(banco), getdate(inicio), hoje)["erros"]

	status = "Erro" if resumo.erros else "Sucesso"
	frappe.db.set_single_value(
		CONFIG,
		{
			"ultima_coleta": now_datetime(),
			"ultima_coleta_status": status,
			"ultima_coleta_resumo": resumo.texto(),
		},
	)
	registrar_evento(
		"Coleta Batidas", status, registros=resumo.novas, erro="\n".join(resumo.erros[:20]) or None
	)
	return asdict(resumo)


class _Coleta:
	def __init__(self, banco: str, inicio, fim, resumo: Resumo):
		self.banco = banco
		self.inicio = inicio
		self.fim = fim
		self.resumo = resumo
		self.espelhar = cint(frappe.db.get_single_value(CONFIG, "espelhar_employee_checkin"))
		self.skip_auto_attendance = cint(frappe.db.get_single_value(CONFIG, "skip_auto_attendance"))
		self._fechamentos: dict[str, object] = {}
		self._empresas: dict[str, str] = {}

	def executar(self):
		remotas, dias_ok = self._buscar()
		existentes = {
			e.name: e
			for e in frappe.get_all(
				RAW,
				filters={
					"id_banco": self.banco,
					"status": "Ativa",
					"data": ["between", [self.inicio, self.fim]],
				},
				fields=["name", "origem_id", "hash", "employee", "data", "data_hora", "employee_checkin"],
			)
		}
		plano = planejar_sincronizacao(
			remotas, [RawExistente(e.name, e.origem_id, e.hash) for e in existentes.values()]
		)
		self.resumo.inalteradas += plano.inalteradas
		vinculos = self._vinculos()

		for nome in plano.remover:
			raw = existentes[nome]
			if getdate(raw.data) not in dias_ok:
				continue  # o dia não foi lido com sucesso: não dá para afirmar que a batida sumiu
			if self._bloquear_se_fechado(raw.employee, raw.data, raw.data_hora, "excluída", nome):
				continue
			self._substituir(raw, _("Batida excluída no Secullum."))

		for batida, nome_antiga in plano.inserir:
			employee = self._resolver(batida, vinculos)
			if not employee:
				self.resumo.sem_colaborador += 1
				continue
			antiga = existentes.get(nome_antiga) if nome_antiga else None
			acao = "alterada" if antiga else "incluída"
			if self._bloquear_se_fechado(employee, batida.data, batida.data_hora, acao, nome_antiga):
				continue
			if antiga and self._bloquear_se_fechado(
				antiga.employee, antiga.data, antiga.data_hora, acao, nome_antiga
			):
				continue
			self._gravar(batida, employee, antiga)

	# ------------------------------------------------------------------ leitura

	def _buscar(self) -> tuple[list[BatidaSecullum], set]:
		client = get_client(self.banco)
		remotas, dias_ok = [], set()
		dia = self.inicio
		while dia <= self.fim:
			try:
				registros = client.listar_fonte_dados(dia, dia)
			except SecullumError as exc:
				self.resumo.erros.append(f"{dia}: {exc}")
			else:
				dias_ok.add(dia)
				for registro in registros:
					try:
						remotas.append(parse_fonte_dados(registro))
					except ValueError as exc:
						self.resumo.erros.append(str(exc))
			dia = add_days(dia, 1)
		return remotas, dias_ok

	def _vinculos(self) -> dict[str, dict[str, list[Vinculo]]]:
		indices: dict[str, dict[str, list[Vinculo]]] = {
			"cpf": defaultdict(list),
			"pis": defaultdict(list),
			"id": defaultdict(list),
		}
		for e in frappe.get_all(
			"Employee",
			fields=["name", "company", "cpf", "pis", "id_secullum", "date_of_joining", "relieving_date"],
		):
			if self._banco_da_empresa(e.company) != self.banco:
				continue
			vinculo = Vinculo(
				e.name,
				getdate(e.date_of_joining) if e.date_of_joining else None,
				getdate(e.relieving_date) if e.relieving_date else None,
			)
			for indice, chave in (("cpf", e.cpf), ("pis", e.pis), ("id", e.id_secullum)):
				if chave:
					indices[indice][str(chave)].append(vinculo)
		return indices

	def _resolver(self, batida: BatidaSecullum, vinculos) -> str | None:
		for indice, chave in (("cpf", batida.cpf), ("pis", batida.pis), ("id", batida.funcionario_id)):
			if chave and vinculos[indice].get(chave):
				return escolher_vinculo(vinculos[indice][chave], batida.data)
		return None

	def _banco_da_empresa(self, company: str) -> str:
		if company not in self._empresas:
			self._empresas[company] = id_banco_da_empresa(company)
		return self._empresas[company]

	# ------------------------------------------------------------------ período fechado

	def _bloquear_se_fechado(self, employee, data, data_hora, acao: str, nome_raw: str | None) -> bool:
		company = frappe.db.get_value("Employee", employee, "company")
		if company not in self._fechamentos:
			self._fechamentos[company] = fechado_ate(company)
		limite = self._fechamentos[company]
		if not limite or getdate(data) > limite:
			return False
		registrar_inconsistencia(
			employee,
			"batida_periodo_fechado",
			_(
				"Batida de {0} foi {1} no Secullum, mas o ponto está fechado até {2}. "
				"Nada foi alterado no Frappe; avalie a reabertura do período."
			).format(frappe.utils.format_datetime(data_hora), acao, frappe.utils.formatdate(limite)),
			severidade="Alta",
			data=getdate(data),
			referencia_doctype=RAW if nome_raw else None,
			referencia_name=nome_raw,
		)
		self.resumo.bloqueadas_periodo_fechado += 1
		return True

	# ------------------------------------------------------------------ escrita

	def _substituir(self, raw, motivo: str, por: str | None = None):
		frappe.db.set_value(
			RAW,
			raw.name,
			{
				"status": "Substituida",
				"chave_unica": None,
				"substituida_em": now_datetime(),
				"substituida_por": por,
				"motivo_substituicao": motivo,
			},
		)
		if raw.employee_checkin and self._remover_espelho(raw.employee_checkin):
			frappe.db.set_value(RAW, raw.name, "employee_checkin", None)
		marcar_para_reapuracao(raw.employee, raw.data, motivo)
		self.resumo.substituidas += 1

	def _gravar(self, batida: BatidaSecullum, employee: str, antiga):
		frappe.db.savepoint("secullum_batida")
		try:
			if antiga:
				# libera a chave_unica antes de gravar a nova versão (pode ter o mesmo horário e Id)
				self._substituir(antiga, _("Batida alterada no Secullum."))
			raw = frappe.get_doc(
				{
					"doctype": RAW,
					"employee": employee,
					"data": batida.data,
					"data_hora": batida.data_hora,
					"status": "Ativa",
					"tipo_fonte": batida.tipo,
					"tipo_origem": batida.origem,
					"equipamento": batida.equipamento,
					"origem_id": batida.origem_id,
					"funcionario_id_secullum": batida.funcionario_id,
					"id_banco": self.banco,
					"importado_em": now_datetime(),
					"data_inclusao_secullum": batida.data_inclusao,
					"hash": batida.hash,
					"chave_unica": f"{employee}|{batida.data_hora.isoformat()}|{batida.origem_id}",
					"payload": resumir_payload(batida.payload, limite=10_000),
				}
			).insert(ignore_permissions=True)
		except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
			frappe.db.rollback(save_point="secullum_batida")
			self.resumo.inalteradas += 1
			return

		if antiga:
			frappe.db.set_value(RAW, antiga.name, "substituida_por", raw.name)
		self.resumo.novas += 1
		if self.espelhar and not batida.desconsiderada:
			self._espelhar(raw.name, batida, employee)
		marcar_para_reapuracao(employee, batida.data, _("Nova batida importada do Secullum."))

	def _espelhar(self, nome_raw: str, batida: BatidaSecullum, employee: str):
		frappe.db.savepoint("secullum_espelho")
		try:
			checkin = frappe.get_doc(
				{
					"doctype": "Employee Checkin",
					"employee": employee,
					"time": batida.data_hora,
					"device_id": batida.equipamento,
					"skip_auto_attendance": self.skip_auto_attendance,
					"secullum_checkin_raw": nome_raw,
				}
			).insert(ignore_permissions=True)
		except frappe.ValidationError:
			# colaborador inativo, horário duplicado, geolocalização obrigatória etc.
			frappe.db.rollback(save_point="secullum_espelho")
			frappe.clear_messages()
			self.resumo.espelho_nao_criado += 1
			return
		frappe.db.set_value(RAW, nome_raw, "employee_checkin", checkin.name)

	def _remover_espelho(self, nome_checkin: str) -> bool:
		"""Remove o Employee Checkin espelhado. Não remove se já virou Attendance (fica no resumo)."""
		if not frappe.db.exists("Employee Checkin", nome_checkin):
			return True
		if frappe.db.get_value("Employee Checkin", nome_checkin, "attendance"):
			self.resumo.erros.append(
				_("Employee Checkin {0} está vinculado a uma Attendance e não foi removido.").format(
					nome_checkin
				)
			)
			return False
		frappe.delete_doc("Employee Checkin", nome_checkin, ignore_permissions=True, force=True)
		return True
