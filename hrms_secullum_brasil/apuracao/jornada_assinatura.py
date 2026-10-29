"""Alteração do horário fixo com assinatura (docs/PRD-cockpit-escalas.md, DE-17 / CE-16).

Fluxo: o RH/gestor monta o cenário (Alteracao de Jornada) com o novo horário de cada pessoa e a data de início →
classificação pelo engine (ciência, concordância, proibida; só dias flexíveis = dispensada) → "Enviar para
assinatura": termo de ciência ou aditivo, link pessoal no WhatsApp e código de confirmação → assinatura com trilha
(data/hora, IP, aparelho, SHA-256 do PDF anexado ao colaborador) ou em papel → **liberação só com todos**: o novo
horário entra no Histórico de horário a partir da data de início (nunca antes) → envio ao Secullum na data de início,
pela trava própria `Configuracao Secullum.envio_horarios`.

Recusa ou prazo vencido: nada muda; o gestor ajusta o cenário (tira a pessoa ou muda o horário) e só ela assina de
novo. O horário novo precisa existir no Secullum (perfil SEC-n igual): a API não cria horário.
"""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_url, getdate, now_datetime

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.cockpit_escala import hhmm, periodos_do_texto
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.configuracao_ponto.escala import periodos_da_linha
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
from hrms_secullum_brasil.engine import alteracao_jornada as aj
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine.escala import DIAS_SEMANA
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

CENARIO = "Alteracao de Jornada"
LINHA = "Alteracao de Jornada Linha"
PERFIL = "Perfil de Jornada"
PAPEIS = ("System Manager", "RH Ponto", "Gestor Ponto")
PAPEIS_RH = ("System Manager", "RH Ponto")
ASSINADAS = ("Assinado", "Assinado em papel")
DISPENSADA = "Dispensada"
TIPO = "alteracao_jornada"
TIPO_ENVIO = "envio_horario_secullum"
CODIGO_MINUTOS = 15
PRAZO_PADRAO_DIAS = 7


# ------------------------------------------------------------------ horários e classificação (etapa 14)


def horario_do_perfil(perfil) -> dict:
	if not perfil:
		return {}
	horario = {}
	for linha in perfil.dias:
		if cint(linha.get("neutro")) or linha.dia_semana not in DIAS_SEMANA:
			continue
		periodos = periodos_da_linha(linha)
		if periodos:
			horario[DIAS_SEMANA.index(linha.dia_semana)] = periodos
	return horario


def dias_flexiveis(emp) -> set[int]:
	"""Dias da semana com escala flexível no cadastro (todos, se "Escala flexível")."""
	if cint(emp.get("escala_flexivel")):
		return set(range(7))
	nomes = {n.split("-")[0].strip().lower()[:3]: i for i, n in enumerate(DIAS_SEMANA)}
	return {
		nomes[p.strip().lower()[:3]]
		for p in (emp.get("dias_flexiveis") or "").split(",")
		if p.strip().lower()[:3] in nomes
	}


def _fixo(horario: dict, flexiveis: set[int]) -> dict:
	"""Só o horário fixo: segunda a sexta que não são flexíveis (fim de semana segue o cockpit, sem assinatura)."""
	return {d: p for d, p in horario.items() if d < 5 and d not in flexiveis}


def he_habituais(employee: str, inicio: date) -> bool:
	"""Hora extra em pelo menos 4 dias em cada um dos 3 meses anteriores (Súmula 291)."""
	fim = inicio.replace(day=1) - timedelta(days=1)
	de = (fim.replace(day=1) - timedelta(days=62)).replace(day=1)
	por_mes = {}
	for linha in frappe.get_all(
		"Apuracao Diaria",
		filters={"employee": employee, "data": ["between", [de, fim]], "hora_extra": [">", 0]},
		pluck="data",
	):
		chave = getdate(linha).strftime("%Y-%m")
		por_mes[chave] = por_mes.get(chave, 0) + 1
	return len(por_mes) == 3 and all(n >= 4 for n in por_mes.values())


def perfil_do_secullum(horario: dict, company: str) -> str | None:
	"""Perfil importado do Secullum (com número de horário) com exatamente o mesmo horário semanal."""
	for nome in frappe.get_all(
		PERFIL,
		filters={"numero_horario_secullum": [">", 0]},
		or_filters=[["company", "=", company], ["company", "is", "not set"]],
		pluck="name",
	):
		if aj.mesmo_horario(horario_do_perfil(frappe.get_doc(PERFIL, nome)), horario):
			return nome
	return None


