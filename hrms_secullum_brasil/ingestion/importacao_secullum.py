"""Importação dos cadastros do Secullum (docs/PRD-importacao-secullum.md, IS-06).

    bench --site ponto.localhost execute hrms_secullum_brasil.ingestion.importacao_secullum.importar \\
        --kwargs "{'simular': 1}"

O Secullum é a origem (IS-02). Cada passo lê do Secullum, converte com as regras puras de
integrations/secullum/importacao.py e grava por upsert pela chave do Secullum: rodar de novo só atualiza o que
mudou. Cada registro vira uma linha no Log de Importacao Secullum; erro num registro não para os outros.
`simular=True` calcula tudo e não grava nada (a pré-visualização do assistente).
"""

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta

import frappe
from frappe.utils import getdate, now_datetime, today, validate_email_address
from frappe.utils.nestedset import rebuild_tree

from hrms_secullum_brasil.apuracao.feriados import _normalizar as normalizar_texto
from hrms_secullum_brasil.apuracao.feriados import gerar_feriados
from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.regra_sindical_cct import (
	get_faixas_padrao,
)
from hrms_secullum_brasil.engine.documentos import somente_digitos
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia
from hrms_secullum_brasil.ingestion.secullum import get_client
from hrms_secullum_brasil.install import garantir_generos
from hrms_secullum_brasil.integrations.secullum import importacao as imp

LOG = "Log de Importacao Secullum"
PERFIL = "Perfil de Jornada"
CCT = "Regra Sindical CCT"
RAIZ_DEPARTAMENTOS = "All Departments"
SINDICATO_IMPORTADO = "Importada do Secullum"  # IS-07: a CCT padrão de cada empresa

# passos na ordem em que precisam rodar (os seguintes entram nas próximas etapas do PRD)
PASSOS = (
	"empresas",
	"justificativas",
	"funcoes",
	"departamentos",
	"horarios",
	"cct",
	"feriados",
	"funcionarios",
	"estruturas",
	"afastamentos",
	"equipamentos",
)
ROTULOS = {
	"empresas": "Empresas",
	"justificativas": "Justificativas",
	"funcoes": "Funções",
	"departamentos": "Departamentos",
	"horarios": "Horários",
	"cct": "CCT padrão",
	"feriados": "Feriados",
	"funcionarios": "Funcionários",
	"estruturas": "Estruturas",
	"afastamentos": "Afastamentos",
	"equipamentos": "Equipamentos",
}
JUSTIFICATIVA = "Justificativa Secullum"
AFASTAMENTO = "Afastamento Secullum"
EQUIPAMENTO = "Equipamento Secullum"
NASCIMENTO_AUSENTE = "nascimento_ausente"  # DI-6
SUMIDO = "colaborador_nao_encontrado_secullum"  # IS-08
PERIODO_FECHADO = "alteracao_periodo_fechado"  # IS-08

CRIADO, ATUALIZADO, SEM_MUDANCA, IGNORADO, AVISO, ERRO = (
	"Criado",
	"Atualizado",
	"Sem mudança",
	"Ignorado",
	"Aviso",
	"Erro",
)


@dataclass
class Linha:
	passo: str
	resultado: str
	chave: str
	mensagem: str = ""
	doctype: str | None = None
	nome: str | None = None


