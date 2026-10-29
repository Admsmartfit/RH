"""Turno padrão do cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-02 e DE-1). Python puro.

Um turno é entrada, saída e uma pausa opcional (minutos e, se informado, o horário em que começa; vazio = no meio do
turno). As horas trabalhadas não incluem a pausa: T1 08:00-14:15 com 15 min de pausa = 6h de trabalho. Saída menor
que a entrada = termina no dia seguinte.
"""

from dataclasses import dataclass

from hrms_secullum_brasil.engine.jornada_prevista import Periodo


@dataclass(frozen=True)
class TurnoPadrao:
	nome: str
	entrada: int  # minutos do dia
	saida: int
	pausa: int = 0
	pausa_inicio: int | None = None


def periodos_do_turno(turno: TurnoPadrao) -> tuple[tuple[Periodo, ...], list[str]]:
	"""Períodos do turno na linha do tempo do dia e os erros de cadastro."""
	if turno.saida == turno.entrada:
		return (), [f"{turno.nome}: a saída precisa ser diferente da entrada."]
	fim = turno.saida if turno.saida > turno.entrada else turno.saida + 1440
	duracao = fim - turno.entrada
	if turno.pausa < 0:
		return (), [f"{turno.nome}: a pausa não pode ser negativa."]
	if not turno.pausa:
		return (Periodo(turno.entrada, fim),), []
	if turno.pausa_inicio is None:
		inicio_pausa = turno.entrada + (duracao - turno.pausa) // 2
	else:
		inicio_pausa = (
			turno.pausa_inicio if turno.pausa_inicio >= turno.entrada else turno.pausa_inicio + 1440
		)
	fim_pausa = inicio_pausa + turno.pausa
	if not (turno.entrada < inicio_pausa and fim_pausa < fim):
		return (), [f"{turno.nome}: a pausa precisa ficar dentro do turno, com trabalho antes e depois."]
	return (Periodo(turno.entrada, inicio_pausa), Periodo(fim_pausa, fim)), []
