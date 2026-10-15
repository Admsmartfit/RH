"""Marcações originais do Secullum (rota FonteDados): parsing, hash e plano de sincronização. Python puro.

Formato conforme o manual da Integração Externa (págs. 37-38 e 56-59):
Id, FuncionarioId, FuncionarioPis, FuncionarioCpf, EquipamentoId, Data, DataInclusao, Hora, Tipo, Origem.
"""

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time

from hrms_secullum_brasil.engine.documentos import somente_digitos

TIPOS_FONTE = {0: "Original", 1: "Manual", 2: "PreAssinalado", 3: "Desconsiderado"}
ORIGENS = {
	0: "Desconhecido",
	1: "RelogioPonto",
	2: "IncluidoManualmente",
	3: "PreAssinalado",
	4: "Checkin",
	5: "CentralFuncionarioWeb",
	6: "CentralFuncionarioApp",
	7: "CentralFuncionarioAppOffline",
	8: "IntegracaoExterna",
}
CAMPOS_FONTE_DADOS = (
	"Id",
	"FuncionarioId",
	"FuncionarioPis",
	"FuncionarioCpf",
	"EquipamentoId",
	"Data",
	"DataInclusao",
	"Hora",
	"Tipo",
	"Origem",
)
DESCONSIDERADO = "Desconsiderado"


@dataclass(frozen=True)
class BatidaSecullum:
	origem_id: str
	cpf: str
	pis: str
	funcionario_id: str | None
	equipamento: str | None
	data_hora: datetime
	tipo: str
	origem: str
	data_inclusao: datetime | None
	hash: str
	payload: dict = field(compare=False)

	@property
	def data(self) -> date:
		return self.data_hora.date()

	@property
	def desconsiderada(self) -> bool:
		return self.tipo == DESCONSIDERADO


def _data(valor) -> date:
	return date.fromisoformat(str(valor)[:10])


def _hora(valor) -> time:
	"""Aceita "08:00", "08:00:59" e "08-00" (o manual admite ":" ou "-"). Segundos são truncados (PRD, 5.13)."""
	partes = str(valor).replace("-", ":").split(":")
	return time(int(partes[0]), int(partes[1]))


def _data_hora_opcional(valor) -> datetime | None:
	if not valor:
		return None
	try:
		return datetime.fromisoformat(str(valor)[:19])
	except ValueError:
		return None


def _rotulo(mapa: dict[int, str], valor) -> str:
	try:
		return mapa[int(valor)]
	except (TypeError, ValueError, KeyError):
		return str(valor) if valor not in (None, "") else mapa[0]


def _texto(valor) -> str | None:
	return None if valor in (None, "") else str(valor)


def hash_registro(payload: dict) -> str:
	return hashlib.sha256(
		json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
	).hexdigest()


def parse_fonte_dados(registro: dict) -> BatidaSecullum:
	"""Converte um registro de FonteDados. Levanta ValueError se faltar Id, Data ou Hora."""
	payload = {campo: registro.get(campo) for campo in CAMPOS_FONTE_DADOS}
	if payload["Id"] in (None, "") or not payload["Data"] or not payload["Hora"]:
		raise ValueError(f"Registro de FonteDados incompleto: {payload}")
	try:
		data_hora = datetime.combine(_data(payload["Data"]), _hora(payload["Hora"]))
	except (TypeError, ValueError, IndexError) as exc:
		raise ValueError(f"Data/Hora inválida no registro {payload['Id']}: {exc}") from exc
	return BatidaSecullum(
		origem_id=str(payload["Id"]),
		cpf=somente_digitos(_texto(payload["FuncionarioCpf"])),
		pis=somente_digitos(_texto(payload["FuncionarioPis"])),
		funcionario_id=_texto(payload["FuncionarioId"]),
		equipamento=_texto(payload["EquipamentoId"]),
		data_hora=data_hora,
		tipo=_rotulo(TIPOS_FONTE, payload["Tipo"]),
		origem=_rotulo(ORIGENS, payload["Origem"]),
		data_inclusao=_data_hora_opcional(payload["DataInclusao"]),
		hash=hash_registro(payload),
		payload=payload,
	)


# ------------------------------------------------------------------ plano de sincronização


@dataclass(frozen=True)
class RawExistente:
	nome: str
	origem_id: str
	hash: str


@dataclass
class Plano:
	inserir: list[tuple[BatidaSecullum, str | None]] = field(
		default_factory=list
	)  # (batida, raw substituída)
	remover: list[str] = field(default_factory=list)  # raws que sumiram do Secullum
	inalteradas: int = 0


def planejar_sincronizacao(remotas: Iterable[BatidaSecullum], existentes: Iterable[RawExistente]) -> Plano:
	"""Compara as batidas do Secullum com as raws ativas da mesma janela.

	- mesmo Id e mesmo hash: nada a fazer (idempotência);
	- mesmo Id e hash diferente: a raw antiga é substituída pela nova versão;
	- raw ativa cujo Id não veio do Secullum: foi excluída lá e é marcada como substituída.
	"""
	plano = Plano()
	por_origem: dict[str, list[RawExistente]] = defaultdict(list)
	for raw in existentes:
		por_origem[raw.origem_id].append(raw)

	vistos: set[str] = set()
	processadas: set[tuple[str, str]] = set()
	for batida in remotas:
		if (batida.origem_id, batida.hash) in processadas:
			continue
		processadas.add((batida.origem_id, batida.hash))
		vistos.add(batida.origem_id)
		atuais = por_origem.get(batida.origem_id, [])
		if any(raw.hash == batida.hash for raw in atuais):
			plano.inalteradas += 1
			plano.remover += [raw.nome for raw in atuais if raw.hash != batida.hash]
			continue
		plano.inserir.append((batida, atuais[0].nome if atuais else None))
		plano.remover += [raw.nome for raw in atuais[1:]]

	plano.remover += [
		raw.nome for origem, lista in por_origem.items() if origem not in vistos for raw in lista
	]
	return plano


# ------------------------------------------------------------------ vínculo da batida


@dataclass(frozen=True)
class Vinculo:
	nome: str
	admissao: date | None
	demissao: date | None

	def ativo_em(self, data: date) -> bool:
		return (self.admissao is None or self.admissao <= data) and (
			self.demissao is None or data <= self.demissao
		)


def escolher_vinculo(vinculos: list[Vinculo], data: date) -> str | None:
	"""Vínculo (Employee) dono da batida: o único candidato, ou o único ativo na data."""
	if len(vinculos) == 1:
		return vinculos[0].nome
	ativos = [v for v in vinculos if v.ativo_em(data)]
	return ativos[0].nome if len(ativos) == 1 else None
