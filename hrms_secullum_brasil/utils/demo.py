"""Cenário de TESTE da ES Fitness (um colaborador por cargo) e batidas simuladas, para o manual
docs/manual_teste_windows.md. Só para o site de testes/desenvolvimento — não use em produção.

    bench --site testes.localhost execute hrms_secullum_brasil.utils.demo.preparar_teste
    bench --site testes.localhost execute hrms_secullum_brasil.utils.demo.bater --kwargs "{'cargo': 'recepcao', 'data': '2026-10-05', 'horarios': '08:00 12:00 13:00 17:48'}"
    bench --site testes.localhost execute hrms_secullum_brasil.utils.demo.semana --kwargs "{'cargo': 'recepcao', 'segunda': '2026-10-05'}"

Os valores (piso, tarifas, bolsa, laudo) são fictícios.
"""

from datetime import date, datetime, timedelta

import frappe
from frappe.utils import getdate
from frappe.utils.nestedset import rebuild_tree

from hrms_secullum_brasil.utils.config_es_fitness import EMPRESA, SINDICATO, aplicar
from hrms_secullum_brasil.utils.seeds import _colaborador, _get_or_insert, _perfil

DIAS_UTEIS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira")
CARGOS = {
	"recepcao": "Recepcionista",
	"asg": "Auxiliar de Serviços Gerais",
	"instrutor": "Instrutor de Musculação",
	"estagiario": "Estagiário",
}
# chave: (nome, CPF base, cargo, perfil, campos do Employee)
NOMES = {
	"recepcao": ("Renata Teste Recepção", "300000001", "recepcao", "recepcao", {"gender": "Female"}),
	"asg": ("Antônio Teste ASG", "300000002", "asg", "asg", {"gender": "Male"}),
	"instrutor": (
		"Igor Teste Instrutor",
		"300000003",
		"instrutor",
		"instrutor",
		{"tipo_remuneracao": "Horista", "gender": "Male"},
	),
	"estagiario": ("Elisa Teste Estagiária", "300000004", "estagiario", "estagiario", {"gender": "Female"}),
	"recepcao2": ("Bruno Teste Recepção", "300000005", "recepcao", "recepcao", {"gender": "Male"}),
	"recepcao_noite": (
		"Marcos Teste Recepção Noite",
		"300000006",
		"recepcao",
		"recepcao_noite",
		{"gender": "Male"},
	),
	"asg2": ("Carla Teste ASG", "300000007", "asg", "asg", {"gender": "Female"}),
	"instrutor2": (
		"Paula Teste Instrutora",
		"300000008",
		"instrutor",
		"instrutor",
		{"tipo_remuneracao": "Horista", "gender": "Female"},
	),
}
HORARIOS_PADRAO = {
	"recepcao": "08:00 12:00 13:00 17:48",
	"asg": "08:00 12:00 13:00 17:48",
	"instrutor": "06:00 10:00",
	"estagiario": "08:00 14:00",
	"recepcao2": "08:00 12:00 13:00 17:48",
	"recepcao_noite": "13:12 18:00 19:00 23:00",
	"asg2": "08:00 12:00 13:00 17:48",
	"instrutor2": "06:00 10:00",
}
SALARIOS = {
	"recepcao": 1800,
	"asg": 1700,
	"instrutor": 16.50,
	"estagiario": 1200,
	"recepcao2": 1800,
	"recepcao_noite": 1900,
	"asg2": 1700,
	"instrutor2": 16.50,
}


def _dias(entrada1, saida1, entrada2=None, saida2=None, dias=DIAS_UTEIS):
	return [
		{
			"dia_semana": d,
			"entrada1": entrada1,
			"saida1": saida1,
			**({"entrada2": entrada2, "saida2": saida2} if entrada2 else {}),
		}
		for d in dias
	]


def colaborador(cargo: str) -> str:
	nome = frappe.db.get_value("Employee", {"company": EMPRESA, "employee_name": NOMES[cargo][0]}, "name")
	if not nome:
		frappe.throw(f"Rode primeiro preparar_teste (colaborador de {cargo} não encontrado).")
	return nome


