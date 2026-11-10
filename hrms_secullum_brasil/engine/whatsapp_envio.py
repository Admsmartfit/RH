"""Envio de WhatsApp: modo de teste, ritmo e aceite (docs/PRD-whatsapp-aceite-auditoria.md). Python puro.

- Modo de teste (CW-08 a CW-10): a mensagem vai só ao número de teste, com o cabeçalho "[TESTE] para: ...", e os
  links do texto ganham o marcador `teste` (a página abre sem gravar nada).
- Ritmo (CW-11 a CW-13): intervalo sorteado entre as mensagens, horário de envio e limite por dia com aquecimento do
  chip novo.
- Aceite (CW-05): em Ligado, só o colaborador que aceitou recebe (os gestores não precisam, decisão do RH).
"""

import re
from collections.abc import Callable
from datetime import date, datetime, time, timedelta

DESLIGADO = "Desligado"
TESTE = "Teste"
LIGADO = "Ligado"
MODOS = (DESLIGADO, TESTE, LIGADO)

ENVIADA_TESTE = "Enviada (teste)"
ENVIADAS_NO_DIA = ("Enviada", "Entregue", "Lida", ENVIADA_TESTE)
MOTIVO_SEM_ACEITE = "sem aceite do WhatsApp"

# padrões (o `default` dos campos da Configuracao Apuracao repete estes valores; há teste)
INTERVALO_MIN_S = 20
INTERVALO_MAX_S = 90
LIMITE_DIA = 150
AQUECIMENTO_DIAS = 7
AQUECIMENTO_INICIAL = 30
HORA_INICIO = 8
HORA_FIM = 20

# link das páginas sem login: /ponto/<página>?t=<token> ou ?token=<token>
_LINK = re.compile(r"https?://[^\s?]+/ponto/[^\s?]+\?(?:[^\s]*?&)?(?:t|token)=([A-Za-z0-9_\-.]+)")


def final_do_numero(numero: str | None) -> str:
	digitos = re.sub(r"\D", "", str(numero or ""))
	return digitos[-4:] if digitos else "----"


def cabecalho_teste(nome: str | None, papel: str | None, numero: str | None) -> str:
	"""CW-09: "[TESTE] para: Ana Souza — Colaborador (final 1234)"; do número real, só os 4 últimos dígitos."""
	return f"[TESTE] para: {nome or '-'} — {papel or '-'} (final {final_do_numero(numero)})"


def texto_de_teste(texto: str, cabecalho: str) -> str:
	return f"{cabecalho}\n\n{texto or ''}"


def marcar_links_de_teste(texto: str, assinar: Callable[[str], str]) -> str:
	"""CW-10: cada link de página sem login ganha `&teste=<assinatura do token>`."""

	def trocar(m: re.Match) -> str:
		url, token = m.group(0), m.group(1)
		sobra = ""
		while token.endswith("."):  # ponto final da frase não faz parte do token
			token, url, sobra = token[:-1], url[:-1], "." + sobra
		return f"{url}&teste={assinar(token)}{sobra}" if token else m.group(0)

	return _LINK.sub(trocar, texto or "")


def precisa_de_aceite(modo: str | None, destinatario: str | None, exigir: bool = True) -> bool:
	"""CW-05: em Ligado, a mensagem ao colaborador exige o aceite; gestor, RH e teste não."""
	return bool(exigir) and modo == LIGADO and destinatario == "Colaborador"


def dentro_do_horario(momento: datetime, inicio: int = HORA_INICIO, fim: int = HORA_FIM) -> bool:
	return inicio <= momento.hour < fim


def _ajustar_ao_horario(momento: datetime, inicio: int, fim: int) -> datetime:
	if momento.hour < inicio:
		return datetime.combine(momento.date(), time(inicio))
	if momento.hour >= fim:
		return datetime.combine(momento.date() + timedelta(days=1), time(inicio))
	return momento


def proximo_horario(
	ultimo: datetime | None,
	agora: datetime,
	minimo: int,
	maximo: int,
	sorteio: float,
	inicio: int = HORA_INICIO,
	fim: int = HORA_FIM,
) -> datetime:
	"""CW-11: a mensagem sai depois da última da fila (ou de agora) mais um intervalo sorteado (`sorteio` de 0 a 1,
	vindo de fora para o teste ser fixo). Fora das 8h-20h, vai para o início do próximo horário útil."""
	minimo, maximo = max(0, int(minimo or 0)), max(0, int(maximo or 0))
	if maximo < minimo:
		minimo, maximo = maximo, minimo
	base = max(agora, ultimo) if ultimo else agora
	passo = minimo + round((maximo - minimo) * min(max(sorteio, 0.0), 1.0))
	return _ajustar_ao_horario(base + timedelta(seconds=passo), inicio, fim)


def limite_do_dia(
	hoje: date,
	inicio_chip: date | None,
	limite: int = LIMITE_DIA,
	dias: int = AQUECIMENTO_DIAS,
	inicial: int = AQUECIMENTO_INICIAL,
) -> int:
	"""CW-12/CW-13: limite por dia; nos `dias` primeiros a partir do chip novo, começa em `inicial` e sobe por igual."""
	limite = max(0, int(limite or 0))
	if not inicio_chip:
		return limite
	decorridos = (hoje - inicio_chip).days
	if decorridos >= dias:
		return limite
	if decorridos <= 0:
		return min(inicial, limite)
	return min(limite, inicial + (limite - inicial) * decorridos // dias)
