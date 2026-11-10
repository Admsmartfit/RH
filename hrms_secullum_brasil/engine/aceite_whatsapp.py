"""Aceite do colaborador para receber WhatsApp (docs/PRD-whatsapp-aceite-auditoria.md, CW-01 a CW-07). Python puro.

O colaborador abre a página do QR, informa CPF e data de nascimento, confere o celular, aceita, salva o contato e
manda a primeira mensagem (o WhatsApp bloqueia números que só enviam). O programa não lê mensagens.
"""

import re
from datetime import date, datetime
from urllib.parse import quote

PENDENTE = "Pendente"
ACEITO = "Aceito"
REVOGADO = "Revogado"
SITUACOES = (PENDENTE, ACEITO, REVOGADO)

ACEITE = "Aceite"
REVOGACAO = "Revogação"

NOME_CONTATO_PADRAO = "Ponto ES Fitness"

VERSAO_TEXTO = "1"
TEXTO_ACEITE = (
	"Aceito receber pelo WhatsApp os avisos do meu ponto, da minha escala e os termos de ocorrências, "
	"só das 8h às 20h. Sei que posso pedir para parar a qualquer momento ao meu gerente ou ao RH."
)
TEXTO_PRIMEIRA_MENSAGEM = "Olá! Sou {nome}, salvei o contato e aceito receber os avisos do meu ponto."


def so_digitos(valor: str | None) -> str:
	return re.sub(r"\D", "", str(valor or ""))


def mascarar_celular(numero: str | None) -> str:
	""" "(27) *****-1234"; vazio se não houver número."""
	digitos = so_digitos(numero)
	if digitos.startswith("55") and len(digitos) in (12, 13):
		digitos = digitos[2:]
	if len(digitos) < 4:
		return ""
	ddd = f"({digitos[:2]}) " if len(digitos) >= 10 else ""
	return f"{ddd}*****-{digitos[-4:]}"


def _data(valor) -> date | None:
	if isinstance(valor, date):
		return valor
	texto = str(valor or "").strip()
	for formato in ("%Y-%m-%d", "%d/%m/%Y"):
		try:
			return datetime.strptime(texto, formato).date()
		except ValueError:
			continue
	return None


def confere(cpf: str | None, nascimento, cpf_cadastro: str | None, nascimento_cadastro) -> bool:
	"""CW-02: CPF (só os dígitos) e data de nascimento iguais aos do cadastro."""
	informado = so_digitos(cpf)
	if len(informado) != 11 or informado != so_digitos(cpf_cadastro):
		return False
	data = _data(nascimento)
	return data is not None and data == _data(nascimento_cadastro)


def situacao_depois_da_mudanca(
	situacao: str | None, celular_aceito: str | None, celular_novo: str | None
) -> str:
	"""CW-07: celular trocado depois do aceite volta a Pendente (o novo número precisa aceitar)."""
	situacao = situacao or PENDENTE
	if situacao == ACEITO and so_digitos(celular_aceito)[-8:] != so_digitos(celular_novo)[-8:]:
		return PENDENTE
	return situacao


def primeiro_nome(nome: str | None) -> str:
	return (str(nome or "").split() or [""])[0].capitalize()


def vcard(nome: str, numero: str) -> str:
	"""Cartão de contato (.vcf) com o nome e o número da empresa."""
	digitos = so_digitos(numero)
	return "\r\n".join(
		[
			"BEGIN:VCARD",
			"VERSION:3.0",
			f"FN:{nome}",
			f"N:{nome};;;;",
			f"TEL;TYPE=CELL;waid={digitos}:+{digitos}",
			"END:VCARD",
			"",
		]
	)


def link_primeira_mensagem(numero_empresa: str, nome: str | None) -> str:
	"""https://wa.me/<número>?text=... com a primeira mensagem pronta."""
	texto = TEXTO_PRIMEIRA_MENSAGEM.format(nome=primeiro_nome(nome) or "colaborador")
	return f"https://wa.me/{so_digitos(numero_empresa)}?text={quote(texto)}"