class ImportacaoSecullum:
	def __init__(self, client=None, hoje: date | None = None, simular: bool = False):
		self.client = client or get_client()
		self.hoje = getdate(hoje or today())
		self.simular = simular
		self.linhas: list[Linha] = []
		self._cache: dict = {}
		self.empresa_por_documento: dict[str, str] = {}  # CNPJ → Company (ou o nome que terá, ao simular)
		self.abbr_por_documento: dict[str, str] = {}
		self.cct_por_documento: dict[str, str] = {}  # CNPJ → CCT que os funcionários usam (IS-07)

	# ------------------------------------------------------------------ dados do Secullum (lidos uma vez)

	def _ler(self, chave: str, funcao):
		if chave not in self._cache:
			self._cache[chave] = funcao()
		return self._cache[chave]

	@property
	def colaboradores(self) -> list[imp.ColaboradorImportado]:
		"""Vínculos que entram na importação (DI-7), já convertidos; os com problema ficam de fora dos usos."""

		def carregar():
			brutos = self._ler("funcionarios_brutos", self.client.listar_funcionarios)
			vinculos = imp.selecionar_vinculos(brutos, self.hoje)
			motivos = {
				int(m["Id"]): m.get("Descricao") for m in self.client.listar_motivos_demissao() if m.get("Id")
			}
			return [imp.colaborador_do_secullum(f, motivos) for f in vinculos]

		return self._ler("colaboradores", carregar)

	def _usados(self) -> list[imp.ColaboradorImportado]:
		return [c for c in self.colaboradores if not c.problemas]

	@property
	def perfis(self) -> dict[int, imp.PerfilImportado]:
		"""Horários do Secullum convertidos, por número (sem os que têm problema)."""

		def carregar():
			convertidos = (imp.perfil_do_horario(h) for h in self.client.listar_horarios())
			return {p.numero: p for p in convertidos if not p.problemas}

		return self._ler("perfis", carregar)

	def _codigo_perfil(self, numero: int, documento: str) -> str | None:
		"""Código do perfil de um horário numa empresa: SEC-<n>, ou SEC-<n>-<sigla> quando várias empresas usam."""
		empresas = self._ler(
			"empresas_por_horario",
			lambda: _agrupar(
				(int(c.horario_numero), c.empresa_documento)
				for c in self._usados()
				if c.horario_numero is not None
			),
		).get(int(numero), set())
		if len(empresas) <= 1:
			return f"SEC-{int(numero)}"
		abbr = self._empresa(documento)[1]
		return f"SEC-{int(numero)}-{abbr}" if abbr else None

	def _documentos_importados(self) -> list[str]:
		"""CNPJs das empresas com funcionário importado (na ordem do CNPJ)."""
		return sorted({c.empresa_documento for c in self._usados() if c.empresa_documento})

	# ------------------------------------------------------------------ execução

	def registrar(self, passo, resultado, chave, mensagem="", doctype=None, nome=None) -> None:
		self.linhas.append(
			Linha(ROTULOS.get(passo, passo), resultado, str(chave)[:140], mensagem, doctype, nome)
		)

	def executar(self, passos=None) -> dict:
		passos = [p for p in PASSOS if not passos or p in passos]
		frappe.flags.importacao_secullum = True
		try:
			for passo in passos:
				getattr(self, f"_passo_{passo}")()
		finally:
			frappe.flags.importacao_secullum = False
		execucao = f"{'SIMULACAO' if self.simular else 'IMPORTACAO'}-{now_datetime():%Y%m%d-%H%M%S}"
		if not self.simular:
			self._gravar_log(execucao)
		contagem = defaultdict(Counter)
		for linha in self.linhas:
			contagem[linha.passo][linha.resultado] += 1
		return {
			"execucao": execucao,
			"simulacao": self.simular,
			"contagem": {passo: dict(c) for passo, c in contagem.items()},
			"linhas": [asdict(linha) for linha in self.linhas],
		}

	def _gravar_log(self, execucao: str) -> None:
		for linha in self.linhas:
			frappe.get_doc(
				{
					"doctype": LOG,
					"execucao": execucao,
					"passo": linha.passo,
					"resultado": linha.resultado,
					"chave": linha.chave,
					"mensagem": linha.mensagem[:5000] if linha.mensagem else None,
					"referencia_doctype": linha.doctype if linha.nome else None,
					"referencia_name": linha.nome,
				}
			).insert(ignore_permissions=True)

	def _ponto_de_salvamento(self) -> None:
		"""Erro num registro desfaz só esse registro (savepoint), não a importação inteira."""
		if not self.simular:
			frappe.db.savepoint("importacao_registro")

	def _desfazer(self) -> None:
		if not self.simular:
			frappe.db.rollback(save_point="importacao_registro")

	def _salvar(self, doc) -> None:
		if self.simular:
			return
		doc.flags.ignore_permissions = True
		if doc.is_new():
			doc.insert()
		else:
			doc.save()

	@staticmethod
	def _mudancas(doc, valores: dict) -> list[str]:
		mudou = []
		for campo, valor in valores.items():
			atual = doc.get(campo)
			if (atual or None) != (valor or None) and str(atual or "") != str(valor or ""):
				doc.set(campo, valor)
				mudou.append(campo)
		return mudou

	# ------------------------------------------------------------------ empresas

	def _company_por_documento(self) -> dict[str, str]:
		return {
			somente_digitos(c.tax_id): c.name
			for c in frappe.get_all("Company", fields=["name", "tax_id"])
			if somente_digitos(c.tax_id)
		}

	def _passo_empresas(self) -> None:
		existentes = self._company_por_documento()
		siglas = set(frappe.get_all("Company", pluck="abbr"))
		ativos_por_empresa = Counter(c.empresa_documento for c in self._usados())
		for bruto in self.client.listar_empresas():
			e = imp.empresa_do_secullum(bruto)
			chave = e.documento or e.nome
			if e.problemas:
				self.registrar("empresas", ERRO, chave, "; ".join(e.problemas))
				continue
			if e.desativada and not ativos_por_empresa.get(e.documento):
				self.registrar(
					"empresas", IGNORADO, chave, f"{e.nome}: desativada no Secullum e sem funcionário."
				)
				continue
			valores = {
				"tax_id": e.documento,
				"uf": e.uf,
				"municipio": (e.cidade or "").title() or None,
				"id_secullum_empresa": e.id_secullum,
				"inscricao_estadual": e.inscricao,
				"cei": e.cei,
				"codigo_folha_empresa": e.codigo_folha,
				"phone_no": e.telefone,
			}
			nome = existentes.get(e.documento)
			self._ponto_de_salvamento()
			try:
				if nome:
					doc = frappe.get_doc("Company", nome)
					mudou = self._mudancas(doc, valores)
					if mudou:
						self._salvar(doc)
					self.empresa_por_documento[e.documento] = nome
					self.abbr_por_documento[e.documento] = doc.abbr
					self.registrar(
						"empresas",
						ATUALIZADO if mudou else SEM_MUDANCA,
						chave,
						", ".join(mudou),
						"Company",
						nome,
					)
					continue
				abbr = imp.sugerir_abbr(e.nome, siglas)
				siglas.add(abbr)
				doc = frappe.get_doc(
					{
						"doctype": "Company",
						"company_name": e.nome,
						"abbr": abbr,
						"country": "Brazil",
						"default_currency": "BRL",
						"create_chart_of_accounts_based_on": "Standard Template",
						"chart_of_accounts": "Standard",
						**valores,
					}
				)
				self._salvar(doc)
				self._endereco(doc, e)
				self.empresa_por_documento[e.documento] = doc.name or e.nome
				self.abbr_por_documento[e.documento] = abbr
				self.registrar(
					"empresas",
					CRIADO,
					chave,
					f"{e.nome} ({abbr}), {e.cidade or ''}/{e.uf or ''}",
					"Company",
					doc.name,
				)
			except Exception as exc:
				self._desfazer()
				self.registrar("empresas", ERRO, chave, f"{e.nome}: {exc}")

	def _endereco(self, company, e: imp.EmpresaImportada) -> None:
		if self.simular or not e.endereco:
			return
		frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": company.name,
				"address_type": "Office",
				"address_line1": e.endereco[:140],
				"address_line2": e.bairro,
				"city": e.cidade or "-",
				"state": e.uf,
				"pincode": e.cep,
				"country": "Brazil",
				"phone": e.telefone,
				"is_your_company_address": 1,
				"links": [{"link_doctype": "Company", "link_name": company.name}],
			}
		).insert(ignore_permissions=True)

	def _empresa(self, documento: str) -> tuple[str | None, str | None]:
		"""(Company, sigla) de um CNPJ do Secullum, importado neste passo ou antes."""
		if documento not in self.empresa_por_documento:
			nome = self._company_por_documento().get(documento)
			if nome:
				self.empresa_por_documento[documento] = nome
				self.abbr_por_documento[documento] = frappe.db.get_value("Company", nome, "abbr")
		return self.empresa_por_documento.get(documento), self.abbr_por_documento.get(documento)

	# ------------------------------------------------------------------ funções (cargos)

	def _passo_funcoes(self) -> None:
		usadas = Counter(c.funcao for c in self._usados() if c.funcao)
		for f in self.client.listar_funcoes():
			descricao = (f.get("Descricao") or "").strip()
			if not descricao:
				continue
			if f.get("Desativado") and not usadas.get(descricao):
				self.registrar("funcoes", IGNORADO, descricao, "Desativada no Secullum e sem funcionário.")
				continue
			if frappe.db.exists("Designation", descricao):
				self.registrar("funcoes", SEM_MUDANCA, descricao, "", "Designation", descricao)
				continue
			doc = frappe.get_doc({"doctype": "Designation", "designation_name": descricao})
			self._salvar(doc)
			self.registrar(
				"funcoes",
				CRIADO,
				descricao,
				f"{usadas.get(descricao, 0)} funcionário(s)",
				"Designation",
				descricao,
			)

	# ------------------------------------------------------------------ departamentos

	def _garantir_raiz_departamentos(self) -> None:
		if self.simular or frappe.db.exists("Department", RAIZ_DEPARTAMENTOS):
			return
		raiz = frappe.get_doc({"doctype": "Department", "department_name": RAIZ_DEPARTAMENTOS, "is_group": 1})
		raiz.flags.ignore_mandatory = True  # a raiz não tem empresa (como no setup do ERPNext)
		raiz.insert(ignore_permissions=True)

	def _passo_departamentos(self) -> None:
		self._garantir_raiz_departamentos()
		empresas_por_departamento = defaultdict(set)
		for c in self._usados():
			if c.departamento:
				empresas_por_departamento[c.departamento].add(c.empresa_documento)
		for d in self.client.listar_departamentos():
			descricao = (d.get("Descricao") or "").strip()
			if not descricao:
				continue
			documentos = empresas_por_departamento.get(descricao)
			if not documentos:
				self.registrar(
					"departamentos", IGNORADO, descricao, "Nenhum funcionário importado neste departamento."
				)
				continue
			for documento in sorted(documentos):
				company, abbr = self._empresa(documento)
				if not company:
					self.registrar("departamentos", ERRO, descricao, f"Empresa {documento} não importada.")
					continue
				nome = f"{descricao} - {abbr}"
				valores = {"codigo_folha": d.get("Nfolha")}
				if frappe.db.exists("Department", nome):
					doc = frappe.get_doc("Department", nome)
					mudou = self._mudancas(doc, valores)
					if mudou:
						self._salvar(doc)
					self.registrar(
						"departamentos", ATUALIZADO if mudou else SEM_MUDANCA, nome, "", "Department", nome
					)
					continue
				doc = frappe.get_doc(
					{
						"doctype": "Department",
						"department_name": descricao,
						"company": company,
						"parent_department": RAIZ_DEPARTAMENTOS,
						**valores,
					}
				)
				self._salvar(doc)
				self.registrar("departamentos", CRIADO, nome, company, "Department", doc.name or nome)

	# ------------------------------------------------------------------ horários → perfis de jornada

	def _passo_horarios(self) -> None:
		uso = defaultdict(lambda: defaultdict(list))  # número → CNPJ → admissões
		for c in self._usados():
			if c.horario_numero is not None:
				uso[int(c.horario_numero)][c.empresa_documento].append(c.admissao)
		for bruto in self.client.listar_horarios():
			perfil = imp.perfil_do_horario(bruto)
			chave = f"Horário {perfil.numero}"
			if perfil.problemas:
				self.registrar("horarios", ERRO, chave, "; ".join(perfil.problemas))
				continue
			empresas = uso.get(perfil.numero)
			if not empresas:
				self.registrar(
					"horarios", IGNORADO, chave, f"{perfil.descricao}: nenhum funcionário importado usa."
				)
				continue
			for documento, admissoes in sorted(empresas.items()):
				company, abbr = self._empresa(documento)
				if not company:
					self.registrar("horarios", ERRO, chave, f"Empresa {documento} não importada.")
					continue
				codigo = self._codigo_perfil(perfil.numero, documento)
				inicio = min(a for a in admissoes if a) if any(admissoes) else self.hoje
				self._ponto_de_salvamento()
				try:
					self._gravar_perfil(perfil, codigo, company, min(inicio, self.hoje))
				except Exception as exc:
					self._desfazer()
					self.registrar("horarios", ERRO, codigo, f"{perfil.descricao}: {exc}")

	@staticmethod
	def _linhas_dias(perfil: imp.PerfilImportado) -> list[dict]:
		if perfil.tipo == imp.HORISTA:
			return []
		linhas = []
		for dia in perfil.dias:
			linha = {"dia_semana": dia.dia_semana, "neutro": int(dia.neutro)}
			for n, (entrada, saida) in enumerate(dia.periodos, start=1):
				linha[f"entrada{n}"], linha[f"saida{n}"] = entrada, saida
			linhas.append(linha)
		return linhas

	@staticmethod
	def _assinatura_dias(linhas) -> list[tuple]:
		def hora(valor):
			return (
				minutos_do_dia(valor) if valor not in (None, "") else None
			)  # "8:00:00", timedelta ou "08:00"

		return sorted(
			(
				linha.get("dia_semana"),
				int(linha.get("neutro") or 0),
				*(hora(linha.get(f"{c}{n}")) for n in (1, 2, 3) for c in ("entrada", "saida")),
			)
			for linha in linhas
			if any(linha.get(f"entrada{n}") for n in (1, 2, 3)) or linha.get("dia_semana")
		)

	def _gravar_perfil(self, perfil: imp.PerfilImportado, codigo: str, company: str, inicio: date) -> None:
		linhas = self._linhas_dias(perfil)
		estrutura = {
			"tipo": perfil.tipo,
			"carga_semanal_minutos": perfil.carga_semanal_minutos,
			"divisor": perfil.divisor,
			"hora_virada_dia": perfil.hora_virada,
			"permite_intervalo_estendido": int(perfil.permite_intervalo_estendido),
		}
		avisos = "; ".join(perfil.avisos)
		vigente = frappe.get_all(
			PERFIL,
			filters={"codigo": codigo, "vigencia_inicio": ["<=", self.hoje]},
			or_filters=[["vigencia_fim", "is", "not set"], ["vigencia_fim", ">=", self.hoje]],
			pluck="name",
			order_by="vigencia_inicio desc",
			limit=1,
		)
		if vigente:
			doc = frappe.get_doc(PERFIL, vigente[0])
			mudou_estrutura = self._assinatura_dias(doc.dias) != self._assinatura_dias(linhas) or any(
				str(doc.get(k) or 0) != str(v or 0) for k, v in estrutura.items()
			)
			if not mudou_estrutura:
				mudou = self._mudancas(
					doc, {"descricao": perfil.descricao, "numero_horario_secullum": perfil.numero}
				)
				if mudou:
					self._salvar(doc)
				self.registrar(
					"horarios", ATUALIZADO if mudou else SEM_MUDANCA, codigo, avisos, PERFIL, doc.name
				)
				return
			if getdate(doc.vigencia_inicio) >= self.hoje:  # criado hoje: corrige no lugar
				doc.update({**estrutura, "descricao": perfil.descricao})
				doc.set("dias", linhas)
				self._salvar(doc)
				self.registrar("horarios", ATUALIZADO, codigo, avisos, PERFIL, doc.name)
				return
			# horário mudou no Secullum: encerra a versão vigente e abre outra a partir de hoje (IS-08)
			doc.vigencia_fim = self.hoje - timedelta(days=1)
			self._salvar(doc)
			inicio = self.hoje
			mensagem = f"Horário mudou no Secullum: nova versão desde {self.hoje:%d/%m/%Y}. {avisos}".strip()
		else:
			mensagem = avisos
		novo = frappe.get_doc(
			{
				"doctype": PERFIL,
				"codigo": codigo,
				"descricao": perfil.descricao,
				"company": company,
				"vigencia_inicio": inicio,
				"numero_horario_secullum": perfil.numero,
				"dias": linhas,
				**estrutura,
			}
		)
		self._salvar(novo)
		self.registrar("horarios", CRIADO if not vigente else ATUALIZADO, codigo, mensagem, PERFIL, novo.name)

	# ------------------------------------------------------------------ CCT padrão (IS-07)

	def _passo_cct(self) -> None:
		por_empresa = defaultdict(
			lambda: ([], set(), set())
		)  # CNPJ → (admissões, nºs de horário, cargos horistas)
		for c in self._usados():
			admissoes, horarios, cargos = por_empresa[c.empresa_documento]
			if c.admissao:
				admissoes.append(c.admissao)
			if c.horario_numero is not None:
				horarios.add(int(c.horario_numero))
				perfil = self.perfis.get(int(c.horario_numero))
				if c.funcao and perfil and perfil.tipo == imp.HORISTA:
					cargos.add(c.funcao)
		for documento in self._documentos_importados():
			company, _abbr = self._empresa(documento)
			if not company:
				self.registrar("cct", ERRO, documento, f"Empresa {documento} não importada.")
				continue
			admissoes, horarios, cargos = por_empresa[documento]
			perfis = [self.perfis[n] for n in sorted(horarios) if n in self.perfis]
			self._ponto_de_salvamento()
			try:
				self._gravar_cct(documento, company, min([*admissoes, self.hoje]), perfis, sorted(cargos))
			except Exception as exc:
				self._desfazer()
				self.registrar("cct", ERRO, company, str(exc))

	def _gravar_cct(
		self, documento: str, company: str, inicio: date, perfis: list, cargos_horistas: list | None = None
	) -> None:
		existe = frappe.db.exists("Company", company)
		do_rh = existe and frappe.get_all(
			CCT,
			filters={
				"company": company,
				"sindicato": ["!=", SINDICATO_IMPORTADO],
				"vigencia_inicio": ["<=", self.hoje],
			},
			or_filters=[["vigencia_fim", "is", "not set"], ["vigencia_fim", ">=", self.hoje]],
			fields=["name", "sindicato"],
			order_by="vigencia_inicio desc",
		)
		if do_rh:
			self.cct_por_documento[documento] = do_rh[0].name
			self.registrar(
				"cct",
				IGNORADO,
				company,
				f"A empresa já tem a CCT {do_rh[0].name} ({do_rh[0].sindicato}) cadastrada no programa: os "
				"funcionários ficam ligados a ela.",
				CCT,
				do_rh[0].name,
			)
			return
		importada = existe and frappe.db.get_value(
			CCT,
			{"company": company, "sindicato": SINDICATO_IMPORTADO},
			["name", "vigencia_inicio"],
			as_dict=True,
		)
		if importada:
			# depois de criada, a CCT é do programa (o Secullum não tem CCT): só a vigência acompanha as admissões
			self.cct_por_documento[documento] = importada.name
			doc = frappe.get_doc(CCT, importada.name)
			mensagens = []
			if inicio < getdate(importada.vigencia_inicio):
				doc.vigencia_inicio = inicio
				mensagens.append(f"Vigência desde {inicio:%d/%m/%Y}.")
			novos = self._jornada_fragmentada(doc, cargos_horistas)
			if novos:
				mensagens.append(self._aviso_fragmentada(novos))
			if mensagens:
				self._salvar(doc)
				self.registrar("cct", ATUALIZADO, company, " ".join(mensagens), CCT, importada.name)
			else:
				self.registrar("cct", SEM_MUDANCA, company, "", CCT, importada.name)
			return

		fixos = [p for p in perfis if p.tipo == imp.FIXA] or perfis
		sugestao = imp.sugestao_de_cct(fixos)
		faixas = [
			{**f, "percentual": sugestao.faixas_he.get(f["tipo_dia"], f["percentual"])}
			for f in get_faixas_padrao()
		]
		doc = frappe.get_doc(
			{
				"doctype": CCT,
				"company": company,
				"sindicato": SINDICATO_IMPORTADO,
				"uf": frappe.db.get_value("Company", company, "uf") if existe else None,
				"vigencia_inicio": inicio,
				"tolerancia_por_marcacao": sugestao.tolerancia_por_marcacao,
				"tolerancia_diaria": sugestao.tolerancia_diaria,
				"faixas_hora_extra": faixas,
			}
		)
		novos = self._jornada_fragmentada(doc, cargos_horistas)
		self._salvar(doc)
		self.cct_por_documento[documento] = doc.name
		resumo = (
			f"Tolerância {sugestao.tolerancia_por_marcacao}/{sugestao.tolerancia_diaria} min; HE "
			+ ", ".join(f"{f['tipo_dia']} {f['percentual']:g}%" for f in faixas)
			+ ". Confira noturno, banco de horas e DSR na CCT."
		)
		avisos = [*sugestao.avisos, *([self._aviso_fragmentada(novos)] if novos else [])]
		self.registrar("cct", CRIADO, company, " ".join([resumo, *avisos]), CCT, doc.name)

	def _jornada_fragmentada(self, doc, cargos: list | None) -> list[str]:
		"""CP-06: cargos dos horistas ganham "Jornada fragmentada" na CCT importada (dois turnos no dia sem
		inconsistência de intervalo). Só cria a linha do cargo que ainda não tem: o que o RH ajustou fica."""
		existentes = {p.designation for p in doc.get("parametros_cargo") or []}
		novos = []
		for funcao in cargos or []:
			cargo = funcao if self.simular else frappe.db.get_value("Designation", funcao, "name")
			if cargo and cargo not in existentes:
				doc.append("parametros_cargo", {"designation": cargo, "jornada_fragmentada": 1})
				existentes.add(cargo)
				novos.append(cargo)
		return novos

	@staticmethod
	def _aviso_fragmentada(cargos: list[str]) -> str:
		return (
			f"Jornada fragmentada (intervalo maior que 2h) ligada para os cargos de horistas: {', '.join(cargos)}. "
			"Confira se a CCT ou acordo escrito permite (CLT, art. 71)."
		)

	# ------------------------------------------------------------------ feriados (IS-10)

	def _passo_feriados(self) -> None:
		anos = (self.hoje.year, self.hoje.year + 1)
		for documento in self._documentos_importados():
			company, _abbr = self._empresa(documento)
			if not company:
				self.registrar("feriados", ERRO, documento, f"Empresa {documento} não importada.")
				continue
			if self.simular or not frappe.db.exists("Company", company):
				self.registrar("feriados", CRIADO, company, f"Lista de feriados de {anos[0]} e {anos[1]}.")
				continue
			self._ponto_de_salvamento()
			try:
				havia = frappe.db.get_value("Company", company, "holiday_list_ponto")
				novos = sum(gerar_feriados(ano, company)[company] for ano in anos)
				lista = frappe.db.get_value("Company", company, "holiday_list_ponto")
				resultado = CRIADO if not havia else ATUALIZADO if novos else SEM_MUDANCA
				mensagem = f"{novos} feriado(s) novo(s) em {anos[0]}-{anos[1]}." if novos else ""
				self.registrar("feriados", resultado, company, mensagem, "Holiday List", lista)
			except Exception as exc:
				self._desfazer()
				self.registrar("feriados", ERRO, company, f"Feriados: {exc}")
				continue
			uf, municipio = frappe.db.get_value("Company", company, ["uf", "municipio"])
			if not self._tem_feriado_municipal(uf, municipio):
				local = f"{municipio or 'município não informado'}/{uf or 'UF não informada'}"
				self.registrar(
					"feriados",
					AVISO,
					company,
					f"Cadastre os feriados municipais de {local} (e os estaduais) em Feriado Regional; "
					"depois clique em Gerar feriados.",
				)

	@staticmethod
	def _tem_feriado_municipal(uf, municipio) -> bool:
		if not (uf and municipio):
			return False
		return any(
			normalizar_texto(m) == normalizar_texto(municipio)
			for m in frappe.get_all(
				"Feriado Regional",
				filters={"ativo": 1, "abrangencia": "Municipal", "uf": uf},
				pluck="municipio",
			)
		)

	# ------------------------------------------------------------------ funcionários (3.5)

	def _passo_funcionarios(self) -> None:
		if not self.simular:
			garantir_generos()
		existentes = dict(
			frappe.get_all(
				"Employee",
				filters={"id_secullum": ["is", "set"]},
				fields=["id_secullum", "name"],
				as_list=True,
			)
		)
		for c in self.colaboradores:
			chave = f"{c.id_secullum} - {c.nome}"
			if c.problemas:
				self.registrar("funcionarios", ERRO, chave, "; ".join(c.problemas + c.avisos))
				continue
			company, abbr = self._empresa(c.empresa_documento)
			if not company:
				self.registrar("funcionarios", ERRO, chave, f"Empresa {c.empresa_documento} não importada.")
				continue
			self._ponto_de_salvamento()
			try:
				self._gravar_funcionario(c, chave, company, abbr, existentes.get(str(c.id_secullum)))
			except Exception as exc:
				self._desfazer()
				self.registrar("funcionarios", ERRO, chave, str(exc))
		self._sumidos()

	def _valores_funcionario(
		self, c: imp.ColaboradorImportado, company: str, abbr: str | None
	) -> tuple[dict, list]:
		avisos = list(c.avisos)
		# nomes como estão gravados (a busca do banco ignora maiúsculas: "RECEPCIONISTA" acha "Recepcionista")
		departamento = f"{c.departamento} - {abbr}" if c.departamento and abbr else None
		if departamento and not self.simular:
			gravado = frappe.db.get_value("Department", departamento, "name")
			if not gravado:
				avisos.append(f"Departamento {departamento} não encontrado.")
			departamento = gravado
		cargo = c.funcao
		if cargo and not self.simular:
			cargo = frappe.db.get_value("Designation", cargo, "name")
		email = validate_email_address(c.email or "") or None
		if c.email and not email:
			avisos.append(f"E-mail inválido no Secullum: {c.email}")
		valores = {
			"first_name": c.first_name,
			"middle_name": None,
			"last_name": c.last_name or None,
			"cpf": c.cpf,
			"pis": c.pis,
			"gender": c.genero,
			"date_of_birth": c.nascimento,
			"date_of_joining": c.admissao,
			"relieving_date": c.demissao,
			"status": c.status,
			"reason_for_leaving": c.motivo_demissao,
			"company": company,
			"department": departamento,
			"designation": cargo,
			"matricula_secullum": c.matricula,
			"id_secullum": str(c.id_secullum),
			"personal_email": email,
			"cell_number": c.celular,
			"current_address": c.endereco,
			"rg": c.rg,
			"ctps": c.ctps,
			"codigo_holerite": c.codigo_holerite,
			"invisivel_secullum": int(c.invisivel),
		}
		return valores, avisos

	def _perfil_do_colaborador(self, c: imp.ColaboradorImportado) -> tuple[str | None, str | None]:
		"""(Perfil de Jornada vigente hoje — ou o mais recente — do horário do colaborador, tipo do perfil)."""
		codigo = self._codigo_perfil(c.horario_numero, c.empresa_documento)
		perfis = frappe.get_all(
			PERFIL,
			filters={"codigo": codigo, "vigencia_inicio": ["<=", self.hoje]},
			fields=["name", "tipo"],
			order_by="vigencia_inicio desc",
			limit=1,
		) or frappe.get_all(
			PERFIL, filters={"codigo": codigo}, fields=["name", "tipo"], order_by="vigencia_inicio", limit=1
		)
		if perfis:
			return perfis[0].name, perfis[0].tipo
		perfil = self.perfis.get(int(c.horario_numero))
		return None, perfil.tipo if perfil else None

	def _gravar_funcionario(self, c, chave: str, company: str, abbr: str | None, nome: str | None) -> None:
		valores, avisos = self._valores_funcionario(c, company, abbr)
		perfil, tipo_perfil = self._perfil_do_colaborador(c)
		if not perfil and not self.simular:
			avisos.append(f"Horário {c.horario_numero} sem Perfil de Jornada importado.")
		if nome:
			doc = frappe.get_doc("Employee", nome)
			atual = frappe.db.get_value(PERFIL, doc.perfil_jornada, "codigo") if doc.perfil_jornada else None
			if atual and atual.endswith("-H"):  # cópia Horista feita na revisão (Etapa 12): é o mesmo horário
				atual = atual[:-2]
			novo = frappe.db.get_value(PERFIL, perfil, "codigo") if perfil else None
			if perfil and atual != novo:
				# IS-08: trocou de horário no Secullum. Ele não informa a data da troca: o perfil novo vale a partir de
				# hoje (histórico de horário, sem reescrever o passado) e o RH acerta a data se foi antes.
				self._trocar_horario(doc, perfil, c)
				avisos.append(
					f"Horário trocado no Secullum ({atual} → {novo}): vale desde {self.hoje:%d/%m/%Y}. Se a troca foi "
					"antes, acerte a data no Histórico de horário do colaborador."
				)
			if not doc.regra_cct and self._cct(c.empresa_documento, company):
				valores["regra_cct"] = self._cct(c.empresa_documento, company)
			demitido_agora = c.demissao and not doc.relieving_date
			mudou = self._mudancas(doc, valores)
			if atual != novo and perfil:
				mudou.append("perfil_jornada")
			if mudou:
				self._salvar(doc)
				if demitido_agora and not self.simular:
					# os dias depois da demissão já apurados deixam de ter apuração (reapurar_dia descarta)
					reapurar_dias_apurados(
						doc.name, c.demissao + timedelta(days=1), self.hoje, "Demissão no Secullum"
					)
			resultado = ATUALIZADO if mudou else SEM_MUDANCA
			mensagem = "; ".join(([", ".join(mudou)] if mudou else []) + avisos)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "Employee",
					**valores,
					"perfil_jornada": perfil,
					"regra_cct": self._cct(c.empresa_documento, company),
					"tipo_remuneracao": "Horista" if tipo_perfil == imp.HORISTA else "Mensalista",
					"create_user_permission": 0,
				}
			)
			self._salvar(doc)
			if not self.simular and doc.participa_banco_horas:
				# o banco vale desde a admissão (a carga das batidas começa antes de hoje, DI-3)
				doc.db_set("banco_horas_desde", c.admissao, update_modified=False)
			resultado, mensagem = CRIADO, "; ".join(avisos)
		if not self.simular:
			self._nascimento_ausente(doc.name, c)
		self.registrar("funcionarios", resultado, chave, mensagem, "Employee", doc.name)

	def _trocar_horario(self, doc, perfil: str, c: imp.ColaboradorImportado) -> None:
		"""Histórico de horário: a primeira troca registra o perfil antigo desde a admissão; a nova linha vale de hoje."""
		if not doc.get("historico_perfil_jornada") and doc.perfil_jornada:
			doc.append(
				"historico_perfil_jornada",
				{
					"desde": doc.date_of_joining or c.admissao,
					"perfil_jornada": doc.perfil_jornada,
					"observacao": "Importação do Secullum",
				},
			)
		existente = next((x for x in doc.historico_perfil_jornada if getdate(x.desde) == self.hoje), None)
		if existente:
			existente.perfil_jornada = perfil
		else:
			doc.append(
				"historico_perfil_jornada",
				{"desde": self.hoje, "perfil_jornada": perfil, "observacao": "Horário trocado no Secullum"},
			)
		doc.perfil_jornada = perfil

	def _sumidos(self) -> None:
		"""IS-08: colaborador ativo que não está mais no Secullum (sem demissão) → inconsistência Alta; não apaga."""
		ids = {str(f.get("Id")) for f in self._ler("funcionarios_brutos", self.client.listar_funcionarios)}
		for e in frappe.get_all(
			"Employee",
			filters={"id_secullum": ["is", "set"], "status": "Active"},
			fields=["name", "id_secullum", "employee_name"],
		):
			if e.id_secullum in ids:
				if not self.simular:
					resolver_inconsistencias(e.name, SUMIDO)
				continue
			if not self.simular:
				registrar_inconsistencia(
					e.name,
					SUMIDO,
					f"Colaborador (Id {e.id_secullum} no Secullum) não encontrado no Secullum e sem demissão. Confira "
					"no Secullum: se saiu, informe a demissão lá.",
					severidade="Alta",
				)
			self.registrar(
				"funcionarios",
				AVISO,
				f"{e.id_secullum} - {e.employee_name}",
				"Não encontrado no Secullum.",
				"Employee",
				e.name,
			)

	def _cct(self, documento: str, company: str) -> str | None:
		if documento not in self.cct_por_documento and frappe.db.exists("Company", company):
			cct = frappe.db.get_value(CCT, {"company": company, "sindicato": SINDICATO_IMPORTADO}, "name")
			if cct:
				self.cct_por_documento[documento] = cct
		return self.cct_por_documento.get(documento)

	@staticmethod
	def _nascimento_ausente(employee: str, c: imp.ColaboradorImportado) -> None:
		"""DI-6: sem nascimento no Secullum, inconsistência Média até o Secullum informar a data."""
		if c.nascimento_ausente:
			registrar_inconsistencia(
				employee,
				NASCIMENTO_AUSENTE,
				"Sem data de nascimento no Secullum: importado com 01/01/1900. Informe a data no Secullum.",
				severidade="Média",
			)
		else:
			resolver_inconsistencias(employee, NASCIMENTO_AUSENTE)

	# ------------------------------------------------------------------ estruturas → chefes (3.6) e gestores (DI-8)

	def _passo_estruturas(self) -> None:
		estruturas = self.client.listar_estruturas()
		if not estruturas:
			self.registrar(
				"estruturas",
				AVISO,
				"Estruturas",
				"Nenhuma estrutura no Secullum: defina os chefes no programa (campo Reporta a / revisão).",
			)
			return
		chefes, avisos = imp.hierarquia_das_estruturas(estruturas)
		for aviso in avisos:
			self.registrar("estruturas", AVISO, "Estruturas", aviso)
		por_cpf = self._employee_por_cpf()
		for cpf, cpf_chefe in sorted(chefes.items()):
			employee, chefe = por_cpf.get(cpf), por_cpf.get(cpf_chefe)
			if not employee:
				continue  # vínculo que não entrou na importação
			if not chefe:
				self.registrar(
					"estruturas",
					AVISO,
					employee,
					f"Responsável CPF ...{cpf_chefe[-4:]} sem cadastro no programa.",
				)
				continue
			self._ponto_de_salvamento()
			try:
				doc = frappe.get_doc("Employee", employee)
				mudou = self._mudancas(doc, {"reports_to": chefe})
				if mudou:
					self._salvar(doc)
				self.registrar(
					"estruturas",
					ATUALIZADO if mudou else SEM_MUDANCA,
					employee,
					f"Reporta a {chefe}",
					"Employee",
					employee,
				)
			except Exception as exc:
				self._desfazer()
				self.registrar("estruturas", ERRO, employee, str(exc))
		for cpf_chefe in sorted(set(chefes.values())):
			chefe = por_cpf.get(cpf_chefe)
			if not chefe or self.simular:
				continue
			self._ponto_de_salvamento()
			try:
				usuario = garantir_usuario_gestor(chefe)
				if usuario:
					self.registrar(
						"estruturas", CRIADO, chefe, f"Usuário {usuario} (Gestor Ponto)", "User", usuario
					)
				else:
					self.registrar(
						"estruturas", AVISO, chefe, "Chefe sem e-mail no Secullum: usuário não criado."
					)
			except Exception as exc:
				self._desfazer()
				self.registrar("estruturas", ERRO, chefe, f"Usuário do gestor: {exc}")
		if not self.simular:
			rebuild_tree("Employee")

	@staticmethod
	def _employee_por_cpf() -> dict[str, str]:
		"""CPF → colaborador importado (o vínculo ativo, se houver)."""
		saida = {}
		for e in frappe.get_all(
			"Employee",
			filters={"id_secullum": ["is", "set"]},
			fields=["name", "cpf", "status"],
			order_by="date_of_joining",
		):
			if e.cpf and (e.cpf not in saida or e.status == "Active"):
				saida[e.cpf] = e.name
		return saida

	# ------------------------------------------------------------------ justificativas (3.7)

	def _passo_justificativas(self) -> None:
		existentes = dict(frappe.get_all(JUSTIFICATIVA, fields=["id_secullum", "name"], as_list=True))
		for j in self.client.listar_justificativas():
			id_secullum = int(j.get("Id") or 0)
			abreviado = (j.get("NomeAbreviado") or "").strip()
			chave = abreviado or str(id_secullum)
			if not id_secullum or not abreviado:
				self.registrar("justificativas", ERRO, chave, "Justificativa sem Id ou sem nome abreviado.")
				continue
			valores = {
				"nome_abreviado": abreviado,
				"nome_completo": (j.get("NomeCompleto") or "").strip() or None,
				"id_secullum": id_secullum,
				"desativada": int(bool(j.get("Desativar"))),
				"lancar_como_horas_falta": int(bool(j.get("LancarComoHorasFalta"))),
				"calcular_como_folga": int(bool(j.get("CalcularComoFolga"))),
				"descontar_dsr": int(bool(j.get("DescontarDsr"))),
				"descontar_banco_horas": int(bool(j.get("DescontarHorasBancoDeHoras"))),
			}
			self._ponto_de_salvamento()
			try:
				nome = existentes.get(id_secullum)
				if nome:
					# o efeito é do RH depois de criado (a sugestão só vale na criação)
					doc = frappe.get_doc(JUSTIFICATIVA, nome)
					mudou = self._mudancas(doc, valores)
					if mudou:
						self._salvar(doc)
					resultado, mensagem = (ATUALIZADO if mudou else SEM_MUDANCA), ", ".join(mudou)
				else:
					efeito = imp.efeito_da_justificativa(j)
					doc = frappe.get_doc({"doctype": JUSTIFICATIVA, **valores, "efeito": efeito})
					self._salvar(doc)
					resultado, mensagem = CRIADO, f"Efeito no ponto: {efeito} (confira)."
				self.registrar("justificativas", resultado, chave, mensagem, JUSTIFICATIVA, doc.name)
			except Exception as exc:
				self._desfazer()
				self.registrar("justificativas", ERRO, chave, str(exc))

	# ------------------------------------------------------------------ afastamentos (3.8)

	def janela_afastamentos(self) -> tuple[date, date]:
		"""Do 1º dia do mesmo mês do ano passado até um ano à frente (cobre a carga das batidas, DI-3)."""
		return date(self.hoje.year - 1, self.hoje.month, 1), self.hoje + timedelta(days=366)

	def _passo_afastamentos(self) -> None:
		inicio, fim = self.janela_afastamentos()
		justificativas = {
			j.nome_abreviado: j
			for j in frappe.get_all(JUSTIFICATIVA, fields=["name", "nome_abreviado", "efeito"])
		}
		efeitos = {nome: j.efeito for nome, j in justificativas.items()}
		if self.simular:
			for j in self.client.listar_justificativas():
				efeitos.setdefault((j.get("NomeAbreviado") or "").strip(), imp.efeito_da_justificativa(j))
		vinculos = defaultdict(list)
		for e in frappe.get_all(
			"Employee",
			filters={"id_secullum": ["is", "set"]},
			fields=["name", "cpf", "date_of_joining", "relieving_date", "matricula_secullum"],
		):
			vinculos[e.cpf].append(e)
		existentes = {
			a.chave: a
			for a in frappe.get_all(
				AFASTAMENTO,
				filters={"inicio": ["<=", fim], "fim": [">=", inicio]},
				fields=["name", "chave", "employee", "inicio", "fim", "removido_no_secullum"],
			)
		}
		vistos = set()
		for bruto in self.client.listar_afastamentos(inicio, fim):
			af = imp.afastamento_do_secullum(bruto, efeitos)
			chave = f"id:{af.id_secullum}" if af.id_secullum else af.chave
			vistos.add(chave)
			if af.problemas:
				self.registrar("afastamentos", ERRO, chave, "; ".join(af.problemas))
				continue
			employee = _vinculo_do_afastamento(vinculos.get(af.cpf, []), af, bruto.get("NumeroFolha"))
			if not employee and self.simular and af.cpf in {c.cpf for c in self._usados()}:
				# simulação: o funcionário ainda não existe, mas entraria nesta importação
				self.registrar(
					"afastamentos",
					CRIADO,
					chave,
					f"{af.justificativa} de {af.inicio:%d/%m/%Y} a {af.fim:%d/%m/%Y}",
				)
				continue
			if not employee:
				self.registrar(
					"afastamentos",
					IGNORADO,
					chave,
					"Funcionário não importado (demitido há mais de 12 meses?).",
				)
				continue
			self._ponto_de_salvamento()
			try:
				self._gravar_afastamento(chave, af, employee, justificativas, existentes.get(chave))
			except Exception as exc:
				self._desfazer()
				self.registrar("afastamentos", ERRO, chave, str(exc))
		for chave, antigo in existentes.items():
			if chave in vistos or antigo.removido_no_secullum:
				continue
			# apagado no Secullum: deixa de valer e os dias são reapurados
			if not self.simular:
				frappe.db.set_value(AFASTAMENTO, antigo.name, "removido_no_secullum", 1)
				self._reapurar_afastamento(antigo.employee, antigo.inicio, antigo.fim)
			self.registrar(
				"afastamentos",
				ATUALIZADO,
				chave,
				"Removido no Secullum: os dias são reapurados.",
				AFASTAMENTO,
				antigo.name,
			)

	def _gravar_afastamento(self, chave, af, employee: str, justificativas: dict, antigo) -> None:
		justificativa = justificativas.get(af.justificativa)
		valores = {
			"employee": employee,
			"justificativa": justificativa.name if justificativa else None,
			"efeito": justificativa.efeito if justificativa else af.efeito,
			"inicio": af.inicio,
			"fim": af.fim,
			"id_secullum": af.id_secullum,
			"chave": chave,
			"data_inclusao": af.data_inclusao,
			"removido_no_secullum": 0,
		}
		if antigo:
			doc = frappe.get_doc(AFASTAMENTO, antigo.name)
			mudou = self._mudancas(doc, valores)
			if mudou:
				self._salvar(doc)
				if not self.simular:
					self._reapurar_afastamento(
						employee, min(getdate(antigo.inicio), af.inicio), max(getdate(antigo.fim), af.fim)
					)
			self.registrar(
				"afastamentos",
				ATUALIZADO if mudou else SEM_MUDANCA,
				chave,
				", ".join(mudou),
				AFASTAMENTO,
				doc.name,
			)
			return
		doc = frappe.get_doc({"doctype": AFASTAMENTO, **valores})
		self._salvar(doc)
		if not self.simular:
			self._reapurar_afastamento(employee, af.inicio, af.fim)
		self.registrar(
			"afastamentos",
			CRIADO,
			chave,
			f"{af.justificativa} de {af.inicio:%d/%m/%Y} a {af.fim:%d/%m/%Y} ({valores['efeito']})",
			AFASTAMENTO,
			doc.name,
		)

	def _reapurar_afastamento(self, employee: str, inicio, fim) -> None:
		fechados = reapurar_dias_apurados(employee, inicio, fim, "Afastamento do Secullum")
		if fechados:
			# IS-08: mudança em período fechado não altera nada e vira inconsistência
			registrar_inconsistencia(
				employee,
				PERIODO_FECHADO,
				f"Afastamento de {getdate(inicio):%d/%m/%Y} a {getdate(fim):%d/%m/%Y} mudou no Secullum, mas {fechados} "
				"dia(s) estão em período fechado e não foram reapurados.",
				severidade="Média",
			)
			self.registrar(
				"afastamentos",
				AVISO,
				employee,
				f"{fechados} dia(s) em período fechado não foram reapurados.",
				"Employee",
				employee,
			)

	# ------------------------------------------------------------------ equipamentos (3.9)

	def _passo_equipamentos(self) -> None:
		for e in self.client.listar_equipamentos():
			id_secullum = int(e.get("Id") or 0)
			if not id_secullum:
				self.registrar("equipamentos", ERRO, str(e.get("Descricao")), "Equipamento sem Id.")
				continue
			valores = {
				"descricao": (e.get("Descricao") or "").strip() or None,
				"endereco_ip": e.get("EnderecoIP"),
			}
			self._ponto_de_salvamento()
			try:
				if frappe.db.exists(EQUIPAMENTO, str(id_secullum)):
					doc = frappe.get_doc(EQUIPAMENTO, str(id_secullum))
					mudou = self._mudancas(doc, valores)
					if mudou:
						self._salvar(doc)
					resultado = ATUALIZADO if mudou else SEM_MUDANCA
				else:
					doc = frappe.get_doc({"doctype": EQUIPAMENTO, "id_secullum": id_secullum, **valores})
					self._salvar(doc)
					resultado = CRIADO
				self.registrar(
					"equipamentos",
					resultado,
					str(id_secullum),
					valores["descricao"] or "",
					EQUIPAMENTO,
					doc.name,
				)
			except Exception as exc:
				self._desfazer()
				self.registrar("equipamentos", ERRO, str(id_secullum), str(exc))


