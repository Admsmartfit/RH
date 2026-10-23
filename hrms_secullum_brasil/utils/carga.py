"""Teste de carga da apuração (PRD Seção 10: 500 colaboradores x 31 dias em menos de 5 minutos).

Uso (no bench):
    bench --site testes.localhost execute hrms_secullum_brasil.utils.carga.executar \\
        --kwargs "{'colaboradores': 500, 'dias': 31}"

Cria colaboradores, perfil, CCT e batidas (inserção em lote, fora da medição), mede a apuração de todos os
dias pela fila `Reapuracao Pendente` e, por padrão, desfaz tudo no fim (nada fica gravado no site).
"""

import random
import time
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import now_datetime

from hrms_secullum_brasil.engine.documentos import cpf_valido

DIAS_UTEIS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira")


def _cpf(semente: int) -> str:
	base = f"{semente:09d}"[-9:]
	for _ in range(2):
		pesos = range(len(base) + 1, 1, -1)
		base += str(sum(int(d) * p for d, p in zip(base, pesos, strict=True)) * 10 % 11 % 10)
	assert cpf_valido(base)
	return base


def _cronometro():
	inicio = time.perf_counter()
	return lambda: round(time.perf_counter() - inicio, 1)


def preparar(colaboradores: int, dias: int, company: str, inicio: date) -> list[str]:
	etiqueta = frappe.generate_hash(length=6)
	perfil = frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"CARGA-{etiqueta}",
			"company": company,
			"tipo": "Fixa",
			"vigencia_inicio": inicio - timedelta(days=1),
			"dias": [
				{
					"dia_semana": d,
					"entrada1": "08:00",
					"saida1": "12:00",
					"entrada2": "13:00",
					"saida2": "17:00",
				}
				for d in DIAS_UTEIS
			],
		}
	).insert()
	cct = frappe.get_doc(
		{
			"doctype": "Regra Sindical CCT",
			"company": company,
			"sindicato": f"CARGA-{etiqueta}",
			"vigencia_inicio": inicio - timedelta(days=1),
		}
	).insert()

	nomes = []
	for i in range(colaboradores):
		emp = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": f"Carga {etiqueta} {i:04d}",
				"gender": frappe.db.get_value("Gender", {}, "name"),
				"date_of_birth": "1990-01-01",
				"date_of_joining": inicio - timedelta(days=365),
				"company": company,
				"status": "Active",
				"cpf": _cpf(random.randint(10**8, 10**9 - 1)),
				"perfil_jornada": perfil.name,
				"regra_cct": cct.name,
				"participa_banco_horas": i % 2,
			}
		)
		emp.flags.ignore_mandatory = True
		emp.insert(ignore_permissions=True)
		nomes.append(emp.name)

	raws, pendentes = [], []
	agora = now_datetime()
	for employee in nomes:
		for d in range(dias):
			dia = inicio + timedelta(days=d)
			if dia.weekday() < 5 and random.random() > 0.03:  # ~3% de faltas
				horarios = ["08:00", "12:00", "13:00", random.choice(["17:00", "17:03", "18:00", "19:00"])]
				if random.random() < 0.02:
					horarios = horarios[:3]  # marcação ímpar
				for h in horarios:
					hora, minuto = (int(x) for x in h.split(":"))
					momento = datetime(dia.year, dia.month, dia.day, hora, minuto)
					origem = frappe.generate_hash(length=10)
					raws.append(
						(
							frappe.generate_hash(length=10),
							agora,
							agora,
							"Administrator",
							"Administrator",
							employee,
							dia,
							momento,
							"Ativa",
							"Original",
							"RelogioPonto",
							origem,
							frappe.generate_hash(length=20),
							f"{employee}|{momento.isoformat()}|{origem}",
						)
					)
			pendentes.append(
				(
					frappe.generate_hash(length=10),
					agora,
					agora,
					"Administrator",
					"Administrator",
					employee,
					dia,
					"Pendente",
					"carga",
					agora,
				)
			)
	frappe.db.bulk_insert(
		"Secullum Checkin Raw",
		fields=[
			"name",
			"creation",
			"modified",
			"owner",
			"modified_by",
			"employee",
			"data",
			"data_hora",
			"status",
			"tipo_fonte",
			"tipo_origem",
			"origem_id",
			"hash",
			"chave_unica",
		],
		values=raws,
		chunk_size=5000,
	)
	frappe.db.bulk_insert(
		"Reapuracao Pendente",
		fields=[
			"name",
			"creation",
			"modified",
			"owner",
			"modified_by",
			"employee",
			"data",
			"status",
			"motivo",
			"ultima_solicitacao",
		],
		values=pendentes,
		chunk_size=5000,
	)
	return nomes