def preparar_teste() -> dict:
	"""Cria (sem duplicar) a empresa, a CCT, os cargos, perfis, colaboradores e cadastros de teste."""
	aplicar(valor_dia_vr=25)
	for cargo in CARGOS.values():
		_get_or_insert("Designation", {"designation_name": cargo}, {"designation_name": cargo})
	cct = frappe.get_doc("Regra Sindical CCT", {"company": EMPRESA, "sindicato": SINDICATO})
	if not cct.parametros_cargo:
		cct.append(
			"parametros_cargo",
			{
				"designation": CARGOS["recepcao"],
				"tipo_piso": "Mensalista",
				"valor_piso": 1650,
				"carga_referencia_horas": 44,
				"banco_padrao": 1,
			},
		)
		cct.append("parametros_cargo", {"designation": CARGOS["asg"], "banco_padrao": 1})
		cct.append(
			"parametros_cargo",
			{
				"designation": CARGOS["instrutor"],
				"tipo_piso": "Horista",
				"valor_piso": 15.20,
				"banco_padrao": 0,
			},
		)
		cct.save()
	perfis = {
		"recepcao": _perfil(
			EMPRESA,
			"TESTE-RECEPCAO-5X2",
			"Fixa",
			_dias("08:00", "12:00", "13:00", "17:48"),
			carga_semanal_minutos=2640,
			divisor=220,
		),
		"asg": _perfil(
			EMPRESA,
			"TESTE-ASG-5X2",
			"Fixa",
			_dias("08:00", "12:00", "13:00", "17:48"),
			carga_semanal_minutos=2640,
			divisor=220,
		),
		"instrutor": _perfil(EMPRESA, "TESTE-INSTRUTOR-HORISTA", "Horista", _dias("06:00", "10:00")),
		"estagiario": _perfil(
			EMPRESA,
			"TESTE-ESTAGIO-6H",
			"Fixa",
			_dias("08:00", "14:00"),
			carga_semanal_minutos=1800,
			divisor=150,
		),
		"recepcao_noite": _perfil(
			EMPRESA,
			"TESTE-RECEPCAO-NOITE",
			"Fixa",
			_dias("13:12", "18:00", "19:00", "23:00"),
			carga_semanal_minutos=2640,
			divisor=220,
		),
	}
	pessoas = {}
	for chave, (nome, cpf, cargo, perfil, extras) in NOMES.items():
		pessoas[chave] = _colaborador(
			EMPRESA, nome, cpf, CARGOS[cargo], perfis[perfil], cct, date_of_joining="2026-05-01", **extras
		)
	# horista: salário-base = valor da hora, com divisor 1 (Igor com mínimo de 80h no mês; Paula sem mínimo)
	frappe.db.set_value(
		"Employee",
		pessoas["instrutor"],
		{"minimo_horas": 80, "minimo_periodo": "Mês", "divisor_horas": 1},
	)
	frappe.db.set_value("Employee", pessoas["instrutor2"], "divisor_horas", 1)
	_definir_chefe(pessoas["estagiario"], pessoas["recepcao"])
	_estrutura_salarial(pessoas)

	# salário mínimo, insalubridade do ASG, EPI, tarifa de VT
	_get_or_insert(
		"Salario Minimo",
		{"vigencia_inicio": "2026-01-01"},
		{"vigencia_inicio": date(2026, 1, 1), "valor": 1621},
	)
	if not frappe.db.exists("Regra de Adicional de Risco", {"company": EMPRESA}):
		frappe.get_doc(
			{
				"doctype": "Regra de Adicional de Risco",
				"company": EMPRESA,
				"tipo": "Insalubridade",
				"percentual": 20,
				"base_calculo": "Salário base",
				"vigencia_inicio": date(2026, 5, 1),
				"laudo_numero": "LTCAT-TESTE",
				"laudo_validade": date(2027, 12, 31),
				"cargos": [{"designation": CARGOS["asg"]}],
			}
		).insert(ignore_permissions=True)
	for item, prazo in (("Luvas de borracha (teste)", 30), ("Botas de segurança (teste)", 180)):
		_get_or_insert(
			"Item de Seguranca",
			{"nome_item": item},
			{
				"nome_item": item,
				"tipo": "EPI",
				"ca_numero": "00000",
				"ca_validade": date(2028, 12, 31),
				"prazo_troca_dias": prazo,
				"cargos": [{"designation": CARGOS["asg"]}],
			},
		)
	_get_or_insert(
		"Item de Seguranca",
		{"nome_item": "Camiseta uniforme (teste)"},
		{"nome_item": "Camiseta uniforme (teste)", "tipo": "Uniforme"},
	)
	tarifa = _get_or_insert(
		"Tarifa VT",
		{"company": EMPRESA, "codigo_gvbus": "A"},
		{
			"company": EMPRESA,
			"codigo_gvbus": "A",
			"descricao": "Passagem ônibus (teste)",
			"valores": [{"vigencia_inicio": date(2026, 1, 1), "valor": 5}],
		},
	)
	frappe.db.set_value(
		"Employee",
		pessoas["recepcao"],
		{
			"usa_vt": 1,
			"cartao_gv": "123456",
			"rg": "1234567",
			"rg_orgao": "SSP/ES",
			"vt_tarifa1": tarifa.name,
			"vt_qtd_tarifa1": 2,
		},
	)

	# estagiária com TCE
	_get_or_insert("Instituicao de Ensino", {"nome": "UFES (teste)"}, {"nome": "UFES (teste)"})
	if not frappe.db.exists(
		"Termo de Compromisso de Estagio", {"employee": pessoas["estagiario"], "docstatus": 1}
	):
		tce = frappe.get_doc(
			{
				"doctype": "Termo de Compromisso de Estagio",
				"employee": pessoas["estagiario"],
				"instituicao": "UFES (teste)",
				"agente": "CIEE-ES",
				"nivel_ensino": "Superior",
				"vigencia_inicio": date(2026, 5, 1),
				"vigencia_fim": date(2027, 4, 30),
				"carga_diaria": 360,
				"carga_semanal": 1800,
				"bolsa": 1200,
				"auxilio_transporte": 150,
				"supervisor": pessoas["recepcao"],
				"seguro_fim": date(2027, 4, 30),
			}
		)
		tce.insert(ignore_permissions=True)
		tce.submit()
	usuarios_de_teste(pessoas)
	frappe.db.commit()
	resumo = {chave: pessoas[chave] for chave in pessoas}
	print("Cenário de teste pronto:", resumo)
	return resumo