def _checar_visivel(employee: str) -> None:
	visiveis = employees_visiveis()
	if visiveis is not None and employee not in visiveis:
		frappe.throw(_("{0} está fora da sua equipe.").format(employee), frappe.PermissionError)


def validar_cenario(doc) -> None:
	"""Classifica cada linha (só no rascunho; depois de enviado o cenário não muda)."""
	if doc.situacao != "Rascunho":
		return
	vistos = set()
	inicio = getdate(doc.data_inicio)
	for linha in doc.linhas:
		if linha.employee in vistos:
			frappe.throw(_("{0} aparece mais de uma vez.").format(linha.employee_name or linha.employee))
		vistos.add(linha.employee)
		_checar_visivel(linha.employee)
		if not linha.perfil_desejado:
			frappe.throw(
				_("{0}: escolha o novo horário (perfil).").format(linha.employee_name or linha.employee)
			)
		emp = frappe.get_cached_doc("Employee", linha.employee)
		atual = get_perfil_vigente(linha.employee, inicio)
		antes = horario_do_perfil(atual)
		depois = horario_do_perfil(frappe.get_doc(PERFIL, linha.perfil_desejado))
		flex = dias_flexiveis(emp)
		ctx = aj.Contexto(
			horista=(emp.get("tipo_remuneracao") or "") in ("Horista", "Intermitente"),
			he_habituais=he_habituais(linha.employee, inicio),
		)
		if aj.mesmo_horario(_fixo(antes, flex), _fixo(depois, flex)):
			classificacao, motivos = (
				DISPENSADA,
				("só muda dia flexível (fim de semana ou dia flexível do contrato): sem assinatura.",),
			)
			resultado = aj.classificar(antes, depois, ctx)
		else:
			resultado = aj.classificar(_fixo(antes, flex), _fixo(depois, flex), ctx)
			classificacao, motivos = resultado.tipo, resultado.motivos
		secullum = perfil_do_secullum(depois, doc.company)
		linha.update(
			{
				"perfil_atual": atual.name if atual else None,
				"horario_novo": json.dumps(
					{DIAS_SEMANA[d]: [[hhmm(p.inicio), hhmm(p.fim)] for p in ps] for d, ps in depois.items()}
				),
				"resumo_antes": aj.resumo_do_horario(antes),
				"resumo_depois": aj.resumo_do_horario(depois),
				"carga_antes": aj.carga(antes),
				"carga_depois": aj.carga(depois),
				"noturno_depois": aj.noturno(depois),
				"classificacao": classificacao,
				"motivos": "\n".join(motivos),
				"perfil_secullum": secullum,
				"numero_secullum": cint(frappe.db.get_value(PERFIL, secullum, "numero_horario_secullum"))
				if secullum
				else 0,
			}
		)
		if resultado.tipo == aj.PROIBIDA and classificacao == DISPENSADA:
			linha.classificacao, linha.motivos = aj.PROIBIDA, "\n".join(resultado.motivos)
	if not doc.prazo_assinatura:
		doc.prazo_assinatura = max(getdate(), inicio - timedelta(days=1))


# ------------------------------------------------------------------ token, documento e WhatsApp (etapa 15)


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def gerar_token(cenario: str, linha: str) -> str:
	corpo = _b64(json.dumps({"a": cenario, "l": linha}).encode())
	return f"{corpo}.{_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())}"


