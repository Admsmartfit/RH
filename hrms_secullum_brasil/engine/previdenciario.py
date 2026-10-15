"""Regra dos 15 dias para encaminhamento ao INSS (Lei 8.213/91, Art. 60; Decreto 3.048/99, Art. 75) — PRD 7.2.

- Mesma doença = mesmo grupo de CID (3 primeiros caracteres) ou correlação manual feita pelo RH; atestado
  sem CID só soma com outro por correlação manual.
- Cadeia: um afastamento da mesma doença soma com o anterior se começar até 60 dias depois do fim
  (retorno) do anterior. Dias sobrepostos contam uma vez.
- Passou de 15 dias na cadeia: a empresa paga até o 15º; o 16º dia é a data de encaminhamento ao INSS.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

JANELA_RETORNO_DIAS = 60
LIMITE_DIAS_EMPRESA = 15


def grupo_cid(cid: str | None) -> str | None:
	codigo = (cid or "").strip().upper().replace(".", "")
	return codigo[:3] if len(codigo) >= 3 else None


@dataclass(frozen=True)
class Afastamento:
	id: str
	inicio: date
	fim: date
	grupo: str | None = None  # grupo do CID

	def __post_init__(self):
		if self.fim < self.inicio:
			raise ValueError(f"Afastamento {self.id}: fim anterior ao início.")

	def dias(self) -> list[date]:
		return [self.inicio + timedelta(days=i) for i in range((self.fim - self.inicio).days + 1)]


@dataclass(frozen=True)
class Avaliacao:
	soma_dias: int
	data_16_dia: date | None


@dataclass(frozen=True)
class AlertaPrevidenciario:
	atestados: tuple[str, ...]
	soma_dias: int
	data_16_dia: date
	grupo: str | None


def agrupar_por_doenca(
	afastamentos: Iterable[Afastamento], correlacoes: Iterable[tuple[str, str]] = ()
) -> list[list[Afastamento]]:
	"""Une afastamentos do mesmo grupo de CID ou correlacionados manualmente (union-find)."""
	lista = list(afastamentos)
	pai = {a.id: a.id for a in lista}

	def raiz(x):
		while pai[x] != x:
			pai[x] = pai[pai[x]]
			x = pai[x]
		return x

	def unir(a, b):
		if a in pai and b in pai:
			pai[raiz(a)] = raiz(b)

	por_grupo: dict[str, str] = {}
	for a in lista:
		if a.grupo:
			if a.grupo in por_grupo:
				unir(a.id, por_grupo[a.grupo])
			else:
				por_grupo[a.grupo] = a.id
	for a, b in correlacoes:
		unir(a, b)

	grupos: dict[str, list[Afastamento]] = defaultdict(list)
	for a in lista:
		grupos[raiz(a.id)].append(a)
	return [sorted(g, key=lambda a: (a.inicio, a.id)) for g in grupos.values()]


def cadeias(
	mesma_doenca: Iterable[Afastamento], janela: int = JANELA_RETORNO_DIAS
) -> list[list[Afastamento]]:
	"""Divide os afastamentos de uma doença em cadeias pelo prazo de 60 dias após o retorno."""
	resultado: list[list[Afastamento]] = []
	fim_cadeia = None
	for a in sorted(mesma_doenca, key=lambda a: (a.inicio, a.id)):
		if fim_cadeia is not None and a.inicio <= fim_cadeia + timedelta(days=janela):
			resultado[-1].append(a)
			fim_cadeia = max(fim_cadeia, a.fim)
		else:
			resultado.append([a])
			fim_cadeia = a.fim
	return resultado


def avaliar(cadeia: Iterable[Afastamento], limite: int = LIMITE_DIAS_EMPRESA) -> Avaliacao:
	dias = sorted({dia for a in cadeia for dia in a.dias()})
	return Avaliacao(len(dias), dias[limite] if len(dias) > limite else None)


def verificar_alertas(
	afastamentos: Iterable[Afastamento],
	correlacoes: Iterable[tuple[str, str]] = (),
	janela: int = JANELA_RETORNO_DIAS,
	limite: int = LIMITE_DIAS_EMPRESA,
) -> list[AlertaPrevidenciario]:
	alertas = []
	for doenca in agrupar_por_doenca(afastamentos, correlacoes):
		for cadeia in cadeias(doenca, janela):
			avaliacao = avaliar(cadeia, limite)
			if avaliacao.data_16_dia:
				grupo = next((a.grupo for a in cadeia if a.grupo), None)
				alertas.append(
					AlertaPrevidenciario(
						tuple(a.id for a in cadeia), avaliacao.soma_dias, avaliacao.data_16_dia, grupo
					)
				)
	return sorted(alertas, key=lambda a: (a.data_16_dia, a.atestados))
