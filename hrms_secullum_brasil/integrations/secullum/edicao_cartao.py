"""Envio das correções do cartão ponto ao Secullum (docs/PRD-cartao-ponto.md, CP-10). Python puro.

As rotas `CartaoPonto/*` trabalham por coluna (Entrada1..Saida5) e fazem uma operação por requisição (manual da
Integração Externa, págs. 45 a 52; registrado em docs/secullum_api.md):
- POST CartaoPonto/Manual {Data, Coluna, Hora, Motivo}: inclui ou edita a batida manual da coluna (erro se a coluna tem
  batida original; uma justificativa na coluna é apagada com o seu par);
- DELETE CartaoPonto {Data, Coluna, Motivo}: tira o valor da coluna (a original fica desconsiderada; a justificativa
  apaga o grupo);
- POST CartaoPonto/Justificativa {Data, Grupo, Justificativa}: justificativa (nome abreviado) no grupo 1..5 (erro se o
  grupo tem batida original).

O programa sincroniza o dia inteiro: o cartão do Secullum daquele dia passa a ter as mesmas batidas do programa, na
ordem, a partir da Entrada1. Recalcular de novo com o cartão atualizado não gera operação (o reenvio é seguro).
"""

import re
from dataclasses import dataclass, field
from datetime import date

COLUNAS = tuple(f"{tipo}{n}" for n in range(1, 6) for tipo in ("Entrada", "Saida"))
HORA = re.compile(r"^\d{1,2}:\d{2}$")
MANUAL = ("POST", "CartaoPonto/Manual")
EXCLUIR = ("DELETE", "CartaoPonto")
JUSTIFICATIVA = ("POST", "CartaoPonto/Justificativa")
ROTAS = frozenset(r for _, r in (MANUAL, EXCLUIR, JUSTIFICATIVA))
LIMITE_MOTIVO = 150


@dataclass(frozen=True)
class Operacao:
	metodo: str
	rota: str
	corpo: dict = field(default_factory=dict)

	def descricao(self) -> str:
		c = self.corpo
		if self.rota == MANUAL[1]:
			return f"Incluir {c['Hora']} em {c['Coluna']}"
		if self.rota == JUSTIFICATIVA[1]:
			return f"Justificativa {c['Justificativa']} no grupo {c['Grupo']}"
		return f"Tirar {c['Coluna']}"


def colunas_do_registro(registro: dict | None) -> dict[str, str]:
	"""Registro do GET Batidas → {"Entrada1": "08:00", "Saida1": "ATESTAD", ...} (só as colunas preenchidas)."""
	registro = registro or {}
	saida = {}
	for coluna in COLUNAS:
		valor = str(registro.get(coluna) or "").strip()
		if valor:
			saida[coluna] = valor.upper() if not HORA.match(valor) else valor.zfill(5)
	return saida


def _hora(valor: str) -> bool:
	return bool(HORA.match(valor or ""))


def disposicao(atuais: dict[str, str], horarios: list[str]) -> dict[str, str]:
	"""Coluna de cada horário. Mantém as batidas que já estão no lugar (a original não vira manual à toa) e põe as
	novas nas colunas livres; se a ordem do dia não fechar assim, refaz a partir da Entrada1."""
	ordem = {h: i for i, h in enumerate(horarios)}
	mantidas = {c: v for c, v in atuais.items() if _hora(v) and v in ordem}
	novas = [h for h in horarios if h not in mantidas.values()]
	livres = [c for c in COLUNAS if c not in mantidas]
	tentativa = {**mantidas, **dict(zip(livres, novas, strict=False))}
	sequencia = [ordem[tentativa[c]] for c in COLUNAS if c in tentativa]
	ocupadas = [c for c in COLUNAS if c in tentativa]
	if sequencia == sorted(sequencia) and ocupadas == list(COLUNAS[: len(ocupadas)]):
		return tentativa
	return dict(zip(COLUNAS, horarios, strict=False))


def operacoes(
	data: date,
	atuais: dict[str, str],
	horarios: list[str],
	motivo: str,
	*,
	justificativa: str | None = None,
	grupos_abono: int = 1,
	justificativa_retirada: str | None = None,
) -> list[Operacao]:
	"""Operações para o cartão do Secullum no dia ficar com `horarios` (na ordem do dia de trabalho).

	`justificativa`: abono do dia sem batidas → a justificativa nos grupos 1..`grupos_abono`.
	`justificativa_retirada`: abono tirado no programa → apaga só os grupos com essa justificativa (as lançadas no
	próprio Secullum ficam).
	"""
	if len(horarios) > len(COLUNAS):
		raise ValueError(
			f"O Secullum aceita até {len(COLUNAS)} batidas no dia; o programa tem {len(horarios)}."
		)
	dia = data.isoformat()
	motivo = (motivo or "Correção do cartão ponto").strip()[:LIMITE_MOTIVO]
	desejadas = disposicao(atuais, horarios)
	ops: list[Operacao] = []
	grupos_com_justificativa = set()
	if justificativa and not horarios:
		for grupo in range(1, max(1, grupos_abono) + 1):
			if atuais.get(f"Entrada{grupo}") != justificativa:
				ops.append(
					Operacao(*JUSTIFICATIVA, {"Data": dia, "Grupo": grupo, "Justificativa": justificativa})
				)
			grupos_com_justificativa.add(grupo)
	for coluna in COLUNAS:
		grupo = int(coluna[-1])
		atual, desejada = atuais.get(coluna, ""), desejadas.get(coluna, "")
		if grupo in grupos_com_justificativa or atual == desejada:
			continue
		if not _hora(atual) and atual:  # justificativa no Secullum
			if desejada:
				ops.append(
					Operacao(*MANUAL, {"Data": dia, "Coluna": coluna, "Hora": desejada, "Motivo": motivo})
				)
			elif justificativa_retirada and atual == justificativa_retirada and coluna.startswith("Entrada"):
				ops.append(Operacao(*EXCLUIR, {"Data": dia, "Coluna": coluna, "Motivo": motivo}))
			continue
		if atual:
			ops.append(Operacao(*EXCLUIR, {"Data": dia, "Coluna": coluna, "Motivo": motivo}))
		if desejada:
			ops.append(Operacao(*MANUAL, {"Data": dia, "Coluna": coluna, "Hora": desejada, "Motivo": motivo}))
	return ops


def com_identificador(operacao: Operacao, cpf: str) -> dict:
	"""Corpo final da requisição: o colaborador vai pelo CPF (só dígitos)."""
	return {"Cpf": "".join(c for c in str(cpf or "") if c.isdigit()), **operacao.corpo}
