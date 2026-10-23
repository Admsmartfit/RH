"""Descoberta das respostas reais do Secullum (docs/PRD-importacao-secullum.md, IS-03).

    bench --site ponto.localhost execute hrms_secullum_brasil.ingestion.amostras_secullum.estrutura
    bench --site ponto.localhost execute hrms_secullum_brasil.ingestion.amostras_secullum.gravar

- estrutura: mostra, de cada GET, só os nomes dos campos, os tipos e as contagens (nenhum valor).
- gravar: grava uma amostra ANONIMIZADA de cada resposta em integrations/secullum/fixtures/reais/
  (integrations/secullum/anonimizar.py). Os dados reais não saem da memória.
"""

import json
from datetime import timedelta
from pathlib import Path

import frappe
from frappe.utils import getdate, today

from hrms_secullum_brasil.ingestion.secullum import get_client

PASTA = Path(__file__).resolve().parent.parent / "integrations" / "secullum" / "fixtures" / "reais"


def _rotas() -> list[tuple[str, str, dict]]:
	hoje = getdate(today())
	ontem = hoje - timedelta(days=1)
	return [
		("empresas", "Empresas", {}),
		("funcoes", "Funcoes", {}),
		("departamentos", "Departamentos", {}),
		("horarios", "Horarios", {}),
		("funcionarios", "Funcionarios", {}),
		("estruturas", "Estruturas", {}),
		("justificativas", "Justificativas", {}),
		("motivos_demissao", "MotivosDemissao", {}),
		("equipamentos", "Equipamentos", {}),
		(
			"afastamentos",
			"FuncionariosAfastamentos",
			{"dataInicio": str(hoje - timedelta(days=365)), "dataFim": str(hoje + timedelta(days=90))},
		),
		("fonte_dados", "FonteDados", {"dataInicio": str(ontem), "dataFim": str(ontem)}),
	]


def _ler(rota: str, params: dict):
	cliente = get_client()
	try:
		return cliente._api("GET", rota, params=params or None), None
	except Exception as exc:  # a descoberta mostra o erro de cada rota e segue
		return None, f"{type(exc).__name__}: {str(exc)[:200]}"


def _forma(valor, profundidade: int = 0):
	"""Estrutura de um valor JSON sem o conteúdo: tipos, chaves e tamanhos."""
	if isinstance(valor, list):
		itens = [_forma(v, profundidade + 1) for v in valor[:50]]
		chaves: dict = {}
		for item in itens:
			if isinstance(item, dict):
				for k, v in item.items():
					chaves.setdefault(k, v)
		return {"lista": len(valor), "item": chaves or (itens[0] if itens else None)}
	if isinstance(valor, dict):
		return {k: _forma(v, profundidade + 1) for k, v in valor.items()}
	if valor is None:
		return "null"
	return type(valor).__name__


def estrutura() -> dict:
	saida = {}
	for nome, rota, params in _rotas():
		dados, erro = _ler(rota, params)
		saida[nome] = {"erro": erro} if erro else _forma(dados)
	print(json.dumps(saida, ensure_ascii=False, indent=1))
	return saida


def _recorte(dados: dict) -> dict:
	"""Amostra pequena e coerente: todos os ativos e até 30 demitidos; afastamentos e batidas só deles."""
	funcionarios = dados.get("funcionarios") or []
	ativos = [f for f in funcionarios if not f.get("Demissao")]
	demitidos = sorted(
		(f for f in funcionarios if f.get("Demissao")), key=lambda f: f["Demissao"], reverse=True
	)
	escolhidos = ativos + demitidos[:30]
	cpfs = {"".join(c for c in str(f.get("Cpf") or "") if c.isdigit()) for f in escolhidos}

	def do_grupo(item, campo):
		return "".join(c for c in str(item.get(campo) or "") if c.isdigit()) in cpfs

	dados["funcionarios"] = escolhidos
	dados["afastamentos"] = [a for a in dados.get("afastamentos") or [] if do_grupo(a, "Cpf")][:80]
	dados["fonte_dados"] = [b for b in dados.get("fonte_dados") or [] if do_grupo(b, "FuncionarioCpf")]
	return dados


def gravar() -> list[str]:
	from hrms_secullum_brasil.integrations.secullum.anonimizar import Anonimizador

	reais = {}
	for nome, rota, params in _rotas():
		dados, erro = _ler(rota, params)
		if erro:
			print(f"{nome}: {erro}")
			continue
		reais[nome] = dados
	reais = _recorte(reais)
	anonimizador = Anonimizador(semente=frappe.generate_hash(length=12))
	amostras = {nome: anonimizador.anonimizar(dados) for nome, dados in reais.items()}
	vazados = anonimizador.sobrou_original(amostras)
	if vazados:
		frappe.throw(f"{len(vazados)} documento(s) real(is) sobraram na anonimização; nada foi gravado.")
	PASTA.mkdir(parents=True, exist_ok=True)
	for nome, amostra in amostras.items():
		texto = json.dumps(amostra, ensure_ascii=False, indent=1)
		if len(texto) > 100_000:  # horários e funcionários: compacto, para não pesar o repositório
			texto = json.dumps(amostra, ensure_ascii=False, separators=(",", ":"))
		(PASTA / f"{nome}.json").write_text(texto + chr(10), encoding="utf-8")
	resumo = {nome: len(a) if isinstance(a, list) else 1 for nome, a in amostras.items()}
	print("Amostras anonimizadas gravadas:", resumo)
	return sorted(resumo)