def _vinculo_do_afastamento(vinculos: list, af, matricula: str | None) -> str | None:
	"""O vínculo do CPF que estava empregado no período (o da mesma matrícula, se houver mais de um)."""
	candidatos = [
		v
		for v in vinculos
		if v.date_of_joining
		and getdate(v.date_of_joining) <= af.fim
		and (not v.relieving_date or getdate(v.relieving_date) >= af.inicio)
	]
	if len(candidatos) > 1 and matricula:
		mesma = [v for v in candidatos if (v.matricula_secullum or "").strip() == str(matricula).strip()]
		candidatos = mesma or candidatos
	return candidatos[0].name if candidatos else None


def reapurar_dias_apurados(employee: str, inicio, fim, motivo: str) -> int:
	"""Marca para reapuração os dias já apurados do intervalo, fora de período fechado. Devolve quantos dias
	ficaram de fora por estarem fechados. Dias sem apuração ficam para a carga das batidas (Etapa 10)."""
	fechados = 0
	for dia in frappe.get_all(
		"Apuracao Diaria",
		filters={"employee": employee, "data": ["between", [getdate(inicio), getdate(fim)]]},
		pluck="data",
	):
		if periodo_fechado(employee, dia):
			fechados += 1
			continue
		marcar_para_reapuracao(employee, dia, motivo)
	return fechados


