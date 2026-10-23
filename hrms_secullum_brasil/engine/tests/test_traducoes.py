"""Arquivo de traduções pt-BR do app (translations/pt-BR.csv): completa o que o Frappe, o ERPNext e o HRMS v16 não
traduzem (o HRMS vem 100% sem tradução para pt-BR). Garante que cada linha é válida e que os marcadores ({0}, {}...)
da origem continuam na tradução — uma tradução trocada de linha costuma quebrar isso."""

import csv
import re
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[2] / "translations" / "pt-BR.csv"
MARCADOR = re.compile(r"\{[^}]*\}")


def linhas():
	with ARQUIVO.open(encoding="utf-8", newline="") as f:
		return [linha for linha in csv.reader(f) if linha]


def test_linhas_validas_e_sem_repeticao():
	vistos = set()
	for linha in linhas():
		assert len(linha) in (2, 3), linha
		origem, traducao = linha[0], linha[1]
		contexto = linha[2] if len(linha) == 3 else ""
		assert origem and traducao, linha
		assert (origem, contexto) not in vistos, f"repetida: {origem}"
		vistos.add((origem, contexto))


def test_marcadores_preservados():
	erradas = [
		(t[0], t[1]) for t in linhas() if sorted(MARCADOR.findall(t[0])) != sorted(MARCADOR.findall(t[1]))
	]
	assert erradas == []


def test_termos_principais():
	traducoes = {t[0]: t[1] for t in linhas() if len(t) == 2 or not t[2]}
	assert traducoes["Salary Slip"] == "Holerite"
	assert traducoes["Leave Application"] == "Licença"
	assert traducoes["Deductions"] == "Descontos"
	assert traducoes["Earnings"] == "Proventos"
	assert traducoes["Inconsistencia de Ponto"] == "Inconsistência de Ponto"
