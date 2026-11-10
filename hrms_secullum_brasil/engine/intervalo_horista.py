"""Instrutor horista que passou de 4h15 sem marcar o intervalo (RH, 09/11/2026). Python puro.

O instrutor não recebe WhatsApp. O RH recebe, uma vez por dia, a lista dos dias novos com o link para lançar o
intervalo de 15 min no meio da jornada, que desconta das horas e não é pago. O termo do mês registra cada dia. A
pendência é o tipo `intervalo_nao_marcado_horista` (engine/apuracao_dia.py).
"""

from dataclasses import dataclass
from datetime import date

TIPO = "intervalo_nao_marcado_horista"
MOTIVO = "Intervalo não marcado — lançado pelo RH (instrutor horista, não remunerado)"
LIMITE_LINHAS = 30  # mensagem de WhatsApp curta: o resto fica no link da central


def intervalo_no_meio(entrada: int, saida: int, duracao: int) -> tuple[int, int] | None:
	"""O intervalo de `duracao` minutos no meio da jornada (minutos do dia; a saída pode passar de 24h)."""
	if duracao <= 0 or saida - entrada <= duracao:
		return None
	inicio = entrada + (saida - entrada - duracao) // 2
	return inicio, inicio + duracao


def minutos_em_ordem(horas: list[str]) -> list[int]:
	"""["21:30", "01:10"] → [1290, 1510]: a batida depois da meia-noite continua o dia de trabalho."""
	saida, anterior = [], None
	for h in horas:
		hh, mm = (int(x) for x in h.split(":"))
		m = hh * 60 + mm
		while anterior is not None and m < anterior:
			m += 24 * 60
		saida.append(m)
		anterior = m
	return saida


def hhmm(minutos: int) -> str:
	minutos %= 24 * 60
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


@dataclass(frozen=True)
class ItemRH:
	nome: str
	data: date
	trabalhado: int  # minutos do dia, sem intervalo
	link: str


def _duracao(minutos: int) -> str:
	return f"{minutos // 60}h{minutos % 60:02d}"


def mensagem_rh(dia: date, itens: list[ItemRH], anteriores: int, link_central: str) -> str:
	"""Uma mensagem por dia para o RH, com todos os dias novos; os de antes que ainda estão sem o intervalo vêm só
	contados, com o link da central."""
	linhas = [
		f"Instrutores horistas que passaram de 4h15 sem marcar o intervalo ({dia:%d/%m}):",
		"",
	]
	for item in itens[:LIMITE_LINHAS]:
		linhas.append(
			f"• {item.nome}: {_duracao(item.trabalhado)} em {item.data:%d/%m}. Lançar o intervalo: {item.link}"
		)
	if len(itens) > LIMITE_LINHAS:
		linhas.append(f"• e mais {len(itens) - LIMITE_LINHAS}: veja na central.")
	linhas += [
		"",
		"O intervalo de 15 min entra no meio da jornada e não é pago. O instrutor não recebe mensagem; o termo do mês "
		"registra o dia.",
	]
	if anteriores:
		linhas.append(f"Ainda sem o intervalo, de dias anteriores: {anteriores}. Central: {link_central}")
	return "\n".join(linhas)
