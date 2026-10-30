"""Restrições do planejador (PE-06, DP-10). As duras rejeitam a proposta; as suaves só pesam. O otimizador e a
heurística respeitam as duras na construção; esta função é a conferência (e o `escala_validacao` do cockpit é o juiz
final no Frappe, DP-5)."""

from collections.abc import Iterable
from dataclasses import dataclass

from hrms_secullum_brasil.engine.planejador.modelos import (
	Escala,
	Horizonte,
	Pessoa,
	Premissas,
	Regras,
	Turno,
	diaria_permitida,
	faixa_texto,
)

DIARIA = "diaria"
SEMANAL = "semanal"
MINIMO = "minimo_semanal"
FOLGAS = "folgas"
SETIMO_DIA = "setimo_dia"
INTERJORNADA = "interjornada"
INDISPONIVEL = "indisponivel"
DOMINGOS = "domingos"
SUPERVISAO = "supervisao_estagiario"
COTA = "cota_estagiario"
DURAS = frozenset({DIARIA, SEMANAL, FOLGAS, SETIMO_DIA, INTERJORNADA, INDISPONIVEL, DOMINGOS, SUPERVISAO})


@dataclass(frozen=True)
class Violacao:
	tipo: str
	pessoa: str | None
	dia: int | None
	mensagem: str

	@property
	def dura(self) -> bool:
		return self.tipo in DURAS


def _semana(escala_pessoa, horizonte: Horizonte, semana: int) -> list[Turno]:
	return [t for i in horizonte.dias_da_semana(semana) if (t := escala_pessoa[i])]


def violacoes(
	escala: Escala,
	pessoas: Iterable[Pessoa],
	horizonte: Horizonte,
	regras: Regras,
	premissas: Premissas,
	ampliar: bool = True,
) -> list[Violacao]:
	pessoas = {p.id: p for p in pessoas}
	saida: list[Violacao] = []
	datas = horizonte.datas
	for pid, turnos in escala.items():
		p = pessoas[pid]
		limite_dia = diaria_permitida(p, regras, premissas, ampliar)
		teto = min(regras.teto_semanal, p.semanal_max)
		for i, t in enumerate(turnos):
			if t is None:
				continue
			if t.minutos > limite_dia:
				saida.append(
					Violacao(
						DIARIA,
						pid,
						i,
						f"{p.nome}: turno de {t.minutos // 60}h{t.minutos % 60:02d} acima do permitido ({limite_dia // 60}h{limite_dia % 60:02d}).",
					)
				)
			for ind in p.indisponivel:
				if ind.dia == i and t.inicio < ind.fim and ind.inicio < t.fim:
					saida.append(
						Violacao(INDISPONIVEL, pid, i, f"{p.nome} está indisponível em {datas[i]:%d/%m}.")
					)
			if i + 1 < len(turnos) and turnos[i + 1] is not None:
				descanso = turnos[i + 1].inicio + 1440 - t.fim
				if descanso < regras.interjornada:
					saida.append(
						Violacao(
							INTERJORNADA,
							pid,
							i + 1,
							f"{p.nome}: {descanso // 60}h{descanso % 60:02d} de descanso entre {datas[i]:%d/%m} e {datas[i + 1]:%d/%m} (mínimo {regras.interjornada // 60}h).",
						)
					)
		for semana in range(horizonte.n_semanas):
			trabalhados = _semana(turnos, horizonte, semana)
			minutos = sum(t.minutos for t in trabalhados)
			inicio = datas[7 * semana]
			if minutos > teto:
				saida.append(
					Violacao(
						SEMANAL,
						pid,
						7 * semana,
						f"{p.nome}: {minutos // 60}h{minutos % 60:02d} na semana de {inicio:%d/%m}, acima do teto de {teto // 60}h{teto % 60:02d}.",
					)
				)
			if p.semanal_min and minutos < p.semanal_min and not p.vaga:
				saida.append(
					Violacao(
						MINIMO,
						pid,
						7 * semana,
						f"{p.nome}: {minutos // 60}h na semana de {inicio:%d/%m}, abaixo do mínimo de {p.semanal_min // 60}h (complemento pago).",
					)
				)
			if len(trabalhados) > 7 - regras.folgas_semana:
				saida.append(
					Violacao(
						FOLGAS,
						pid,
						7 * semana,
						f"{p.nome}: {7 - len(trabalhados)} folga(s) na semana de {inicio:%d/%m}; o regime exige {regras.folgas_semana}.",
					)
				)
		seguidos = 0
		for i, t in enumerate(turnos):
			seguidos = seguidos + 1 if t else 0
			if seguidos == 7:
				saida.append(
					Violacao(SETIMO_DIA, pid, i, f"{p.nome}: 7º dia seguido de trabalho em {datas[i]:%d/%m}.")
				)
		domingos = p.domingos_seguidos_antes
		for i in horizonte.domingos():
			domingos = domingos + 1 if turnos[i] else 0
			if domingos > p.limite_domingos:
				saida.append(
					Violacao(
						DOMINGOS,
						pid,
						i,
						f"{p.nome}: {domingos}º domingo seguido de trabalho em {datas[i]:%d/%m} (limite {p.limite_domingos}).",
					)
				)
	saida += _estagiarios(escala, pessoas, horizonte, premissas)
	return saida


def _estagiarios(escala: Escala, pessoas: dict, horizonte: Horizonte, premissas: Premissas) -> list[Violacao]:
	"""DP-10: estagiário nunca sem profissional com CREF na faixa; no máximo a cota por faixa."""
	saida = []
	for i, data in enumerate(horizonte.datas):
		presentes: dict[int, list[Pessoa]] = {}
		for pid, turnos in escala.items():
			if turnos[i]:
				for faixa in turnos[i].faixas():
					presentes.setdefault(faixa, []).append(pessoas[pid])
		for faixa, quem in sorted(presentes.items()):
			estagiarios = [p for p in quem if p.estagiario]
			if not estagiarios:
				continue
			if not any(p.cref and not p.estagiario for p in quem):
				saida.append(
					Violacao(
						SUPERVISAO,
						estagiarios[0].id,
						i,
						f"{data:%d/%m} {faixa_texto(faixa)}: estagiário sem profissional com CREF na unidade.",
					)
				)
			if len(estagiarios) * 100 > premissas.cota_estagiario_pct * len(quem):
				saida.append(
					Violacao(
						COTA,
						estagiarios[0].id,
						i,
						f"{data:%d/%m} {faixa_texto(faixa)}: {len(estagiarios)} de {len(quem)} são estagiários (cota {premissas.cota_estagiario_pct}%).",
					)
				)
	return saida


def tem_dura(violacoes_: Iterable[Violacao]) -> bool:
	return any(v.dura for v in violacoes_)
