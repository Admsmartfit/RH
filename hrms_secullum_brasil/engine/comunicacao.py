"""Comunicação com o colaborador por WhatsApp (docs/configuracao_operacao.md): textos padrão das regras de envio e
quem a regra alcança. Python puro; o envio e a trava ficam em apuracao/whatsapp.py e apuracao/regras_whatsapp.py.
"""

from collections.abc import Iterable
from datetime import date

BATIDA_ESQUECIDA = "Ponto do dia: batida esquecida (marcação ímpar)"
FALTA = "Ponto do dia: falta sem justificativa"
HORISTA = "Horista além de 4h sem intervalo (limite do mês)"
EVENTOS_DO_DIA = {BATIDA_ESQUECIDA: "marcacao_impar", FALTA: "falta"}

DIAS_SEMANA = (
	"segunda-feira",
	"terça-feira",
	"quarta-feira",
	"quinta-feira",
	"sexta-feira",
	"sábado",
	"domingo",
)

TEXTOS = {
	(BATIDA_ESQUECIDA, "Colaborador"): (
		"Olá, {primeiro_nome}! No dia {data} ({dia_semana}) o seu ponto ficou com uma batida faltando "
		"(registrado: {batidas}). Se esqueceu de bater, avise o seu gestor para o RH corrigir."
	),
	(BATIDA_ESQUECIDA, "Gestor"): (
		"Olá, {primeiro_nome}! {colaborador} ficou com uma batida faltando no dia {data} ({dia_semana}); "
		"registrado: {batidas}. Confira e corrija no cartão ponto."
	),
	(FALTA, "Colaborador"): (
		"Olá, {primeiro_nome}! Não encontramos batidas no dia {data} ({dia_semana}). Se você trabalhou ou tem "
		"justificativa (atestado, declaração), fale com o seu gestor."
	),
	(FALTA, "Gestor"): (
		"Olá, {primeiro_nome}! {colaborador} não tem batidas no dia {data} ({dia_semana}). Confira no cartão ponto."
	),
}


PARTICULAS = {"de", "da", "do", "das", "dos", "e"}


def nome_proprio(nome: str | None) -> str:
	"""Nome como se escreve ("LEANDRO DA SILVA" → "Leandro da Silva"): o Secullum guarda tudo em maiúsculas."""
	palavras = str(nome or "").strip().split()
	return " ".join(
		p.lower() if n and p.lower() in PARTICULAS else p[:1].upper() + p[1:].lower()
		for n, p in enumerate(palavras)
	)


def texto_padrao(evento: str, destinatario: str) -> str:
	return TEXTOS.get((evento, destinatario), "")


def alcanca(empresa: str | None, cargo: str | None, empresas: Iterable[str], cargos: Iterable[str]) -> bool:
	"""Filtro da regra: lista vazia = todos."""
	empresas, cargos = set(empresas), set(cargos)
	return (not empresas or empresa in empresas) and (not cargos or cargo in cargos)


def data_curta(dia: date) -> str:
	return f"{dia:%d/%m}"


def dia_da_semana(dia: date) -> str:
	return DIAS_SEMANA[dia.weekday()]


def chave(regra: str, employee: str, dia: date | str, destinatario: str) -> str:
	"""Identifica um aviso: a mesma regra não manda duas vezes o mesmo dia para a mesma pessoa."""
	return f"{regra}|{employee}|{dia}|{destinatario}"[:140]


def primeiro_nome(nome: str | None) -> str:
	partes = str(nome or "").split()
	return nome_proprio(partes[0]) if partes else ""