SENHA_TESTE = "Ponto@teste1"
USUARIO_RH = "rh.teste@esfitness.local"
USUARIO_GESTOR = "gestor.teste@esfitness.local"


def _usuario(email: str, nome: str, papeis: tuple[str, ...]) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": nome,
				"send_welcome_email": 0,
				"language": "pt-BR",
				"new_password": SENHA_TESTE,
			}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles(*papeis)
	return email


def _definir_chefe(employee: str, chefe: str) -> None:
	"""reports_to pelo documento (não por set_value), para a árvore lft/rgt acompanhar."""
	if frappe.db.get_value("Employee", employee, "reports_to") == chefe:
		return
	doc = frappe.get_doc("Employee", employee)
	doc.reports_to = chefe
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.save()


def usuarios_de_teste(pessoas: dict | None = None) -> dict:
	"""Usuários para testar o painel /ponto (senha Ponto@teste1):
	- rh.teste@esfitness.local: RH Ponto (vê todos);
	- gestor.teste@esfitness.local: Gestor Ponto, chefe das recepcionistas (Renata, Bruno, Marcos e, abaixo da
	  Renata, a estagiária Elisa). O colaborador do gestor é criado sem a User Permission do HRMS, que o
	  restringiria ao próprio cadastro (docs/implantacao.md)."""
	pessoas = pessoas or {chave: colaborador(chave) for chave in NOMES}
	_usuario(USUARIO_RH, "Rita Teste RH", ("RH Ponto",))
	_usuario(USUARIO_GESTOR, "Gustavo Teste Gestor", ("Gestor Ponto",))
	gestor = frappe.db.get_value("Employee", {"user_id": USUARIO_GESTOR}, "name")
	if not gestor:
		cct = frappe.get_doc("Regra Sindical CCT", {"company": EMPRESA, "sindicato": SINDICATO})
		perfil = frappe.get_doc("Perfil de Jornada", {"codigo": "TESTE-RECEPCAO-5X2"})
		gestor = _colaborador(
			EMPRESA,
			"Gustavo Teste Gestor",
			"300000009",
			CARGOS["recepcao"],
			perfil,
			cct,
			date_of_joining="2026-05-01",
			gender="Male",
			create_user_permission=0,
			user_id=USUARIO_GESTOR,
		)
	for chave in ("recepcao", "recepcao2", "recepcao_noite"):
		_definir_chefe(pessoas[chave], gestor)
	rebuild_tree("Employee")  # a visibilidade do gestor usa a árvore (lft/rgt) do Employee
	frappe.db.commit()
	print(f"Usuários de teste: {USUARIO_RH} e {USUARIO_GESTOR} (senha {SENHA_TESTE}).")
	return {"rh": USUARIO_RH, "gestor": USUARIO_GESTOR, "gestor_employee": gestor}


