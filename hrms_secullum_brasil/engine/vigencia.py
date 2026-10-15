"""Regras com vigência (PRD, Seção 3.6).

Toda regra (CCT, Perfil de Jornada, Benefício, Premiação) vale num intervalo de datas fechado
[inicio, fim]; fim = None significa vigência em aberto. O motor sempre usa a regra vigente na data.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Vigencia:
	inicio: date
	fim: date | None = None

	def __post_init__(self):
		if self.fim is not None and self.fim < self.inicio:
			raise ValueError(f"Fim da vigência ({self.fim}) anterior ao início ({self.inicio})")

	def contem(self, data: date) -> bool:
		return self.inicio <= data and (self.fim is None or data <= self.fim)

	def sobrepoe(self, outra: "Vigencia") -> bool:
		return (self.fim is None or outra.inicio <= self.fim) and (
			outra.fim is None or self.inicio <= outra.fim
		)


@dataclass(frozen=True)
class RegraComVigencia:
	"""Uma versão de regra dentro de um escopo (ex.: empresa + sindicato).

	`cargos` vazio significa que a regra vale para todos os cargos do escopo.
	"""

	nome: str
	vigencia: Vigencia
	cargos: frozenset[str] = field(default_factory=frozenset)

	def aplica_ao_cargo(self, cargo: str | None) -> bool:
		return not self.cargos or cargo in self.cargos

	def compartilha_cargos(self, outra: "RegraComVigencia") -> bool:
		return not self.cargos or not outra.cargos or bool(self.cargos & outra.cargos)


def conflitos_de_vigencia(nova: RegraComVigencia, existentes: Iterable[RegraComVigencia]) -> list[str]:
	"""Nomes das regras do mesmo escopo que conflitam com `nova` (vigência e cargos em comum)."""
	return sorted(
		r.nome
		for r in existentes
		if r.nome != nova.nome and r.vigencia.sobrepoe(nova.vigencia) and r.compartilha_cargos(nova)
	)


def selecionar_vigentes(
	regras: Iterable[RegraComVigencia], data: date, cargo: str | None = None
) -> list[RegraComVigencia]:
	"""Regras vigentes na data que se aplicam ao cargo, ordenadas por nome."""
	return sorted(
		(r for r in regras if r.vigencia.contem(data) and r.aplica_ao_cargo(cargo)),
		key=lambda r: r.nome,
	)
