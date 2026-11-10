"""Relatório de auditoria (docs/PRD-whatsapp-aceite-auditoria.md, AU-01 a AU-06). Python puro.

Recebe as linhas de cada seção já lidas (dicts vindos do banco) e devolve o relatório montado: uma descrição curta por
linha, organizada por empresa e, dentro dela, por seção e colaborador, com o resumo em números. Nunca leva dado de
saúde (CID, anexo de atestado): o motivo de um atestado aparece só como "Atestado"; CPF sempre mascarado.
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

CORRECOES = "correcoes"
RELOGIO = "relogio"
RESPOSTAS = "respostas"
TERMOS = "termos"
WHATSAPP = "whatsapp"
EMAILS = "emails"
SECULLUM = "secullum"
RETROATIVAS = "retroativas"
ESCALA = "escala"
MANTIDAS = "mantidas"
CADASTRO = "cadastro"
ACEITES = "aceites"

SECOES = {
	CORRECOES: "Correções do ponto",
	RELOGIO: "Batidas do relógio desconsideradas",
	RESPOSTAS: "Respostas do colaborador (WhatsApp do dia seguinte)",
	TERMOS: "Termos de ocorrências",
	WHATSAPP: "Mensagens de WhatsApp",
	EMAILS: "E-mails enviados",
	SECULLUM: "Envio ao Secullum",
	RETROATIVAS: "Alterações vindas do Secullum",
	ESCALA: "Escala",
	MANTIDAS: "Inconsistências mantidas",
	CADASTRO: "Cadastro e regras",
	ACEITES: "Aceites de WhatsApp",
}
DESTAQUES = {RELOGIO}
GERAL = "Geral (todas as empresas)"
LINHAS_POR_PAGINA = 30
PAGINAS_PARA_INDICE = 10

# chaves que nunca entram no relatório (LGPD: dados de saúde ficam em permlevel 1)
_SAUDE = re.compile(r"(^|_)(cid|atestado_anexo|anexo_atestado|anexos_atestado)($|_)", re.IGNORECASE)


@dataclass(frozen=True)
class Linha:
	secao: str
	descricao: str
	company: str | None = None
	employee: str | None = None
	employee_name: str | None = None
	dia: date | None = None
	quando: datetime | None = None
	doctype: str | None = None
	name: str | None = None


@dataclass
class Relatorio:
	inicio: date
	fim: date
	tipo: str
	resumo: dict[str, int] = field(default_factory=dict)
	empresas: list[dict] = field(default_factory=list)
	total: int = 0
	indice: list[dict] = field(default_factory=list)

	@property
	def tem_conteudo(self) -> bool:
		return self.total > 0


# ------------------------------------------------------------------ utilidades


def limpar(linha: dict) -> dict:
	"""Tira qualquer chave de saúde (CID, anexo de atestado) antes de montar a linha."""
	return {k: v for k, v in (linha or {}).items() if not _SAUDE.search(str(k))}


def mascarar_cpf(cpf: str | None) -> str:
	digitos = re.sub(r"\D", "", str(cpf or ""))
	if len(digitos) != 11:
		return ""
	return f"***.{digitos[3:6]}.***-{digitos[9:]}"


def final_celular(numero: str | None) -> str:
	digitos = re.sub(r"\D", "", str(numero or ""))
	return f"final {digitos[-4:]}" if len(digitos) >= 4 else "sem celular"


def _dt(valor) -> datetime | None:
	if isinstance(valor, datetime):
		return valor
	if isinstance(valor, date):
		return datetime(valor.year, valor.month, valor.day)
	texto = str(valor or "").strip()[:19]
	for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
		try:
			return datetime.strptime(texto, formato)
		except ValueError:
			continue
	return None


def _d(valor) -> date | None:
	quando = _dt(valor)
	return quando.date() if quando else None


def quando_br(valor) -> str:
	quando = _dt(valor)
	return quando.strftime("%d/%m %H:%M") if quando else "-"


def dia_br(valor) -> str:
	dia = _d(valor)
	return dia.strftime("%d/%m/%Y") if dia else "-"


def hora(valor) -> str:
	quando = _dt(valor)
	return quando.strftime("%H:%M") if quando else "-"


def _quem(usuario: str | None) -> str:
	return usuario or "-"


def rota(doctype: str | None, name: str | None) -> str:
	"""Caminho do registro no Desk (/app/<doctype>/<nome>)."""
	if not doctype or not name:
		return ""
	return f"/app/{doctype.lower().replace(' ', '-')}/{name}"


def _e_atestado(*textos) -> bool:
	return any("atestado" in str(t or "").lower() for t in textos)


def _base(secao: str, r: dict, **extra) -> dict:
	return {
		"secao": secao,
		"company": r.get("company"),
		"employee": r.get("employee"),
		"employee_name": r.get("employee_name"),
		**extra,
	}


# ------------------------------------------------------------------ uma linha por seção


def linha_tratamento(r: dict) -> Linha:
	"""Cada Tratamento de Ponto: o que mudou, motivo, quem fez e quem aprovou."""
	r = limpar(r)
	tipo = r.get("tipo") or ""
	if tipo == "Inclusao de marcacao":
		oque = f"Incluiu {hora(r.get('data_hora'))}"
	elif tipo == "Desconsiderar marcacao":
		oque = f"Desconsiderou {hora(r.get('data_hora'))}"
	elif tipo == "Abono parcial":
		oque = f"Abono parcial de {int(r.get('minutos_abonados') or 0)} min"
	elif tipo in ("Abono do dia", "Falta justificada"):
		oque = tipo
	else:
		oque = tipo or "Correção"
	motivo = r.get("motivo") or ""
	if _e_atestado(r.get("justificativa"), motivo):
		motivo = "Atestado"  # nunca o CID nem o texto do atestado
	elif r.get("justificativa"):
		motivo = f"{r.get('justificativa')}: {motivo}" if motivo else str(r.get("justificativa"))
	partes = [oque, motivo or "sem motivo", f"por {_quem(r.get('owner'))}"]
	docstatus = int(r.get("docstatus") or 0)
	if docstatus == 2:
		partes.append("CANCELADO")
	elif docstatus == 1:
		partes.append(f"aprovado por {_quem(r.get('aprovado_por'))} em {quando_br(r.get('aprovado_em'))}")
	else:
		partes.append("aguardando aprovação")
	if r.get("anexo"):
		partes.append("com anexo")
	secao = (
		RELOGIO
		if tipo == "Desconsiderar marcacao" and int(r.get("confirmou_apagar_relogio") or 0)
		else CORRECOES
	)
	if secao == RELOGIO:
		partes.insert(
			1,
			f"batida do relógio; as duas confirmações por {_quem(r.get('owner'))} em "
			f"{quando_br(r.get('creation'))}",
		)
	return Linha(
		**_base(secao, r),
		descricao=" — ".join(partes),
		dia=_d(r.get("data")),
		quando=_dt(r.get("modified") or r.get("creation")),
		doctype="Tratamento de Ponto",
		name=r.get("name"),
	)


def resumo_dias_resposta(dias) -> str:
	"""Os dias da resposta do WhatsApp: "03/11: 08:00 12:00 → 08:00 12:00 13:00 17:00"."""
	partes = []
	for d in dias or []:
		dia = _d(d.get("data"))
		rotulo = dia.strftime("%d/%m") if dia else "-"
		if int(d.get("nao_reconhece") or 0):
			partes.append(f"{rotulo}: não reconhece")
		elif (d.get("horarios_informados") or "") != (d.get("horarios_antes") or ""):
			partes.append(
				f"{rotulo}: {d.get('horarios_antes') or '(sem batidas)'} → {d.get('horarios_informados') or '-'}"
			)
		else:
			partes.append(f"{rotulo}: confirmou")
		if d.get("explicacao"):
			partes[-1] += f" (explicou: {str(d.get('explicacao'))[:80]})"
	return "; ".join(partes)


def linha_resposta(r: dict) -> Linha:
	r = limpar(r)
	partes = [
		f"Confirmou em {quando_br(r.get('confirmado_em'))} (CPF + código)",
		r.get("resumo") or "",
		f"situação: {r.get('situacao') or '-'}",
	]
	if r.get("aprovado_por"):
		partes.append(f"por {r.get('aprovado_por')} em {quando_br(r.get('aprovado_em'))}")
	if r.get("motivo_recusa"):
		partes.append(f"motivo da recusa: {r.get('motivo_recusa')}")
	return Linha(
		**_base(RESPOSTAS, r),
		descricao=" — ".join(p for p in partes if p),
		quando=_dt(r.get("modified") or r.get("confirmado_em")),
		doctype="Resposta WhatsApp Ponto",
		name=r.get("name"),
	)


def linha_termo(r: dict) -> Linha:
	r = limpar(r)
	partes = [
		f"Termo de {dia_br(r.get('inicio'))} a {dia_br(r.get('fim'))}",
		f"emitido por {_quem(r.get('emitido_por'))} em {quando_br(r.get('emitido_em'))}",
		f"situação: {r.get('status') or '-'}",
	]
	if r.get("confirmado_em"):
		via = f" ({r.get('via')})" if r.get("via") else ""
		partes.append(
			f"confirmado{via} por {r.get('confirmado_por') or '-'} em {quando_br(r.get('confirmado_em'))}"
		)
	if r.get("cancelado_motivo"):
		partes.append(f"cancelado: {r.get('cancelado_motivo')}")
	return Linha(
		**_base(TERMOS, r),
		descricao=" — ".join(partes),
		quando=_dt(r.get("modified")),
		doctype="Termo de Ocorrencias",
		name=r.get("name"),
	)


def linha_whatsapp(r: dict) -> Linha:
	r = limpar(r)
	partes = [f"Para {r.get('destinatario') or '-'} ({final_celular(r.get('numero'))})"]
	if r.get("regra"):
		partes.append(str(r.get("regra")))
	partes.append(f"situação: {r.get('situacao') or '-'}")
	if r.get("enviada_em"):
		partes.append(f"enviada {quando_br(r.get('enviada_em'))}")
	if r.get("entregue_em"):
		partes.append(f"entregue {quando_br(r.get('entregue_em'))}")
	if r.get("lida_em"):
		partes.append(f"lida {quando_br(r.get('lida_em'))}")
	if r.get("situacao") == "Barrada" and r.get("filtro"):
		partes.append(f"motivo: {r.get('filtro')}")
	return Linha(
		**_base(WHATSAPP, r),
		descricao=" — ".join(partes),
		dia=_d(r.get("dia")),
		quando=_dt(r.get("creation")),
		doctype="Notificacao WhatsApp",
		name=r.get("name"),
	)


def linha_email(r: dict) -> Linha:
	r = limpar(r)
	referencia = f"{r.get('reference_doctype')} {r.get('reference_name')}" if r.get("reference_name") else "-"
	descricao = (
		f"Para {r.get('destinatarios') or '-'} — sobre {referencia} — situação: {r.get('status') or '-'}"
	)
	return Linha(
		**_base(EMAILS, r),
		descricao=descricao,
		quando=_dt(r.get("creation")),
		doctype="Email Queue",
		name=r.get("name"),
	)


def linha_envio_secullum(r: dict, doctype: str = "Envio Secullum") -> Linha:
	r = limpar(r)
	oque = r.get("descricao") or r.get("tipo") or "Correção do cartão"
	partes = [oque, f"dia {dia_br(r.get('data'))}", f"situação: {r.get('situacao') or '-'}"]
	if r.get("usuario"):
		partes.append(f"por {r.get('usuario')}")
	if r.get("situacao") in ("Erro", "Divergente") and r.get("resposta"):
		partes.append(str(r.get("resposta"))[:160])
	return Linha(
		**_base(SECULLUM, r),
		descricao=" — ".join(partes),
		dia=_d(r.get("data")),
		quando=_dt(r.get("modified") or r.get("creation")),
		doctype=doctype,
		name=r.get("name"),
	)


def linha_inconsistencia(r: dict) -> Linha:
	"""Retroativa do Secullum ou inconsistência mantida (pelo status)."""
	r = limpar(r)
	if r.get("status") == "Mantida":
		descricao = (
			f"{r.get('tipo') or '-'} — mantida por {_quem(r.get('mantida_por'))} em {quando_br(r.get('mantida_em'))}"
			f" — motivo: {r.get('motivo_manter') or '-'}"
		)
		secao, quando = MANTIDAS, r.get("mantida_em")
	else:
		descricao = f"Dia {dia_br(r.get('data'))} mudou no Secullum — {r.get('descricao') or ''}".rstrip(" —")
		secao, quando = RETROATIVAS, r.get("creation")
	return Linha(
		**_base(secao, r),
		descricao=descricao,
		dia=_d(r.get("data")),
		quando=_dt(quando),
		doctype="Inconsistencia de Ponto",
		name=r.get("name"),
	)


def linha_publicacao(r: dict) -> Linha:
	descricao = (
		f"Escala publicada por {_quem(r.get('publicado_por'))} em {quando_br(r.get('publicado_em'))}"
		f" — de {dia_br(r.get('inicio'))} a {dia_br(r.get('fim'))} — {int(r.get('colaboradores') or 0)} colaborador(es)"
	)
	if int(r.get("urgente") or 0):
		descricao += " — mudança urgente"
	return Linha(
		secao=ESCALA,
		company=r.get("company"),
		descricao=descricao,
		quando=_dt(r.get("publicado_em")),
		doctype="Publicacao de Escala",
		name=r.get("name"),
	)


def linha_troca(r: dict) -> Linha:
	r = limpar(r)
	descricao = (
		f"Troca de escala aprovada por {_quem(r.get('aprovado_por'))} em {quando_br(r.get('aprovado_em'))}"
		f" — motivo: {r.get('motivo') or '-'}"
	)
	return Linha(
		**_base(ESCALA, r),
		descricao=descricao,
		quando=_dt(r.get("aprovado_em") or r.get("modified")),
		doctype="Troca de Escala",
		name=r.get("name"),
	)


def linha_convite(r: dict) -> Linha:
	r = limpar(r)
	descricao = (
		f"Convite para turno de {dia_br(r.get('data'))} {r.get('horario') or ''}".rstrip()
		+ f' — respondeu "{r.get("resposta") or "-"}" em {quando_br(r.get("respondido_em"))}'
	)
	return Linha(
		**_base(ESCALA, r),
		descricao=descricao,
		dia=_d(r.get("data")),
		quando=_dt(r.get("respondido_em")),
		doctype="Convite de Turno",
		name=r.get("parent"),
	)


def mudancas_da_versao(dados) -> list[tuple[str, str, str]]:
	"""(campo, antes, depois) do `data` de uma Version; ignora campos de saúde."""
	try:
		conteudo = json.loads(dados) if isinstance(dados, str) else dict(dados or {})
	except (TypeError, ValueError):
		return []
	mudancas = []
	for item in conteudo.get("changed") or []:
		if len(item) >= 3 and not _SAUDE.search(str(item[0])):
			mudancas.append((str(item[0]), str(item[1] if item[1] is not None else ""), str(item[2] or "")))
	return mudancas


def linha_versao(r: dict, maximo: int = 6) -> Linha | None:
	mudancas = mudancas_da_versao(r.get("data"))
	if not mudancas:
		return None
	texto = "; ".join(f"{c}: {a or '(vazio)'} → {d or '(vazio)'}" for c, a, d in mudancas[:maximo])
	if len(mudancas) > maximo:
		texto += f"; e mais {len(mudancas) - maximo}"
	return Linha(
		secao=CADASTRO,
		company=r.get("company"),
		descricao=f"{r.get('ref_doctype')} {r.get('docname')} — por {_quem(r.get('owner'))} em "
		f"{quando_br(r.get('creation'))} — {texto}",
		quando=_dt(r.get("creation")),
		doctype=r.get("ref_doctype"),
		name=r.get("docname"),
	)


def linha_aceite(r: dict) -> Linha:
	r = limpar(r)
	if r.get("acao") == "Revogação":
		descricao = (
			f"Revogado por {_quem(r.get('registrado_por'))} em {quando_br(r.get('registrado_em'))}"
			f" — motivo: {r.get('motivo') or '-'}"
		)
	else:
		passos = []
		if r.get("salvou_contato_em"):
			passos.append("salvou o contato")
		if r.get("primeira_mensagem_em"):
			passos.append("tocou em enviar a primeira mensagem")
		descricao = (
			f"Aceitou em {quando_br(r.get('registrado_em'))} ({final_celular(r.get('numero'))}, texto versão "
			f"{r.get('versao_texto') or '-'}, IP {r.get('ip') or '-'})"
		)
		if passos:
			descricao += " — " + ", ".join(passos)
	return Linha(
		**_base(ACEITES, r),
		descricao=descricao,
		quando=_dt(r.get("registrado_em") or r.get("creation")),
		doctype="Aceite WhatsApp",
		name=r.get("name"),
	)


# ------------------------------------------------------------------ montagem


def montar(linhas, inicio: date, fim: date, tipo: str) -> Relatorio:
	"""Empresa → seção (na ordem de SECOES) → colaborador e dia. Linhas sem empresa (regras gerais) vão para "Geral".
	O índice por colaborador entra quando o relatório passa de ~10 páginas."""
	validas = [linha for linha in linhas if linha is not None]
	relatorio = Relatorio(inicio=inicio, fim=fim, tipo=tipo, total=len(validas))
	relatorio.resumo = {chave: 0 for chave in SECOES}
	por_empresa: dict[str, dict[str, list[Linha]]] = defaultdict(lambda: defaultdict(list))
	for linha in validas:
		relatorio.resumo[linha.secao] = relatorio.resumo.get(linha.secao, 0) + 1
		por_empresa[linha.company or GERAL][linha.secao].append(linha)

	def chave(linha: Linha):
		return (
			(linha.employee_name or "").lower(),
			linha.dia or date.min,
			linha.quando or datetime.min,
			linha.name or "",
		)

	ordem_empresas = sorted(por_empresa, key=lambda e: (e == GERAL, e.lower()))
	for empresa in ordem_empresas:
		secoes = []
		for secao, titulo in SECOES.items():
			itens = sorted(por_empresa[empresa].get(secao, []), key=chave)
			if itens:
				secoes.append(
					{"chave": secao, "titulo": titulo, "destaque": secao in DESTAQUES, "linhas": itens}
				)
		relatorio.empresas.append({"empresa": empresa, "secoes": secoes})

	if relatorio.total > LINHAS_POR_PAGINA * PAGINAS_PARA_INDICE:
		contagem: dict[tuple[str, str], int] = defaultdict(int)
		for linha in validas:
			if linha.employee_name:
				contagem[(linha.company or GERAL, linha.employee_name)] += 1
		relatorio.indice = [
			{"empresa": e, "employee_name": n, "linhas": q} for (e, n), q in sorted(contagem.items())
		]
	return relatorio


def resumo_em_texto(relatorio: Relatorio) -> str:
	"""Uma linha por seção com movimento (para o registro e o corpo do e-mail)."""
	return "\n".join(f"{SECOES[c]}: {n}" for c, n in relatorio.resumo.items() if n)