def _estrutura_salarial(pessoas: dict) -> None:
	"""Estrutura salarial simples (só o salário-base) e a atribuição de cada colaborador de teste."""
	_get_or_insert(
		"Salary Component",
		{"salary_component": "Salário Base (teste)"},
		{"salary_component": "Salário Base (teste)", "salary_component_abbr": "SBT", "type": "Earning"},
	)
	estrutura = "TESTE ES Fitness"
	if not frappe.db.exists("Salary Structure", estrutura):
		doc = frappe.get_doc(
			{
				"doctype": "Salary Structure",
				"name": estrutura,
				"company": EMPRESA,
				"payroll_frequency": "Monthly",
				"currency": frappe.db.get_value("Company", EMPRESA, "default_currency"),
				"earnings": [
					{
						"salary_component": "Salário Base (teste)",
						"abbr": "SBT",
						"amount_based_on_formula": 1,
						"formula": "base",
					}
				],
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
	for chave, base in SALARIOS.items():
		employee = pessoas[chave]
		if frappe.db.exists("Salary Structure Assignment", {"employee": employee, "docstatus": 1}):
			continue
		ssa = frappe.get_doc(
			{
				"doctype": "Salary Structure Assignment",
				"employee": employee,
				"salary_structure": estrutura,
				"company": EMPRESA,
				"from_date": date(2026, 5, 1),
				"base": base,
			}
		)
		ssa.insert(ignore_permissions=True)
		ssa.submit()


def _inserir_batidas(employee: str, dia: date, horarios: str) -> None:
	for texto in horarios.split():
		hora, minuto = (int(x) for x in texto.split(":"))
		momento = datetime(dia.year, dia.month, dia.day, hora, minuto)
		origem = f"TESTE-{frappe.generate_hash(length=8)}"
		frappe.get_doc(
			{
				"doctype": "Secullum Checkin Raw",
				"employee": employee,
				"data": dia,
				"data_hora": momento,
				"status": "Ativa",
				"tipo_fonte": "Original",
				"tipo_origem": "RelogioPonto",
				"origem_id": origem,
				"hash": frappe.generate_hash(length=16),
				"chave_unica": f"{employee}|{momento.isoformat()}|{origem}",
			}
		).insert(ignore_permissions=True)


def bater(cargo: str, data: str, horarios: str | None = None, reapurar: int = 1) -> str | None:
	"""Cria batidas simuladas (como se viessem do Secullum) e reapura o dia. horarios = "08:00 12:00 13:00 17:48"."""
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	employee = colaborador(cargo)
	dia = getdate(data)
	_inserir_batidas(employee, dia, horarios or HORARIOS_PADRAO[cargo])
	nome = reapurar_dia(employee, dia) if int(reapurar) else None
	frappe.db.commit()
	print(f"{cargo} {dia}: batidas {horarios or HORARIOS_PADRAO[cargo]} → apuração {nome}")
	return nome


def semana(cargo: str, segunda: str, horarios: str | None = None, dias: int = 5) -> None:
	"""Bate o horário padrão do cargo de segunda até `dias` dias depois."""
	inicio = getdate(segunda)
	for i in range(int(dias)):
		bater(cargo, str(inicio + timedelta(days=i)), horarios)


def apurar(cargo: str, data: str) -> str:
	"""Reapura um dia sem batida nova (ex.: para gerar a falta de um dia sem batidas)."""
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	nome = reapurar_dia(colaborador(cargo), getdate(data))
	frappe.db.commit()
	print(f"{cargo} {data}: apuração {nome}")
	return nome


# Ocorrências de agosto/2026 (dia: horários; "" = falta). Nos demais dias úteis, o horário padrão deslocado em até
# 2 min (dentro da tolerância). Fins de semana sem batida, salvo o que está aqui.
OCORRENCIAS_AGOSTO = {
	"recepcao": {
		5: "08:25 12:00 13:00 17:48",  # atraso de 25 min (vai ao banco)
		12: "",  # falta
		19: "08:00 12:00 13:00",  # esqueceu a saída: marcação ímpar
		26: "08:00 12:00 13:00 19:30",  # HE de 1h42 (banco)
	},
	"recepcao2": {
		7: "08:00 12:00 13:00 16:30",  # saída antecipada
		14: "08:00 12:00 13:00 20:18",  # HE de 2h30: acima do limite
		21: "08:00 12:00 12:40 17:48",  # intervalo de 40 min
		22: "08:00 12:00",  # sábado trabalhado (HE 50%, banco)
	},
	"recepcao_noite": {
		11: "13:12 18:00 19:00 23:45",  # HE noturna
		28: "",  # falta
	},
	"asg": {
		6: "",  # falta
		10: "08:00 08:01 12:00 13:00 17:48",  # batida repetida (ignorada)
		24: "08:00 12:00 13:00 22:30",  # HE longa até 22:30 (noturno)
		25: "08:00 12:00 13:00 17:48",  # voltou 9h30 depois: interjornada
		27: "08:00 12:00 12:30 17:18",  # intervalo de 30 min
	},
	"asg2": {
		4: "08:08 12:00 13:00 17:48",  # atraso de 8 min (passa da tolerância por marcação)
		13: "",  # falta (para lançar atestado)
		14: "",  # falta (para lançar atestado)
	},
	"instrutor": {
		8: "06:00 10:00",  # sábado: horas normais (horista)
		17: "",  # falta
		29: "07:00 11:00",  # sábado
	},
	"instrutor2": {
		5: "06:00 10:00 17:00 21:00",  # 8h no dia
		12: "06:00 10:00 13:00 18:00",  # 9h: 1h de HE (acima de 8h)
		26: "",  # falta
	},
	"estagiario": {
		18: "08:00 15:00",  # 1h além do TCE
		25: "",  # falta (desconta a bolsa)
	},
}


def _com_variacao(horarios: str, rng) -> str:
	"""Desloca o dia inteiro em até 2 min (dentro da tolerância), sem mudar a duração da jornada nem do intervalo."""
	deslocamento = rng.randint(-2, 2)
	saida = []
	for texto in horarios.split():
		hora, minuto = (int(x) for x in texto.split(":"))
		total = hora * 60 + minuto + deslocamento
		saida.append(f"{total // 60:02d}:{total % 60:02d}")
	return " ".join(saida)


def gerar_agosto() -> None:
	"""Mês completo (agosto/2026) para os 8 colaboradores de teste: batidas de todos os dias úteis, com as
	ocorrências de OCORRENCIAS_AGOSTO, e a apuração de todos os dias do mês. Não duplica quem já tem batidas."""
	import random

	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	rng = random.Random(202608)
	dias = [date(2026, 8, d) for d in range(1, 32)]
	for chave in NOMES:
		employee = colaborador(chave)
		if frappe.db.exists(
			"Secullum Checkin Raw", {"employee": employee, "data": ["between", [dias[0], dias[-1]]]}
		):
			print(f"{chave}: agosto já gerado, pulando.")
			continue
		ocorrencias = OCORRENCIAS_AGOSTO.get(chave, {})
		for dia in dias:
			horarios = ocorrencias.get(dia.day)
			if horarios is None:
				if dia.weekday() >= 5:
					continue
				horarios = _com_variacao(HORARIOS_PADRAO[chave], rng)
			if horarios:
				_inserir_batidas(employee, dia, horarios)
		for dia in dias:
			reapurar_dia(employee, dia)
		frappe.db.commit()
		print(f"{chave}: agosto gerado e apurado.")


# Os 14 cenários de batida de setembro/2026 do docs/manual_teste_windows.md (Parte 4); None = dia sem batida
CENARIOS_SETEMBRO = (
	("recepcao", "2026-09-14", "08:00 12:00 13:00 17:48"),
	("recepcao", "2026-09-15", "08:04 12:00 13:00 17:48"),
	("recepcao", "2026-09-16", "08:20 12:00 13:00 17:48"),
	("recepcao", "2026-09-17", None),
	("recepcao", "2026-09-18", "08:00 12:00 13:00"),
	("recepcao", "2026-09-07", None),
	("asg", "2026-09-07", "08:00 12:00 13:00 17:48"),
	("asg", "2026-09-14", "08:00 12:00 13:00 19:00"),
	("asg", "2026-09-15", "08:00 12:00 12:30 17:18"),
	("asg", "2026-09-16", "13:00 17:00 18:00 23:00"),
	("asg", "2026-09-17", "08:00 12:00 13:00 17:48"),
	("estagiario", "2026-09-14", "08:00 15:00"),
	("instrutor", "2026-09-14", "06:00 10:00"),
	("instrutor", "2026-09-19", "06:00 12:00"),
)


def cenarios_setembro() -> list[dict]:
	"""Cria (sem duplicar) os 14 cenários de setembro do manual e apura cada dia."""
	saida = []
	for cargo, data, horarios in CENARIOS_SETEMBRO:
		employee = colaborador(cargo)
		ja_tem = frappe.db.exists("Secullum Checkin Raw", {"employee": employee, "data": data})
		nome = bater(cargo, data, horarios) if horarios and not ja_tem else apurar(cargo, data)
		saida.append({"cargo": cargo, "employee": employee, "data": data, "apuracao": nome})
	_marcacao_substituida()
	return saida


def _marcacao_substituida() -> None:
	"""21/09 da Renata: a batida das 08:00 foi substituída no Secullum pela das 08:05 (gaveta de auditoria).
	Só para o cenário de teste: na operação, quem marca a substituição é a coleta (ingestion/coleta_batidas.py)."""
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	employee, dia = colaborador("recepcao"), date(2026, 9, 21)
	frappe.db.set_value("Employee", employee, "pis", "12012345678")
	if frappe.db.exists("Secullum Checkin Raw", {"employee": employee, "data": dia}):
		return
	_inserir_batidas(employee, dia, "08:05 12:00 13:00 17:48")
	nova = frappe.db.get_value(
		"Secullum Checkin Raw", {"employee": employee, "data_hora": datetime(2026, 9, 21, 8, 5)}, "name"
	)
	momento = datetime(2026, 9, 21, 8, 0)
	frappe.get_doc(
		{
			"doctype": "Secullum Checkin Raw",
			"employee": employee,
			"data": dia,
			"data_hora": momento,
			"status": "Substituida",
			"tipo_fonte": "Original",
			"tipo_origem": "RelogioPonto",
			"equipamento": "REP-RECEPCAO-01",
			"origem_id": f"TESTE-{frappe.generate_hash(length=8)}",
			"hash": frappe.generate_hash(length=16),
			"chave_unica": f"{employee}|{momento.isoformat()}|substituida",
			"substituida_por": nova,
			"substituida_em": datetime(2026, 9, 21, 9, 30),
			"motivo_substituicao": "Horário ajustado no Secullum",
		}
	).insert(ignore_permissions=True)
	reapurar_dia(employee, dia)
	frappe.db.commit()


POR_COLABORADOR = (
	"Secullum Checkin Raw",
	"Apuracao Diaria",
	"Inconsistencia de Ponto",
	"Tratamento de Ponto",
	"DSR Semanal",
	"Banco de Horas Movimento",
	"Reapuracao Pendente",
	"Avaliacao Mensal",
	"Espelho de Ponto",
	"Alerta Previdenciario",
	"Atestado Medico",
	"Escala Mensal",
	"Divergencia Totais Secullum",
	"Entrega de EPI",
	"ASO",
	"Treinamento Realizado",
	"Log Carga VT",
	"Leave Application",
	"Additional Salary",
	"Salary Slip",
)
POR_EMPRESA = ("Fechamento de Ponto", "Fechamento Banco de Horas", "Carga de VT")


def _apagar(doctype: str, nomes: list[str]) -> None:
	if not nomes:
		return
	for campo in frappe.get_meta(doctype).get_table_fields():
		frappe.db.delete(campo.options, {"parent": ["in", nomes], "parenttype": doctype})
	frappe.db.delete(doctype, {"name": ["in", nomes]})


def limpar_teste() -> None:
	"""Apaga as batidas, apurações, tratamentos, escalas, fechamentos e lançamentos dos colaboradores de teste
	(os cadastros ficam). Só no modo de desenvolvimento: nunca rode em produção."""
	from hrms_secullum_brasil.payroll_handoff.fechamento import atualizar_trava

	if not frappe.conf.developer_mode:
		frappe.throw("limpar_teste só roda em site de desenvolvimento (developer_mode).")
	pessoas = frappe.get_all(
		"Employee",
		filters={"company": EMPRESA, "employee_name": ["in", [n[0] for n in NOMES.values()]]},
		pluck="name",
	)
	for doctype in POR_COLABORADOR:
		_apagar(doctype, frappe.get_all(doctype, filters={"employee": ["in", pessoas]}, pluck="name"))
	trocas = frappe.get_all(
		"Troca de Escala Dia", filters={"employee": ["in", pessoas]}, pluck="parent", distinct=True
	)
	_apagar("Troca de Escala", list(set(trocas)))
	for doctype in POR_EMPRESA:
		_apagar(doctype, frappe.get_all(doctype, filters={"company": EMPRESA}, pluck="name"))
	atualizar_trava(EMPRESA)
	frappe.db.commit()
	print("Dados de ponto dos colaboradores de teste apagados (cadastros mantidos).")


# ------------------------------------------------------------------ chamadas pelo docker\teste.ps1 (Windows)
# O PowerShell 5.1 estraga aspas dentro de argumentos; o script passa os valores por variáveis de ambiente.


def _env(nome: str, padrao: str | None = None) -> str | None:
	import os

	valor = os.environ.get(nome, "").strip()
	return valor or padrao


def bater_env() -> None:
	bater(_env("CARGO"), _env("DATA"), _env("HORARIOS"))


def semana_env() -> None:
	semana(_env("CARGO"), _env("DATA"), _env("HORARIOS"), int(_env("DIAS", "5")))


def apurar_env() -> None:
	apurar(_env("CARGO"), _env("DATA"))