def _agrupar(pares) -> dict:
	saida = defaultdict(set)
	for chave, valor in pares:
		saida[chave].add(valor)
	return dict(saida)


GESTOR = "Gestor Ponto"


def garantir_usuario_gestor(employee: str) -> str | None:
	"""DI-8: usuário com o papel Gestor Ponto para o chefe que tem e-mail, sem e-mail de boas-vindas. Devolve o
	usuário (novo ou o já ligado ao colaborador) ou None se não houver e-mail."""
	emp = frappe.db.get_value(
		"Employee",
		employee,
		["user_id", "personal_email", "company_email", "first_name", "last_name"],
		as_dict=True,
	)
	usuario = emp.user_id or emp.company_email or emp.personal_email
	if not usuario:
		return None
	if not frappe.db.exists("User", usuario):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": usuario,
				"first_name": emp.first_name,
				"last_name": emp.last_name,
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", usuario)
	if GESTOR not in {r.role for r in user.roles}:
		user.add_roles(GESTOR)
	if not emp.user_id:
		frappe.db.set_value("Employee", employee, "user_id", usuario)
	return usuario


# ------------------------------------------------------------------ entrada

# sincronização diária (IS-08): os cadastros de todo dia, sem os feriados (job anual próprio)
PASSOS_DIARIOS = tuple(p for p in PASSOS if p != "feriados")


def sincronizar() -> dict | None:
	"""Job diário: repete a importação dos cadastros quando a origem é o Secullum e a sincronização está ligada.
	Nunca levanta exceção (erros ficam no log da importação e no Error Log)."""
	from hrms_secullum_brasil.ingestion.secullum import origem_secullum

	if not origem_secullum() or not frappe.db.get_single_value(
		"Configuracao Secullum", "sincronizar_cadastros"
	):
		return None
	try:
		resultado = ImportacaoSecullum().executar(list(PASSOS_DIARIOS))
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="Sincronização diária do Secullum")
		return None
	frappe.db.commit()
	return resultado["contagem"]


@frappe.whitelist()
def importar(passos=None, simular=1) -> dict:
	"""Importa (ou simula) os cadastros do Secullum. RH Ponto ou System Manager."""
	frappe.only_for(("System Manager", "RH Ponto"))
	if isinstance(passos, str):
		passos = frappe.parse_json(passos) if passos.startswith("[") else [passos]
	return ImportacaoSecullum(simular=bool(int(simular))).executar(passos)