def medir_painel(company: str, competencia: str = "2026-08", repeticoes: int = 3) -> dict:
	"""Tempo do painel /ponto (FE-08): resumo < 2 s e inconsistencias (50 itens) < 1 s. Primeira chamada e a
	melhor de `repeticoes`."""
	from hrms_secullum_brasil.apuracao import painel

	def medir(funcao):
		tempos = []
		for _ in range(repeticoes):
			inicio = time.perf_counter()
			funcao()
			tempos.append(time.perf_counter() - inicio)
		return round(tempos[0], 3), round(min(tempos), 3)

	frappe.clear_cache()
	resumo = medir(lambda: painel.resumo(competencia, company=company))
	lista = medir(lambda: painel.inconsistencias({"competencia": competencia, "company": company}, 0, 50))
	return {
		"painel_resumo_s": resumo,
		"painel_inconsistencias_s": lista,
		"painel_meta": resumo[0] < 2 and lista[0] < 1,
	}


def executar(
	colaboradores: int = 500,
	dias: int = 31,
	company: str | None = None,
	manter: bool = False,
	painel: bool = True,
) -> dict:
	from hrms_secullum_brasil.apuracao.servico import processar_reapuracoes_pendentes

	company = (
		company
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.get_all("Company", pluck="name")[0]
	)
	inicio = date(2026, 8, 1)
	frappe.db.set_value("Company", company, "ponto_fechado_ate", None)
	frappe.flags.in_test = True  # a fila não faz commit por dia; tudo é desfeito no fim
	resultado = {"colaboradores": colaboradores, "dias": dias}
	try:
		tempo = _cronometro()
		preparar(colaboradores, dias, company, inicio)
		resultado["preparo_s"] = tempo()

		tempo = _cronometro()
		processados = processar_reapuracoes_pendentes(limite=colaboradores * dias + 1)
		resultado["apuracao_s"] = tempo()
		resultado["dias_apurados"] = processados
		resultado["dias_por_segundo"] = round(processados / max(resultado["apuracao_s"], 0.1), 1)
		resultado["meta_5_min"] = resultado["apuracao_s"] < 300
		if painel:
			resultado.update(medir_painel(company))
		if manter:
			frappe.db.commit()
	finally:
		frappe.flags.in_test = False
		if not manter:
			frappe.db.rollback()
	print(resultado)
	return resultado


def perfilar(
	colaboradores: int = 10,
	dias: int = 31,
	linhas: int = 35,
	ordem: str = "cumulative",
	arquivo: str | None = None,
) -> None:
	"""cProfile da apuração em lote (sem gravar nada): mostra onde o tempo é gasto."""
	import cProfile
	import io
	import pstats

	from hrms_secullum_brasil.apuracao.servico import processar_reapuracoes_pendentes

	company = (
		frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.get_all("Company", pluck="name")[0]
	)
	frappe.db.set_value("Company", company, "ponto_fechado_ate", None)
	frappe.flags.in_test = True
	try:
		preparar(colaboradores, dias, company, date(2026, 8, 1))
		perfil = cProfile.Profile()
		perfil.enable()
		processar_reapuracoes_pendentes(limite=colaboradores * dias + 1)
		perfil.disable()
		if arquivo:
			perfil.dump_stats(arquivo)
		saida = io.StringIO()
		pstats.Stats(perfil, stream=saida).sort_stats(ordem).print_stats(linhas)
		print(saida.getvalue())
		print("queries:", frappe.db.sql("show session status like 'Questions'"))
	finally:
		frappe.flags.in_test = False
		frappe.db.rollback()
