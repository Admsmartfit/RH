"""Importação dos cadastros do Secullum (docs/PRD-importacao-secullum.md, IS-06; Etapa 6), com o mock servindo as
amostras reais anonimizadas."""

import copy
from collections import Counter
from datetime import date, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.adaptador import abonos_do_dia
from hrms_secullum_brasil.configuracao_ponto.regras import regra_vigente_para
from hrms_secullum_brasil.engine.documentos import somente_digitos
from hrms_secullum_brasil.ingestion.importacao_secullum import SINDICATO_IMPORTADO, ImportacaoSecullum
from hrms_secullum_brasil.integrations.secullum.importacao import _sem_acento
from hrms_secullum_brasil.integrations.secullum.mock import REAIS_DIR, MockSecullumClient

HOJE = date(2026, 10, 19)


def contagem(resultado, passo):
	return resultado["contagem"].get(passo, {})


class TestImportacaoSecullum(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.client = MockSecullumClient(REAIS_DIR)
		cls.primeira = ImportacaoSecullum(client=cls.client, hoje=HOJE).executar()
		cls.cnpjs = {somente_digitos(e["Documento"]) for e in cls.client.cadastros["empresas"]}
		cls.usados = ImportacaoSecullum(client=cls.client, hoje=HOJE)._usados()
		cls.com_funcionarios = {c.empresa_documento for c in cls.usados}  # CCT e feriados só para essas

	def empresa(self, cnpj):
		return next(
			c
			for c in frappe.get_all("Company", fields=["name", "tax_id", "abbr", "uf", "municipio"])
			if somente_digitos(c.tax_id) == cnpj
		)

	def test_primeira_importacao_cria_os_cadastros(self):
		self.assertEqual(contagem(self.primeira, "Empresas"), {"Criado": 7})
		self.assertEqual(sum(contagem(self.primeira, "Funções").values()), 17)
		self.assertEqual(contagem(self.primeira, "Departamentos").get("Criado"), 6)
		self.assertEqual(contagem(self.primeira, "Horários").get("Criado"), 61)
		self.assertNotIn("Erro", str(self.primeira["contagem"]))

	def test_empresas_com_cnpj_uf_e_municipio(self):
		for e in self.client.cadastros["empresas"]:
			c = self.empresa(somente_digitos(e["Documento"]))
			self.assertEqual(c.uf, e["Uf"])
			self.assertEqual(c.municipio, e["Cidade"].title())
			self.assertTrue(c.abbr)
			self.assertEqual(frappe.db.get_value("Company", c.name, "default_currency"), "BRL")

	def test_funcoes_viram_cargos(self):
		usadas = {
			f["Funcao"]["Descricao"] for f in self.client.listar_funcionarios() if not f.get("Demissao")
		}
		for descricao in usadas:
			self.assertTrue(frappe.db.exists("Designation", descricao), descricao)

	def test_departamentos_por_empresa(self):
		for f in self.client.listar_funcionarios():
			if f.get("Demissao"):
				continue
			c = self.empresa(somente_digitos(f["Empresa"]["Documento"]))
			nome = f"{f['Departamento']['Descricao']} - {c.abbr}"
			self.assertEqual(frappe.db.get_value("Department", nome, "company"), c.name)

	def test_horarios_viram_perfis_da_empresa(self):
		horista = frappe.get_all(
			"Perfil de Jornada",
			filters={"numero_horario_secullum": 9},
			fields=["name", "tipo", "divisor", "company"],
		)
		self.assertTrue(horista)
		self.assertTrue(all(p.tipo == "Horista" and p.divisor == 1 for p in horista))
		self.assertEqual(frappe.get_all("Perfil Jornada Dia", filters={"parent": horista[0].name}), [])
		fixo = frappe.get_doc(
			"Perfil de Jornada",
			frappe.get_all(
				"Perfil de Jornada",
				filters={"tipo": "Fixa", "numero_horario_secullum": ["is", "set"]},
				pluck="name",
				limit=1,
			)[0],
		)
		self.assertEqual(len(fixo.dias), 7)
		self.assertTrue(fixo.carga_semanal_minutos > 0)
		self.assertIn(fixo.company, {self.empresa(c).name for c in self.cnpjs})

	def test_log_da_importacao(self):
		linhas = frappe.get_all(
			"Log de Importacao Secullum",
			filters={"execucao": self.primeira["execucao"]},
			fields=["passo", "resultado", "referencia_doctype", "referencia_name"],
		)
		self.assertEqual(len(linhas), len(self.primeira["linhas"]))
		empresa = next(x for x in linhas if x.passo == "Empresas")
		self.assertEqual((empresa.resultado, empresa.referencia_doctype), ("Criado", "Company"))

	def test_segunda_importacao_nao_muda_nada(self):
		segunda = ImportacaoSecullum(client=self.client, hoje=HOJE).executar()
		resultados = Counter(linha["resultado"] for linha in segunda["linhas"])
		mudaram = [
			(x["passo"], x["chave"], x["mensagem"])
			for x in segunda["linhas"]
			if x["resultado"] == "Atualizado"
		]
		self.assertEqual(set(resultados), {"Sem mudança", "Ignorado", "Aviso"}, mudaram[:5])
		self.assertEqual(
			{x["passo"] for x in segunda["linhas"] if x["resultado"] == "Aviso"}, {"Feriados", "Estruturas"}
		)
		self.assertEqual(frappe.db.count("Company", {"tax_id": ["in", list(self.cnpjs)]}), 7)

	def test_simular_nao_grava(self):
		antes = (frappe.db.count("Perfil de Jornada"), frappe.db.count("Log de Importacao Secullum"))
		client = MockSecullumClient(REAIS_DIR)
		client.cadastros["horarios"][0]["Dias"][0]["Entrada1"] = "07:00"
		simulacao = ImportacaoSecullum(client=client, hoje=HOJE + timedelta(days=5), simular=True).executar()
		self.assertTrue(simulacao["simulacao"])
		self.assertEqual(
			(frappe.db.count("Perfil de Jornada"), frappe.db.count("Log de Importacao Secullum")), antes
		)

	def test_horario_alterado_abre_nova_versao(self):
		client = MockSecullumClient(REAIS_DIR)
		horario = next(h for h in client.cadastros["horarios"] if h["Numero"] == 5)
		horario["Dias"][0]["Entrada1"] = "07:30"
		depois = HOJE + timedelta(days=10)
		resultado = ImportacaoSecullum(client=client, hoje=depois).executar(["horarios"])
		linha = next(x for x in resultado["linhas"] if x["chave"] == "SEC-5")
		self.assertEqual(linha["resultado"], "Atualizado")
		versoes = frappe.get_all(
			"Perfil de Jornada",
			filters={"codigo": "SEC-5"},
			fields=["vigencia_inicio", "vigencia_fim"],
			order_by="vigencia_inicio",
		)
		self.assertEqual(len(versoes), 2)
		self.assertEqual(versoes[0].vigencia_fim, depois - timedelta(days=1))
		self.assertEqual(versoes[1].vigencia_inicio, depois)

	def test_registro_com_erro_nao_para_os_outros(self):
		client = MockSecullumClient(REAIS_DIR)
		ruim = copy.deepcopy(client.cadastros["empresas"][0])
		ruim.update({"Documento": "123", "Nome": "Empresa Quebrada"})
		client.cadastros["empresas"].append(ruim)
		resultado = ImportacaoSecullum(client=client, hoje=HOJE).executar(["empresas"])
		self.assertEqual(contagem(resultado, "Empresas").get("Erro"), 1)
		self.assertEqual(contagem(resultado, "Empresas").get("Sem mudança"), 7)

	def test_cct_padrao_por_empresa(self):
		self.assertEqual(contagem(self.primeira, "CCT padrão"), {"Criado": len(self.com_funcionarios)})
		for cnpj in self.com_funcionarios:
			empresa = self.empresa(cnpj)
			cct = frappe.get_doc(
				"Regra Sindical CCT", {"company": empresa.name, "sindicato": SINDICATO_IMPORTADO}
			)
			self.assertEqual((cct.tolerancia_por_marcacao, cct.uf), (5, empresa.uf))
			self.assertEqual(
				{f.tipo_dia: f.percentual for f in cct.faixas_hora_extra},
				{
					"Útil": 50,
					"Sábado": 50,
					"Domingo": 100,
					"Feriado": 100,
					"Folga": 100,
					"Folga compensada": 50,
				},
			)
			admissoes = [c.admissao for c in self.usados if c.empresa_documento == cnpj and c.admissao]
			self.assertEqual(cct.vigencia_inicio, min(admissoes))

	def test_nenhum_funcionario_fica_sem_cct(self):
		for c in self.usados:
			emp = frappe._dict(
				name=c.nome,
				company=self.empresa(c.empresa_documento).name,
				designation=c.funcao,
				regra_cct=None,
			)
			self.assertIsNotNone(regra_vigente_para(emp, c.admissao), c.nome)

	def test_empresa_com_cct_do_programa_nao_ganha_outra(self):
		cnpj = sorted(self.com_funcionarios)[0]
		empresa = self.empresa(cnpj)
		frappe.db.savepoint("cct_do_rh")
		do_rh = frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": empresa.name,
				"sindicato": "Sindicato do Comércio",
				"vigencia_inicio": "2020-01-01",
			}
		).insert()
		importacao = ImportacaoSecullum(client=self.client, hoje=HOJE)
		resultado = importacao.executar(["cct"])
		linha = next(x for x in resultado["linhas"] if x["chave"] == empresa.name)
		self.assertEqual((linha["resultado"], linha["nome"]), ("Ignorado", do_rh.name))
		self.assertEqual(importacao.cct_por_documento[cnpj], do_rh.name)
		frappe.db.rollback(save_point="cct_do_rh")

	def test_feriados_das_empresas(self):
		self.assertEqual(contagem(self.primeira, "Feriados").get("Criado"), len(self.com_funcionarios))
		for cnpj in self.com_funcionarios:
			empresa = self.empresa(cnpj)
			lista = frappe.db.get_value("Company", empresa.name, "holiday_list_ponto")
			datas = set(frappe.get_all("Holiday", filters={"parent": lista}, pluck="holiday_date"))
			self.assertIn(date(2026, 12, 25), datas)
			self.assertIn(date(2027, 1, 1), datas)
		avisos = [
			x for x in self.primeira["linhas"] if x["passo"] == "Feriados" and x["resultado"] == "Aviso"
		]
		self.assertEqual(len(avisos), len(self.com_funcionarios))
		self.assertTrue(any("Vila Velha/ES" in x["mensagem"] for x in avisos))

	# ------------------------------------------------------------------ Etapa 8: funcionários e estruturas

	def isolar(self):
		"""Teste que muda dados do Secullum desfaz tudo no fim (os outros testes esperam a primeira importação)."""
		frappe.db.savepoint("teste_isolado")
		self.addCleanup(frappe.db.rollback, save_point="teste_isolado")

	def colaborador(self, id_secullum):
		return frappe.get_doc("Employee", {"id_secullum": str(id_secullum)})

	def test_funcionarios_importados(self):
		self.assertEqual(contagem(self.primeira, "Funcionários"), {"Criado": len(self.usados)})
		for c in self.usados:
			emp = self.colaborador(c.id_secullum)
			empresa = self.empresa(c.empresa_documento)
			self.assertEqual((emp.cpf, emp.company), (c.cpf, empresa.name))
			# o banco compara sem acento: reaproveita um cargo já cadastrado com acento (ex.: "Educação Física")
			self.assertEqual(_sem_acento(emp.designation).lower(), _sem_acento(c.funcao).lower())
			self.assertEqual(emp.department.lower(), f"{c.departamento} - {empresa.abbr}".lower())
			self.assertEqual(getdate(emp.date_of_joining), c.admissao)
			self.assertEqual(emp.status, "Left" if c.demissao else "Active")
			self.assertEqual(
				frappe.db.get_value("Regra Sindical CCT", emp.regra_cct, ["company", "sindicato"]),
				(empresa.name, SINDICATO_IMPORTADO),
			)
			perfil = frappe.db.get_value("Perfil de Jornada", emp.perfil_jornada, ["codigo", "company"])
			self.assertTrue(perfil[0].startswith(f"SEC-{c.horario_numero}"))
			self.assertEqual(perfil[1], empresa.name)
			self.assertEqual(emp.create_user_permission, 0)

	def test_demitido_com_data_e_motivo(self):
		c = next(x for x in self.usados if x.demissao and x.motivo_demissao)
		emp = self.colaborador(c.id_secullum)
		self.assertEqual(
			(getdate(emp.relieving_date), emp.reason_for_leaving), (c.demissao, c.motivo_demissao)
		)

	def test_horista_entra_como_horista(self):
		c = next(x for x in self.usados if x.horario_numero == 9)
		self.assertEqual(self.colaborador(c.id_secullum).tipo_remuneracao, "Horista")
		perfis = ImportacaoSecullum(client=self.client, hoje=HOJE).perfis
		outro = next(x for x in self.usados if perfis[x.horario_numero].tipo == "Fixa")
		self.assertEqual(self.colaborador(outro.id_secullum).tipo_remuneracao, "Mensalista")

	def test_cargo_de_horista_ganha_jornada_fragmentada_na_cct(self):
		# CP-06 (PRD do cartão ponto): dois turnos no dia sem inconsistência de intervalo maior que 2h
		c = next(x for x in self.usados if x.horario_numero == 9 and x.funcao)
		emp = self.colaborador(c.id_secullum)
		cct = frappe.get_doc("Regra Sindical CCT", {"company": emp.company, "sindicato": SINDICATO_IMPORTADO})
		linha = next(p for p in cct.parametros_cargo if p.designation == emp.designation)
		self.assertEqual(linha.jornada_fragmentada, 1)
		log = frappe.get_all(
			"Log de Importacao Secullum",
			filters={
				"passo": "CCT padrão",
				"referencia_name": cct.name,
				"mensagem": ["like", "%Jornada fragmentada%"],
			},
		)
		self.assertTrue(log)

	def test_jornada_fragmentada_desligada_pelo_rh_fica(self):
		c = next(x for x in self.usados if x.horario_numero == 9 and x.funcao)
		emp = self.colaborador(c.id_secullum)
		nome = frappe.db.get_value(
			"Regra Sindical CCT", {"company": emp.company, "sindicato": SINDICATO_IMPORTADO}
		)
		frappe.db.set_value(
			"Regra CCT Parametro Cargo",
			{"parent": nome, "designation": emp.designation},
			"jornada_fragmentada",
			0,
		)
		ImportacaoSecullum(client=self.client, hoje=HOJE).executar(["cct"])
		cct = frappe.get_doc("Regra Sindical CCT", nome)
		linhas = [p for p in cct.parametros_cargo if p.designation == emp.designation]
		self.assertEqual([p.jornada_fragmentada for p in linhas], [0])

	def test_mesmo_cpf_em_duas_empresas_sao_dois_colaboradores(self):
		repetidos = Counter(c.cpf for c in self.usados)
		cpf = next(k for k, n in repetidos.items() if n > 1)
		self.assertEqual(frappe.db.count("Employee", {"cpf": cpf}), 2)

	def test_nascimento_ausente_abre_inconsistencia(self):
		c = next(x for x in self.usados if x.nascimento_ausente)
		emp = self.colaborador(c.id_secullum)
		self.assertEqual(getdate(emp.date_of_birth), date(1900, 1, 1))
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{"employee": emp.name, "tipo": "nascimento_ausente", "status": ["!=", "Resolvida"]},
			)
		)
		com_data = next(x for x in self.usados if not x.nascimento_ausente)
		self.assertFalse(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{"employee": self.colaborador(com_data.id_secullum).name, "tipo": "nascimento_ausente"},
			)
		)

	def test_troca_de_cargo_no_secullum_chega_na_importacao(self):
		self.isolar()
		client = MockSecullumClient(REAIS_DIR)
		f = next(x for x in client.funcionarios.values() if not x.get("Demissao"))
		outro = next(
			x["Funcao"]
			for x in client.funcionarios.values()
			if x["Funcao"]["Descricao"] != f["Funcao"]["Descricao"]
		)
		f["Funcao"] = dict(outro)
		resultado = ImportacaoSecullum(client=client, hoje=HOJE).executar(["funcionarios"])
		linha = next(x for x in resultado["linhas"] if x["chave"].startswith(f"{f['Id']} - "))
		self.assertEqual(linha["resultado"], "Atualizado")
		self.assertEqual(self.colaborador(f["Id"]).designation.lower(), outro["Descricao"].lower())
		outras = Counter(x["resultado"] for x in resultado["linhas"] if x is not linha)
		self.assertEqual(set(outras), {"Sem mudança"})

	def test_cpf_invalido_vira_erro_e_os_outros_entram(self):
		self.isolar()
		client = MockSecullumClient(REAIS_DIR)
		ruim = copy.deepcopy(next(x for x in client.funcionarios.values() if not x.get("Demissao")))
		ruim.update({"Id": 999001, "Cpf": "111.111.111-11", "Nome": "Pessoa Cpf Ruim"})
		client.funcionarios[f"id:{ruim['Id']}"] = ruim
		resultado = ImportacaoSecullum(client=client, hoje=HOJE).executar(["funcionarios"])
		self.assertEqual(contagem(resultado, "Funcionários").get("Erro"), 1)
		self.assertEqual(contagem(resultado, "Funcionários").get("Sem mudança"), len(self.usados))
		self.assertFalse(frappe.db.exists("Employee", {"id_secullum": "999001"}))

	def test_sem_estruturas_avisa_para_definir_os_chefes(self):
		linhas = [x for x in self.primeira["linhas"] if x["passo"] == "Estruturas"]
		self.assertEqual([x["resultado"] for x in linhas], ["Aviso"])

	def test_estrutura_define_o_chefe_e_cria_o_usuario_do_gestor(self):
		self.isolar()
		client = MockSecullumClient(REAIS_DIR)
		ativos = [x for x in client.funcionarios.values() if not x.get("Demissao")]
		chefe, equipe = ativos[0], ativos[1:3]
		email = f"gestor-{frappe.generate_hash(length=6)}@example.com"
		chefe["Email"] = email
		client.estruturas = [
			{
				"Descricao": "Loja Centro",
				"Responsaveis": [{"Cpf": chefe["Cpf"]}],
				"FuncionariosVinculados": [{"Cpf": x["Cpf"]} for x in equipe],
			}
		]
		resultado = ImportacaoSecullum(client=client, hoje=HOJE).executar(["funcionarios", "estruturas"])
		self.assertNotIn("Erro", contagem(resultado, "Estruturas"))
		emp_chefe = self.colaborador(chefe["Id"])
		for x in equipe:
			self.assertEqual(self.colaborador(x["Id"]).reports_to, emp_chefe.name)
		self.assertEqual(emp_chefe.user_id, email)
		self.assertIn("Gestor Ponto", frappe.get_roles(email))
		self.assertEqual(frappe.db.get_value("User", email, "send_welcome_email"), 0)

	# ------------------------------------------------------------------ Etapa 9: justificativas, afastamentos, relógios

	def afastamento_que_abona(self):
		return frappe.get_doc(
			"Afastamento Secullum",
			frappe.get_all(
				"Afastamento Secullum",
				filters={"efeito": ["!=", "Falta"], "removido_no_secullum": 0},
				pluck="name",
				order_by="inicio desc",
				limit=1,
			)[0],
		)

	def test_justificativas_com_efeito_sugerido(self):
		self.assertEqual(
			contagem(self.primeira, "Justificativas"),
			{"Criado": len(self.client.cadastros["justificativas"])},
		)
		efeitos = dict(
			frappe.get_all("Justificativa Secullum", fields=["nome_abreviado", "efeito"], as_list=True)
		)
		self.assertEqual(efeitos["ATESTAD"], "Atestado")
		self.assertIn("Falta", efeitos.values())

	def test_afastamentos_do_vinculo_importado(self):
		linhas = [x for x in self.primeira["linhas"] if x["passo"] == "Afastamentos"]
		self.assertNotIn(
			"Erro", {x["resultado"] for x in linhas}, [x for x in linhas if x["resultado"] == "Erro"][:3]
		)
		criados = [x for x in linhas if x["resultado"] == "Criado"]
		self.assertTrue(criados)
		self.assertEqual(frappe.db.count("Afastamento Secullum"), len(criados))
		for af in frappe.get_all("Afastamento Secullum", fields=["employee", "inicio", "fim"]):
			emp = frappe.db.get_value(
				"Employee", af.employee, ["date_of_joining", "relieving_date"], as_dict=True
			)
			self.assertLessEqual(getdate(emp.date_of_joining), getdate(af.fim))
			self.assertTrue(not emp.relieving_date or getdate(emp.relieving_date) >= getdate(af.inicio))

	def test_afastamento_abona_o_dia_e_falta_nao(self):
		self.isolar()
		af = self.afastamento_que_abona()
		self.assertIn(af.name, abonos_do_dia(af.employee, getdate(af.inicio)))
		self.assertNotIn(af.name, abonos_do_dia(af.employee, getdate(af.inicio) - timedelta(days=1)))
		justificativa = frappe.get_doc("Justificativa Secullum", af.justificativa)
		justificativa.efeito = "Falta"
		justificativa.save()
		self.assertEqual(frappe.db.get_value("Afastamento Secullum", af.name, "efeito"), "Falta")
		self.assertNotIn(af.name, abonos_do_dia(af.employee, getdate(af.inicio)))

	def test_afastamento_apagado_no_secullum_deixa_de_valer(self):
		self.isolar()
		af = self.afastamento_que_abona()
		client = MockSecullumClient(REAIS_DIR)
		client.cadastros["afastamentos"] = [
			a for a in client.cadastros["afastamentos"] if f"id:{a.get('Id')}" != af.chave
		]
		resultado = ImportacaoSecullum(client=client, hoje=HOJE).executar(["afastamentos"])
		linha = next(x for x in resultado["linhas"] if x["chave"] == af.chave)
		self.assertEqual(linha["resultado"], "Atualizado")
		self.assertEqual(frappe.db.get_value("Afastamento Secullum", af.name, "removido_no_secullum"), 1)
		self.assertNotIn(af.name, abonos_do_dia(af.employee, getdate(af.inicio)))

	def test_afastamento_alterado_reapura_os_dias_apurados(self):
		self.isolar()
		af = self.afastamento_que_abona()
		frappe.get_doc(
			{"doctype": "Apuracao Diaria", "employee": af.employee, "data": af.inicio, "status": "Apurado"}
		).db_insert()
		client = MockSecullumClient(REAIS_DIR)
		bruto = next(a for a in client.cadastros["afastamentos"] if f"id:{a.get('Id')}" == af.chave)
		bruto["Fim"] = f"{getdate(af.fim) + timedelta(days=2)}T00:00:00"
		ImportacaoSecullum(client=client, hoje=HOJE).executar(["afastamentos"])
		self.assertEqual(
			getdate(frappe.db.get_value("Afastamento Secullum", af.name, "fim")),
			getdate(af.fim) + timedelta(days=2),
		)
		self.assertTrue(
			frappe.db.exists(
				"Reapuracao Pendente", {"employee": af.employee, "data": af.inicio, "status": "Pendente"}
			)
		)

	def test_equipamentos(self):
		self.assertEqual(
			contagem(self.primeira, "Equipamentos"), {"Criado": len(self.client.cadastros["equipamentos"])}
		)
		e = self.client.cadastros["equipamentos"][0]
		self.assertEqual(
			frappe.db.get_value("Equipamento Secullum", str(e["Id"]), "descricao"), e["Descricao"]
		)
