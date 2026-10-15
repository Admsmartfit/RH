"""MockSecullumClient: implementação em memória a partir de fixtures JSON (PRD, 6.1, "modo mock")."""

import json
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

from hrms_secullum_brasil.engine.documentos import somente_digitos
from hrms_secullum_brasil.integrations.secullum.client import (
	ChamadaRegistrada,
	SecullumClient,
	filtrar_bancos,
)
from hrms_secullum_brasil.integrations.secullum.erros import SecullumValidacaoError
from hrms_secullum_brasil.integrations.secullum.mapeamento import CAMPOS_OBRIGATORIOS

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _carregar(pasta: Path, nome: str):
	return json.loads((pasta / f"{nome}.json").read_text(encoding="utf-8"))


def _fonte_dados_relativa(registros: list[dict], hoje: date) -> list[dict]:
	"""A fixture usa "DiasAtras" no lugar de "Data" para sempre cair na janela de coleta."""
	resultado = []
	for r in registros:
		r = dict(r)
		if "DiasAtras" in r:
			r["Data"] = (hoje - timedelta(days=int(r.pop("DiasAtras")))).isoformat() + "T00:00:00"
		resultado.append(r)
	return resultado


class MockSecullumClient(SecullumClient):
	"""Simula o Secullum: POST de funcionário faz upsert pelo CPF e valida os campos obrigatórios.

	`falhas` é uma fila de exceções: cada chamada consome a primeira e a levanta (para testes).
	"""

	def __init__(
		self, fixtures_dir: Path = FIXTURES_DIR, registrar: Callable[[ChamadaRegistrada], None] | None = None
	):
		self.bancos: list[dict] = _carregar(fixtures_dir, "bancos")
		self.funcionarios: dict[str, dict] = {
			somente_digitos(f["Cpf"]): f for f in _carregar(fixtures_dir, "funcionarios")
		}
		self.departamentos: set[str] = set()
		self.funcoes: set[str] = set()
		self.fonte_dados: list[dict] = _fonte_dados_relativa(
			_carregar(fixtures_dir, "fonte_dados"), date.today()
		)
		self.totais: dict[str, dict[str, str]] = {}  # CPF -> {coluna: "HH:MM"}
		self.chamadas: list[tuple[str, object]] = []
		self.falhas: list[Exception] = []
		self._registrar = registrar or (lambda chamada: None)
		self._proximo_id = max((int(f.get("Id", 0)) for f in self.funcionarios.values()), default=0) + 1

	def _chamada(self, metodo: str, rota: str, argumento=None):
		self.chamadas.append((rota, argumento))
		erro = self.falhas.pop(0) if self.falhas else None
		self._registrar(
			ChamadaRegistrada(
				servico="mock",
				metodo=metodo,
				rota=rota,
				status_http=None if erro else 200,
				tentativas=1,
				duracao_ms=0,
				erro=str(erro) if erro else None,
				payload=argumento if isinstance(argumento, dict) else None,
			)
		)
		if erro:
			raise erro

	def listar_bancos(self) -> list[dict]:
		self._chamada("GET", "ListarBancos")
		return filtrar_bancos(self.bancos, "3")

	def listar_funcionarios(self) -> list[dict]:
		self._chamada("GET", "Funcionarios")
		return [dict(f) for f in self.funcionarios.values()]

	def buscar_funcionario_por_cpf(self, cpf: str) -> dict | None:
		self._chamada("GET", "Funcionarios/Cpf", cpf)
		encontrado = self.funcionarios.get(somente_digitos(cpf))
		return dict(encontrado) if encontrado else None

	def salvar_funcionario(self, dados: dict) -> None:
		self._chamada("POST", "Funcionarios", dados)
		faltando = [c for c in CAMPOS_OBRIGATORIOS if not dados.get(c)]
		if faltando:
			raise SecullumValidacaoError(
				[{"Property": c, "Message": f"O campo {c} é obrigatório."} for c in faltando]
			)
		cpf = somente_digitos(dados["Cpf"])
		existente = self.funcionarios.get(cpf)
		identificador = existente["Id"] if existente else self._novo_id()
		self.funcionarios[cpf] = {**dados, "Id": identificador}

	def salvar_departamento(self, descricao: str) -> None:
		self._chamada("POST", "Departamentos", {"Descricao": descricao})
		self.departamentos.add(descricao)

	def salvar_funcao(self, descricao: str) -> None:
		self._chamada("POST", "Funcoes", {"Descricao": descricao})
		self.funcoes.add(descricao)

	def _novo_id(self) -> int:
		self._proximo_id += 1
		return self._proximo_id - 1

	def listar_fonte_dados(self, data_inicio: date, data_fim: date) -> list[dict]:
		self._chamada(
			"GET", "FonteDados", {"dataInicio": data_inicio.isoformat(), "dataFim": data_fim.isoformat()}
		)
		return [
			dict(r)
			for r in self.fonte_dados
			if data_inicio <= date.fromisoformat(str(r["Data"])[:10]) <= data_fim
		]

	def calcular_totais(self, cpf: str, data_inicio: date, data_fim: date) -> dict:
		self._chamada("POST", "Calcular/SomenteTotais", {"FuncionarioCpf": cpf})
		totais = self.totais.get(somente_digitos(cpf), {})
		return {"Colunas": list(totais), "Totais": list(totais.values())}
