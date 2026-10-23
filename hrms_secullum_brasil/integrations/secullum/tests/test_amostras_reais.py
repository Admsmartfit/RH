"""Guarda das amostras reais anonimizadas (integrations/secullum/fixtures/reais, docs/PRD-importacao-secullum.md
IS-03): nenhum documento, nome ou contato real pode estar no repositório."""

import json
import re
from pathlib import Path

import pytest

PASTA = Path(__file__).resolve().parent.parent / "fixtures" / "reais"
ARQUIVOS = sorted(PASTA.glob("*.json"))


def _valores(dado, chave=None):
	if isinstance(dado, dict):
		for k, v in dado.items():
			yield from _valores(v, k)
	elif isinstance(dado, list):
		for v in dado:
			yield from _valores(v, chave)
	else:
		yield chave, dado


@pytest.mark.skipif(not ARQUIVOS, reason="amostras ainda não gravadas")
@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=lambda p: p.name)
def test_amostra_sem_dado_pessoal(arquivo):
	dados = json.loads(arquivo.read_text(encoding="utf-8"))
	texto = arquivo.read_text(encoding="utf-8")
	assert set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", texto)) <= {
		"pessoa@example.com",
		"responsavel@example.com",
	}
	for chave, valor in _valores(dados):
		if not valor or not isinstance(valor, str):
			continue
		k = (chave or "").lower()
		if k in ("cpf", "funcionariocpf"):
			assert valor.startswith("9000"), f"CPF fora da faixa fictícia em {arquivo.name}"
		if k in ("numeropis", "funcionariopis"):
			assert valor.startswith("19"), f"PIS fora da faixa fictícia em {arquivo.name}"
		if k == "documento":
			assert valor.startswith("9000"), f"CNPJ fora da faixa fictícia em {arquivo.name}"
		if k == "nascimento":
			assert valor == "1990-01-01T00:00:00"
		if k == "nome" and arquivo.name in ("funcionarios.json", "empresas.json"):
			assert valor.startswith(("Pessoa Exemplo", "Empresa Exemplo")), f"nome real em {arquivo.name}"


def test_amostras_coerentes_entre_si():
	if not ARQUIVOS:
		pytest.skip("amostras ainda não gravadas")
	funcionarios = json.loads((PASTA / "funcionarios.json").read_text(encoding="utf-8"))
	empresas = json.loads((PASTA / "empresas.json").read_text(encoding="utf-8"))
	horarios = json.loads((PASTA / "horarios.json").read_text(encoding="utf-8"))
	afastamentos = json.loads((PASTA / "afastamentos.json").read_text(encoding="utf-8"))
	cpfs = {f["Cpf"] for f in funcionarios if f.get("Cpf")}
	assert {f["Empresa"]["Documento"] for f in funcionarios} <= {e["Documento"] for e in empresas}
	assert {f["Horario"]["Numero"] for f in funcionarios} <= {h["Numero"] for h in horarios}
	assert all(a["Cpf"] in cpfs for a in afastamentos)