def _linha_do_token(token: str):
	try:
		corpo, assinatura = str(token or "").split(".")
		if not hmac.compare_digest(
			_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest()), assinatura
		):
			raise ValueError
		dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
	except (ValueError, json.JSONDecodeError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	doc = frappe.get_doc(CENARIO, dados["a"])
	linha = next((x for x in doc.linhas if x.name == dados["l"]), None)
	if not linha:
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return doc, linha


def _tipo_documento(linha) -> str:
	return (
		"Aditivo ao contrato de trabalho"
		if linha.classificacao == aj.CONCORDANCIA
		else "Termo de ciência de ajuste de horário"
	)


def documento_html(doc, linha, trilha: dict | None = None) -> str:
	emp = frappe.get_cached_doc("Employee", linha.employee)
	empresa = frappe.get_cached_doc("Company", doc.company)
	clausula = (
		"As partes, de comum acordo e sem prejuízo ao empregado (CLT, art. 468), alteram o horário de trabalho "
		"conforme abaixo. As demais cláusulas do contrato continuam valendo."
		if linha.classificacao == aj.CONCORDANCIA
		else "O empregado declara ciência do ajuste do seu horário de trabalho, no mesmo turno, sem alteração da carga "
		"horária, do salário ou de adicionais. As demais condições do contrato continuam valendo."
	)
	return frappe.render_template(
		"""<div style="font-family: Arial, sans-serif; font-size: 12pt; line-height: 1.5">
<h2 style="text-align:center">{{ titulo }}</h2>
<p><b>Empregador:</b> {{ empresa.company_name }}{% if empresa.tax_id %} — CNPJ {{ empresa.tax_id }}{% endif %}<br>
<b>Empregado(a):</b> {{ emp.employee_name }}{% if emp.cpf %} — CPF {{ emp.cpf }}{% endif %}</p>
<p>{{ clausula }}</p>
<table border="1" cellpadding="6" style="border-collapse:collapse; width:100%">
<tr><th>Horário atual</th><td>{{ linha.resumo_antes }}</td></tr>
<tr><th>Novo horário</th><td>{{ linha.resumo_depois }}</td></tr>
<tr><th>Vale a partir de</th><td>{{ frappe.utils.formatdate(doc.data_inicio) }}</td></tr>
</table>
{% if linha.motivos %}<p><b>Observações:</b><br>{{ linha.motivos | replace("\\n", "<br>") }}</p>{% endif %}
{% if trilha %}
<hr><p><b>Assinado eletronicamente</b> (MP 2.200-2/2001, art. 10, §2º; Lei 14.063/2020) por {{ emp.employee_name }}
em {{ trilha.quando }}, CPF confirmado, código enviado ao celular cadastrado, IP {{ trilha.ip }},
aparelho: {{ trilha.aparelho }}.</p>
{% else %}<p style="margin-top:3em">______________________________<br>{{ emp.employee_name }}</p>{% endif %}
</div>""",
		{
			"titulo": _tipo_documento(linha),
			"empresa": empresa,
			"emp": emp,
			"clausula": clausula,
			"linha": linha,
			"doc": doc,
			"trilha": trilha,
		},
	)


@frappe.whitelist()
def enviar_para_assinatura(nome: str) -> dict:
	"""Rascunho → Em assinatura: link pessoal pelo WhatsApp (regra "Jornada: documento para assinar")."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(CENARIO, nome)
	doc.check_permission("write")
	if doc.situacao != "Rascunho":
		frappe.throw(_("O cenário já foi enviado."))
	doc.save()  # reclassifica com os dados de hoje
	proibidas = [x.employee_name for x in doc.linhas if x.classificacao == aj.PROIBIDA]
	if proibidas:
		frappe.throw(
			_("Mudança proibida para {0}: ajuste o horário antes de enviar.").format(", ".join(proibidas))
		)
	doc.db_set("situacao", "Em assinatura")
	enviados = 0
	for linha in doc.linhas:
		if linha.classificacao == DISPENSADA:
			continue
		if _avisar_documento(doc, linha):
			linha.db_set("assinatura", "Enviado")
			enviados += 1
	_tentar_liberar(doc.name)
	return {
		"enviados": enviados,
		"sem_whatsapp": sum(1 for x in doc.linhas if x.classificacao != DISPENSADA) - enviados,
	}


def _avisar_documento(doc, linha) -> str | None:
	from hrms_secullum_brasil.apuracao.whatsapp_escala import _nome_da_empresa, _regra_que_alcanca

	emp = frappe.get_cached_doc("Employee", linha.employee)
	regra = _regra_que_alcanca(com.ASSINATURA, emp)
	if not regra or not emp.cell_number:
		return None
	texto = montar_mensagem(
		regra.mensagem_colaborador or com.texto_padrao(com.ASSINATURA, "Colaborador"),
		primeiro_nome=com.primeiro_nome(emp.first_name or emp.employee_name),
		empresa=_nome_da_empresa(doc.company),
		documento=_tipo_documento(linha).lower(),
		data=getdate(doc.data_inicio).strftime("%d/%m/%Y"),
		prazo=getdate(doc.prazo_assinatura).strftime("%d/%m/%Y"),
		link=get_url(f"/ponto/assinar?token={gerar_token(doc.name, linha.name)}"),
	)
	nota = whatsapp.criar(
		linha.employee,
		"Colaborador",
		emp.cell_number,
		texto,
		regra=regra.name,
		chave=f"ASS:{doc.name}:{linha.name}",
	)
	whatsapp.enviar(nota)
	return nota


# ------------------------------------------------------------------ página de assinatura (sem login)


def _aberta(doc, linha) -> None:
	if doc.situacao != "Em assinatura" or linha.assinatura not in ("Pendente", "Enviado"):
		frappe.throw(_("Este documento não está mais aguardando assinatura."))
	if doc.prazo_assinatura and getdate() > getdate(doc.prazo_assinatura):
		frappe.throw(_("O prazo para assinar terminou. Fale com o seu gestor."))


@frappe.whitelist(allow_guest=True)
def documento(token: str) -> dict:
	doc, linha = _linha_do_token(token)
	return {
		"titulo": _tipo_documento(linha),
		"html": documento_html(doc, linha),
		"situacao": linha.assinatura,
		"aberto": doc.situacao == "Em assinatura" and linha.assinatura in ("Pendente", "Enviado"),
		"prazo": str(doc.prazo_assinatura or ""),
	}


def _hash_codigo(linha_nome: str, codigo: str) -> str:
	return hashlib.sha256(f"{linha_nome}:{codigo}".encode()).hexdigest()


@frappe.whitelist(allow_guest=True, methods=["POST"])
def pedir_codigo(token: str) -> dict:
	"""Código de 6 dígitos (15 min) pelo WhatsApp do cadastro; não passa pela homologação (é segurança)."""
	doc, linha = _linha_do_token(token)
	_aberta(doc, linha)
	emp = frappe.get_cached_doc("Employee", linha.employee)
	if not emp.cell_number:
		frappe.throw(_("Sem celular no cadastro: assine em papel com o RH."))
	codigo = f"{secrets.randbelow(10**6):06d}"
	frappe.db.set_value(
		LINHA,
		linha.name,
		{
			"codigo_hash": _hash_codigo(linha.name, codigo),
			"codigo_expira": add_to_date(now_datetime(), minutes=CODIGO_MINUTOS),
		},
		update_modified=False,
	)
	nota = whatsapp.criar(
		linha.employee,
		"Colaborador",
		emp.cell_number,
		f"Seu código para assinar o documento de horário: {codigo}. Não compartilhe.",
	)
	situacao = whatsapp.enviar(nota, ignorar_horario=True)
	frappe.db.commit()
	return {"enviado": situacao == "Enviada", "celular": f"(**) *****-{str(emp.cell_number)[-4:]}"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def assinar(token: str, cpf: str, codigo: str) -> str:
	doc, linha = _linha_do_token(token)
	_aberta(doc, linha)
	emp = frappe.get_cached_doc("Employee", linha.employee)
	digitos = "".join(c for c in str(cpf or "") if c.isdigit())
	if not emp.cpf or digitos != "".join(c for c in str(emp.cpf) if c.isdigit()):
		frappe.throw(_("CPF não confere."))
	valido = linha.codigo_hash and hmac.compare_digest(
		linha.codigo_hash, _hash_codigo(linha.name, str(codigo or "").strip())
	)
	if (
		not valido
		or not linha.codigo_expira
		or now_datetime() > frappe.utils.get_datetime(linha.codigo_expira)
	):
		frappe.throw(_("Código inválido ou vencido: peça outro."))
	quando = now_datetime()
	trilha = {
		"quando": frappe.utils.format_datetime(quando, "dd/MM/yyyy HH:mm:ss"),
		"ip": getattr(frappe.local, "request_ip", None) or "-",
		"aparelho": (_cabecalho("User-Agent") or "-")[:300],
	}
	_anexar_assinado(doc, linha, documento_html(doc, linha, trilha), quando, trilha)
	_tentar_liberar(doc.name)
	frappe.db.commit()
	return "Assinado"


def _cabecalho(nome: str) -> str | None:
	"""Cabeçalho da requisição (fora de uma requisição web, como nos jobs e testes, não há)."""
	return frappe.get_request_header(nome) if getattr(frappe.local, "request", None) else None


def _anexar_assinado(doc, linha, html: str, quando, trilha: dict) -> None:
	from frappe.utils.pdf import get_pdf

	pdf = get_pdf(html)
	arquivo = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{_tipo_documento(linha)} - {doc.name}.pdf",
			"attached_to_doctype": "Employee",
			"attached_to_name": linha.employee,
			"is_private": 1,
			"content": pdf,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value(
		LINHA,
		linha.name,
		{
			"assinatura": "Assinado",
			"documento": arquivo.file_url,
			"hash_documento": hashlib.sha256(pdf).hexdigest(),
			"assinado_em": quando,
			"assinatura_ip": trilha["ip"],
			"assinatura_aparelho": trilha["aparelho"],
			"codigo_hash": None,
		},
		update_modified=False,
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def recusar(token: str) -> str:
	doc, linha = _linha_do_token(token)
	_aberta(doc, linha)
	frappe.db.set_value(LINHA, linha.name, "assinatura", "Recusado", update_modified=False)
	_avisar_gestor(doc, linha, _("recusou o novo horário: nada muda; ajuste o cenário."))
	frappe.db.commit()
	return "Recusado"


@frappe.whitelist()
def registrar_papel(nome: str, linha: str) -> str:
	"""Sem WhatsApp: o RH anexa o documento assinado em papel e registra."""
	frappe.only_for(PAPEIS_RH)
	doc = frappe.get_doc(CENARIO, nome)
	item = next((x for x in doc.linhas if x.name == linha), None)
	if not item or not item.documento_papel:
		frappe.throw(_("Anexe o documento assinado em papel na linha antes de registrar."))
	_aberta(doc, item)
	conteudo = frappe.get_doc("File", {"file_url": item.documento_papel}).get_content()
	conteudo = conteudo if isinstance(conteudo, bytes) else str(conteudo).encode()
	frappe.db.set_value(
		LINHA,
		item.name,
		{
			"assinatura": "Assinado em papel",
			"documento": item.documento_papel,
			"hash_documento": hashlib.sha256(conteudo).hexdigest(),
			"assinado_em": now_datetime(),
		},
		update_modified=False,
	)
	_tentar_liberar(doc.name)
	return "Assinado em papel"


@frappe.whitelist()
def imprimir(nome: str, linha: str):
	"""PDF do documento (para colher a assinatura em papel)."""
	frappe.only_for(PAPEIS)
	from frappe.utils.pdf import get_pdf

	doc = frappe.get_doc(CENARIO, nome)
	item = next(x for x in doc.linhas if x.name == linha)
	frappe.local.response.filename = f"{_tipo_documento(item)} - {item.employee_name}.pdf"
	frappe.local.response.filecontent = get_pdf(documento_html(doc, item))
	frappe.local.response.type = "download"


# ------------------------------------------------------------------ liberação e Secullum (etapa 16)


def _avisar_gestor(doc, linha, texto: str) -> None:
	from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia

	registrar_inconsistencia(
		linha.employee,
		TIPO,
		f"Alteração de horário {doc.name}: {linha.employee_name or linha.employee} {texto}",
		severidade="Média",
		referencia_doctype=CENARIO,
		referencia_name=doc.name,
	)


def _tentar_liberar(nome: str) -> bool:
	"""Só com todos: assinaturas (ou dispensa) e o horário existente no Secullum; aí o horário entra no histórico a
	partir da data de início e os dias já apurados desde ela são reapurados."""
	from hrms_secullum_brasil.apuracao.inconsistencias import resolver_inconsistencias
	from hrms_secullum_brasil.ingestion.importacao_secullum import reapurar_dias_apurados

	doc = frappe.get_doc(CENARIO, nome)
	if doc.situacao != "Em assinatura":
		return False
	if any(x.classificacao != DISPENSADA and x.assinatura not in ASSINADAS for x in doc.linhas):
		return False
	sem_horario = [x for x in doc.linhas if not x.perfil_secullum]
	for linha in sem_horario:
		_avisar_gestor(
			doc, linha, _("assinou, mas falta criar no Secullum o horário: {0}.").format(linha.resumo_depois)
		)
	if sem_horario:
		return False
	inicio = getdate(doc.data_inicio)
	for linha in doc.linhas:
		frappe.get_doc(
			{
				"doctype": "Historico Perfil Jornada",
				"parent": linha.employee,
				"parenttype": "Employee",
				"parentfield": "historico_perfil_jornada",
				"desde": inicio,
				"perfil_jornada": linha.perfil_secullum,
				"observacao": f"Alteração de horário {doc.name}"[:140],
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value(LINHA, linha.name, "envio_secullum", "Aguardando", update_modified=False)
		resolver_inconsistencias(linha.employee, TIPO)
		if inicio <= getdate():
			reapurar_dias_apurados(linha.employee, inicio, getdate(), f"Alteração de horário {doc.name}")
	doc.db_set("situacao", "Liberada")
	return True


def acompanhar() -> None:
	"""Job diário: prazo vencido → Vencido e aviso ao gestor; horário criado no Secullum → liga e libera; na data de
	início, envia o horário ao Secullum."""
	hoje = getdate()
	for nome in frappe.get_all(CENARIO, filters={"situacao": "Em assinatura"}, pluck="name"):
		doc = frappe.get_doc(CENARIO, nome)
		for linha in doc.linhas:
			if not linha.perfil_secullum:
				horario = {
					DIAS_SEMANA.index(d): periodos_do_texto(p)
					for d, p in json.loads(linha.horario_novo or "{}").items()
				}
				achado = perfil_do_secullum(horario, doc.company)
				if achado:
					frappe.db.set_value(
						LINHA,
						linha.name,
						{
							"perfil_secullum": achado,
							"numero_secullum": cint(
								frappe.db.get_value(PERFIL, achado, "numero_horario_secullum")
							),
						},
						update_modified=False,
					)
			if (
				linha.assinatura in ("Pendente", "Enviado")
				and doc.prazo_assinatura
				and hoje > getdate(doc.prazo_assinatura)
			):
				frappe.db.set_value(LINHA, linha.name, "assinatura", "Vencido", update_modified=False)
				_avisar_gestor(doc, linha, _("não assinou no prazo: nada muda; ajuste o cenário."))
		_tentar_liberar(nome)
	enviar_ao_secullum(hoje)


def envio_liberado() -> bool:
	return frappe.db.get_single_value("Configuracao Secullum", "envio_horarios") == "Sempre enviar"


def enviar_ao_secullum(hoje: date | None = None) -> int:
	"""Na data de início: lê o funcionário no Secullum e manda o cadastro igual, mudando só o HorarioNumero (o POST
	grava o cadastro inteiro). Falha vira `envio_horario_secullum` e não desfaz o horário no programa."""
	from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia
	from hrms_secullum_brasil.ingestion.secullum import get_client, id_banco_da_empresa

	hoje = hoje or getdate()
	enviados = 0
	for nome in frappe.get_all(
		CENARIO, filters={"situacao": "Liberada", "data_inicio": ["<=", hoje]}, pluck="name"
	):
		doc = frappe.get_doc(CENARIO, nome)
		for linha in doc.linhas:
			if linha.envio_secullum not in ("Aguardando", "Bloqueado"):
				continue
			if not envio_liberado():
				frappe.db.set_value(LINHA, linha.name, "envio_secullum", "Bloqueado", update_modified=False)
				continue
			cpf = frappe.db.get_value("Employee", linha.employee, "cpf")
			try:
				cliente = get_client(id_banco_da_empresa(doc.company))
				funcionario = cliente.buscar_funcionario_por_cpf(cpf)
				if not funcionario:
					raise ValueError(_("funcionário não encontrado no Secullum pelo CPF"))
				funcionario["HorarioNumero"] = cint(linha.numero_secullum)
				cliente.salvar_funcionario(funcionario)
			except Exception as erro:  # erro operacional vira pendência; o job não para
				frappe.db.set_value(
					LINHA,
					linha.name,
					{"envio_secullum": "Erro", "envio_resposta": str(erro)[:1000]},
					update_modified=False,
				)
				registrar_inconsistencia(
					linha.employee,
					TIPO_ENVIO,
					f"O novo horário ({linha.resumo_depois}) não foi enviado ao Secullum: {erro}. No programa ele já vale.",
					severidade="Média",
					referencia_doctype=CENARIO,
					referencia_name=doc.name,
				)
				continue
			frappe.db.set_value(
				LINHA,
				linha.name,
				{"envio_secullum": "Enviado", "envio_resposta": None},
				update_modified=False,
			)
			enviados += 1
	return enviados
