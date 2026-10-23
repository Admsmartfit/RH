"""Cartão ponto do Secullum (rota GET Batidas): o que o RH lançou no dia, além das batidas (docs/secullum_api.md).

Cada registro é um funcionário num dia, com `Folga`, `Neutro` e as colunas Entrada1..Saida5. Uma coluna com texto no
lugar da hora (ex.: "ATESTAD", "DECLARA", "FERIAS") é a justificativa (nome abreviado) do grupo n (Entrada n /
Saida n). Conferido no banco real em 20/10/2026. Python puro.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from hrms_secullum_brasil.integrations.secullum.importacao import data_secullum

HORA = re.compile(r"^\d{1,2}:\d{2}$")
GRUPOS = range(1, 6)


@dataclass(frozen=True)
class DiaCartao:
	funcionario_id: str
	data: date
	folga: bool = False
	neutro: bool = False
	justificativas: dict[int, str] = field(default_factory=dict)  # grupo → nome abreviado da justificativa
	grupos_com_batida: frozenset[int] = frozenset()

	@property
	def chave(self) -> str:
		return f"{self.funcionario_id}|{self.data.isoformat()}"

	@property
	def relevante(self) -> bool:
		"""Só vale guardar o dia que muda a apuração (folga, neutro ou justificativa)."""
		return self.folga or self.neutro or bool(self.justificativas)

	def assinatura(self) -> str:
		grupos = ",".join(f"{g}:{j}" for g, j in sorted(self.justificativas.items()))
		return f"{int(self.folga)}|{int(self.neutro)}|{grupos}|{','.join(map(str, sorted(self.grupos_com_batida)))}"


def dia_do_cartao(registro: dict) -> DiaCartao | None:
	"""Converte um registro de GET Batidas. None se faltar o funcionário ou a data."""
	funcionario = registro.get("FuncionarioId")
	dia = data_secullum(registro.get("Data"))
	if funcionario in (None, "") or dia is None:
		return None
	justificativas, com_batida = {}, set()
	for grupo in GRUPOS:
		valores = [str(registro.get(f"{tipo}{grupo}") or "").strip() for tipo in ("Entrada", "Saida")]
		textos = [v for v in valores if v and not HORA.match(v)]
		if textos:
			justificativas[grupo] = textos[0].upper()
		elif any(valores):
			com_batida.add(grupo)
	return DiaCartao(
		funcionario_id=str(funcionario),
		data=dia,
		folga=bool(registro.get("Folga")),
		neutro=bool(registro.get("Neutro")),
		justificativas=justificativas,
		grupos_com_batida=frozenset(com_batida),
	)
