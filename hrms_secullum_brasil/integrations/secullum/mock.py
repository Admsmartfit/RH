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
# respostas reais anonimizadas (ingestion/amostras_secullum.py): cadastros no formato que o GET devolve
REAIS_DIR = FIXTURES_DIR / "reais"
CADASTROS = (
	"empresas",
	"funcoes",
	"departamentos",
	"horarios",
	"justificativas",
	"motivos_demissao",
	"equipamentos",
	"afastamentos",
)


def _carregar(pasta: Path, nome: str):
	arquivo = pasta / f"{nome}.json"
	if not arquivo.exists():  # o que a pasta não tem vem da pasta padrão (ex.: bancos.json)
		arquivo = FIXTURES_DIR / f"{nome}.json"
	return json.loads(arquivo.read_text(encoding="utf-8"))


def _chave_funcionario(f: dict) -> str:
	"""No formato real (GET) cada vínculo é um registro com Id próprio: a mesma pessoa (CPF) pode ter um vínculo
	demitido numa empresa e outro ativo noutra. No formato do POST (envio), a chave é o CPF."""
	if "EmpresaId" in f or not f.get("Cpf"):
		return f"id:{f.get('Id')}"
	return somente_digitos(f["Cpf"])


def _no_periodo(item: dict, inicio: date, fim: date) -> bool:
	de = date.fromisoformat(str(item.get("Inicio"))[:10])
	ate = date.fromisoformat(str(item.get("Fim") or item.get("Inicio"))[:10])
	return de <= fim and ate >= inicio


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
	Com `fixtures_dir=REAIS_DIR`, funcionários e cadastros vêm no formato real do GET (importação); os cadastros
	sempre vêm das amostras reais quando a pasta não os tem. `estruturas` começa vazia, como no banco real.
	"""

	def __init__(
		self, fixtures_dir: Path = FIXTURES_DIR, registrar: Callable[[ChamadaRegistrada], None] | None = None
	):
		self.bancos: list[dict] = _carregar(fixtures_dir, "bancos")
		self.funcionarios: dict[str, dict] = {
			_chave_funcionario(f): f for f in _carregar(fixtures_dir, "funcionarios")
		}
		pasta_cadastros = fixtures_dir if (fixtures_dir / "horarios.json").exists() else REAIS_DIR
		self.cadastros: dict[str, list[dict]] = {nome: _carregar(pasta_cadastros, nome) for nome in CADASTROS}
		self.estruturas: list[dict] = []
		self.cartao: list[dict] = []  # registros do GET Batidas (cartão do dia); vazio = nada lançado
		self.departamentos: set[str] = set()
		self.funcoes: set[str] = set()
		self.fonte_dados: list[dict] = _fonte_dados_relativa(
			_carregar(fixtures_dir, "fonte_dados"), date.today()
		)
		self.totais: dict[str, dict[str, str]] = {}  # CPF -> {coluna: "HH:MM"}
		self.chamadas: list[tuple[str, object]] = []
		self.falhas: list[Exception] = []
		self._registrar = registrar or (lambda chamada: None)
		self._proximo_id = max((int(f.get("Id") or 0) for f in self.funcionarios.values()), default=0) + 1

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
		if not encontrado:  # formato real: o vínculo ativo, senão o mais recente
			vinculos = [
				f
				for f in self.funcionarios.values()
				if somente_digitos(f.get("Cpf") or "") == somente_digitos(cpf)
			]
			vinculos.sort(key=lambda f: (not f.get("Demissao"), str(f.get("Admissao") or "")))
			encontrado = vinculos[-1] if vinculos else None
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

	# ------------------------------------------------------------------ leitura dos cadastros (importação)

	def _lista(self, rota: str, nome: str) -> list[dict]:
		self._chamada("GET", rota)
		return [dict(item) for item in self.cadastros[nome]]

	def listar_empresas(self) -> list[dict]:
		return self._lista("Empresas", "empresas")

	def listar_funcoes(self) -> list[dict]:
		return self._lista("Funcoes", "funcoes")

	def listar_departamentos(self) -> list[dict]:
		return self._lista("Departamentos", "departamentos")

	def listar_horarios(self) -> list[dict]:
		return self._lista("Horarios", "horarios")

	def listar_estruturas(self) -> list[dict]:
		self._chamada("GET", "Estruturas")
		return [dict(e) for e in self.estruturas]

	def listar_justificativas(self) -> list[dict]:
		return self._lista("Justificativas", "justificativas")

	def listar_motivos_demissao(self) -> list[dict]:
		return self._lista("MotivosDemissao", "motivos_demissao")

	def listar_equipamentos(self) -> list[dict]:
		return self._lista("Equipamentos", "equipamentos")

	def listar_cartao(self, data_inicio: date, data_fim: date, cpf: str | None = None) -> list[dict]:
		self._chamada(
			"GET", "Batidas", {"dataInicio": data_inicio.isoformat(), "dataFim": data_fim.isoformat()}
		)
		return [
			dict(r)
			for r in self.cartao
			if data_inicio.isoformat() <= str(r.get("Data") or "")[:10] <= data_fim.isoformat()
			and (not cpf or somente_digitos(r.get("FuncionarioCpf") or "") == somente_digitos(cpf))
		]

	def editar_cartao(self, metodo: str, rota: str, corpo: dict) -> None:
		"""Aplica a operação no cartão em memória; a batida manual também entra na FonteDados (Origem 8,
		IntegracaoExterna), como a coleta seguinte a traria do Secullum."""
		self._chamada(metodo, rota, corpo)
		cpf, dia = somente_digitos(corpo.get("Cpf") or ""), str(corpo["Data"])[:10]
		registro = next(
			(
				r
				for r in self.cartao
				if somente_digitos(r.get("FuncionarioCpf") or "") == cpf and str(r.get("Data"))[:10] == dia
			),
			None,
		)
		if registro is None:
			registro = {"FuncionarioCpf": cpf, "FuncionarioId": cpf, "Data": f"{dia}T00:00:00"}
			self.cartao.append(registro)
		if rota == "CartaoPonto/Manual":
			registro[corpo["Coluna"]] = corpo["Hora"]
			self.fonte_dados.append(
				{
					"Id": 900000 + len(self.fonte_dados),
					"FuncionarioId": cpf,
					"FuncionarioCpf": cpf,
					"EquipamentoId": None,
					"Data": f"{dia}T00:00:00",
					"DataInclusao": None,
					"Hora": corpo["Hora"],
					"Tipo": 1,
					"Origem": 8,
				}
			)
		elif rota == "CartaoPonto/Justificativa":
			grupo = int(corpo["Grupo"])
			registro[f"Entrada{grupo}"] = registro[f"Saida{grupo}"] = corpo["Justificativa"]
		else:
			coluna = corpo["Coluna"]
			valor = str(registro.get(coluna) or "")
			if valor and ":" not in valor:  # justificativa: apaga o grupo
				grupo = coluna[-1]
				registro.pop(f"Entrada{grupo}", None)
				registro.pop(f"Saida{grupo}", None)
			else:
				registro.pop(coluna, None)

	def listar_afastamentos(self, data_inicio: date, data_fim: date) -> list[dict]:
		self._chamada(
			"GET",
			"FuncionariosAfastamentos",
			{"dataInicio": data_inicio.isoformat(), "dataFim": data_fim.isoformat()},
		)
		return [dict(a) for a in self.cadastros["afastamentos"] if _no_periodo(a, data_inicio, data_fim)]
