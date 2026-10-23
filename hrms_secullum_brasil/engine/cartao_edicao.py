"""Edição do cartão ponto (docs/PRD-cartao-ponto.md, CP-02 e DC-1): compara as batidas do dia com a grade editada
pelo RH e diz quais tratamentos criar. A batida original nunca muda: o que some vira "desconsiderar" (ou o
cancelamento da inclusão que o próprio programa fez) e o que aparece vira "incluir". Mudar um horário = as duas
coisas.

Horários em minutos a partir das 00:00 do dia de trabalho (passam de 1440 na madrugada seguinte, antes da hora de
virada do perfil), como em engine/models.py.
"""

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from hrms_secullum_brasil.engine.jornada_prevista import MINUTOS_DIA

# origem da batida mostrada no cartão
ORIGINAL = "original"  # Secullum Checkin Raw
INCLUIDA = "incluida"  # Tratamento de Ponto de inclusão

# ações
INCLUIR = "incluir"
DESCONSIDERAR = "desconsiderar"
CANCELAR_INCLUSAO = "cancelar_inclusao"
ABONAR = "abonar"
CANCELAR_ABONO = "cancelar_abono"

HORARIO = re.compile(r"^\s*(\d{1,2}):?(\d{2})\s*$")


@dataclass(frozen=True)
class Batida:
	minuto: int
	origem: str  # ORIGINAL ou INCLUIDA
	referencia: str  # nome da Secullum Checkin Raw ou do Tratamento de Ponto
	pendente: bool = False  # inclusão ainda não aprovada pelo RH


@dataclass(frozen=True)
class Acao:
	tipo: str
	minuto: int | None = None
	referencia: str | None = None


@dataclass(frozen=True)
class EdicaoDia:
	acoes: tuple[Acao, ...] = ()
	erros: tuple[str, ...] = ()
	avisos: tuple[str, ...] = ()

	@property
	def mudou(self) -> bool:
		return bool(self.acoes)


def ler_horario(texto: str, hora_virada: int = 0) -> int:
	""" "HH:MM" (ou "HHMM") → minutos do dia de trabalho. Antes da hora de virada (em horas) é a madrugada seguinte."""
	achado = HORARIO.match(str(texto or ""))
	if not achado:
		raise ValueError(texto)
	horas, minutos = int(achado.group(1)), int(achado.group(2))
	if horas > 23 or minutos > 59:
		raise ValueError(texto)
	total = horas * 60 + minutos
	return total + MINUTOS_DIA if total < hora_virada * 60 else total


def hhmm(minuto: int) -> str:
	minuto %= MINUTOS_DIA
	return f"{minuto // 60:02d}:{minuto % 60:02d}"


def comparar_dia(
	batidas: Sequence[Batida],
	horarios: Iterable[str],
	*,
	hora_virada: int = 0,
	abonar: bool | None = None,
	abono: str | None = None,
) -> EdicaoDia:
	"""Batidas do cartão versus horários editados (a ordem não importa) → ações.

	`abonar`: None = sem mudança; True = abonar o dia (se ainda não tem `abono`); False = tirar o abono do programa
	(`abono` = Tratamento de Ponto do abono).
	"""
	erros, editados = [], []
	for texto in horarios:
		if not str(texto or "").strip():
			continue
		try:
			editados.append(ler_horario(texto, hora_virada))
		except ValueError:
			erros.append(f"Horário inválido: {texto}. Use HH:MM.")
	repetidos = sorted(m for m, n in Counter(editados).items() if n > 1)
	erros += [f"Horário repetido: {hhmm(m)}." for m in repetidos]
	if erros:
		return EdicaoDia(erros=tuple(erros))

	restantes = Counter(editados)
	acoes = []
	for batida in sorted(batidas, key=lambda b: b.minuto):
		if restantes[batida.minuto]:
			restantes[batida.minuto] -= 1
		elif batida.origem == INCLUIDA:
			acoes.append(Acao(CANCELAR_INCLUSAO, batida.minuto, batida.referencia))
		else:
			acoes.append(Acao(DESCONSIDERAR, batida.minuto, batida.referencia))
	acoes += [Acao(INCLUIR, m) for m in sorted(restantes.elements())]
	if abonar is True and not abono:
		acoes.append(Acao(ABONAR))
	elif abonar is False and abono:
		acoes.append(Acao(CANCELAR_ABONO, referencia=abono))

	avisos = []
	if acoes and len(editados) % 2:
		avisos.append(f"O dia fica com marcação ímpar ({len(editados)} batidas).")
	return EdicaoDia(acoes=tuple(acoes), avisos=tuple(avisos))


ROTULOS = {
	INCLUIR: ("inclusão", "inclusões"),
	DESCONSIDERAR: ("desconsideração", "desconsiderações"),
	CANCELAR_INCLUSAO: ("inclusão desfeita", "inclusões desfeitas"),
	ABONAR: ("abono", "abonos"),
	CANCELAR_ABONO: ("abono retirado", "abonos retirados"),
}


def resumo(edicoes: dict) -> str:
	"""{dia: EdicaoDia} → "3 inclusões, 1 abono em 2 dias" (o texto do Salvar)."""
	contagem = Counter(a.tipo for e in edicoes.values() for a in e.acoes)
	dias = sum(1 for e in edicoes.values() if e.mudou)
	if not dias:
		return "Nenhuma alteração."
	partes = [f"{contagem[tipo]} {ROTULOS[tipo][contagem[tipo] > 1]}" for tipo in ROTULOS if contagem[tipo]]
	return f"{', '.join(partes)} em {dias} dia{'s' if dias > 1 else ''}"
