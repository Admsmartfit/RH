"""Mapeamento puro Secullum → programa (docs/PRD-importacao-secullum.md, IS-05), com os aceites do PRD e as
amostras reais anonimizadas."""

import json
from datetime import date
from pathlib import Path

from hrms_secullum_brasil.integrations.secullum import importacao as imp

REAIS = Path(__file__).resolve().parent.parent / "fixtures" / "reais"


def carregar(nome):
	return json.loads((REAIS / f"{nome}.json").read_text(encoding="utf-8"))


def dia(indice, *horarios, **extra):
	base = {
		"DiaSemana": indice,
		"TipoDia": 0,
		"Neutro": False,
		"Fechamento": 0,
		"ToleranciaExtra": 5,
		"ToleranciaFalta": 5,
	}
	for n, (entrada, saida) in enumerate(zip(horarios[::2], horarios[1::2], strict=True), start=1):
		base[f"Entrada{n}"], base[f"Saida{n}"] = entrada, saida
	return {**base, **extra}


def horario(numero, dias, faixas=None, **extra):
	return {
		"Numero": numero,
		"Descricao": f"H{numero}",
		"Tipo": 0,
		"Dias": dias,
		"FaixasExtras": faixas or [],
		"Opcoes": {},
		**extra,
	}


SEMANA_44H = [dia(i, "08:00", "12:00", "13:00", "17:48") for i in range(5)] + [dia(5), dia(6)]


# ------------------------------------------------------------------ horários (aceites do PRD)


def test_horario_44h_seg_a_sex():
	p = imp.perfil_do_horario(horario(12, SEMANA_44H))
	assert (p.codigo, p.tipo) == ("SEC-12", imp.FIXA)
	assert [d.dia_semana for d in p.dias] == list(imp.DIAS_SEMANA)
	assert p.dias[0].periodos == [("08:00", "12:00"), ("13:00", "17:48")]
	assert p.dias[5].periodos == [] and p.dias[6].periodos == []
	assert (p.carga_semanal_minutos, p.divisor) == (2640, 220)
	assert p.problemas == [] and p.avisos == []
	assert p.tolerancia_por_marcacao == 5


def test_jornada_noturna_com_virada():
	dias = [dia(i, "22:00", "06:00", Fechamento=12) for i in range(5)] + [dia(5), dia(6)]
	p = imp.perfil_do_horario(horario(30, dias))
	assert p.hora_virada == 12
	assert p.dias[0].periodos == [("22:00", "06:00")]
	assert p.carga_semanal_minutos == 5 * 480


def test_quatro_periodos_avisa_e_importa_tres():
	dias = [dia(0, "06:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00")] + [
		dia(i) for i in range(1, 7)
	]
	p = imp.perfil_do_horario(horario(40, dias))
	assert len(p.dias[0].periodos) == 3
	assert any("4 períodos" in a for a in p.avisos)


def test_dia_neutro_com_horario_vira_dia_neutro_fora_da_carga():
	dias = [dia(i, "08:00", "12:00", "13:00", "17:00") for i in range(5)] + [
		dia(5, "08:00", "12:00", Neutro=True),
		dia(6),
	]
	p = imp.perfil_do_horario(horario(41, dias))
	assert (p.dias[5].periodos, p.dias[5].neutro) == ([("08:00", "12:00")], True)
	assert (p.dias[6].periodos, p.dias[6].neutro) == ([], False)
	assert not p.dias[0].neutro
	assert p.carga_semanal_minutos == 5 * 480
	assert p.divisor == 200


def test_todos_os_dias_neutros_e_horista():
	dias = [dia(i, "07:00", "10:00", Neutro=True) for i in range(7)]
	p = imp.perfil_do_horario(horario(9, dias, [{"DiaSemana": 2, "Faixas": [{"Ordem": 1, "Coluna": 100.0}]}]))
	assert (p.tipo, p.divisor, p.carga_semanal_minutos) == (imp.HORISTA, 1, 0)
	assert all(d.periodos == [] for d in p.dias)
	assert p.faixas_he == {"Domingo": 100.0}
	assert any("Horista" in a for a in p.avisos)


def test_intervalo_longo_liga_intervalo_estendido():
	dias = [dia(i, "06:00", "10:00", "17:00", "21:00") for i in range(5)] + [dia(5), dia(6)]
	p = imp.perfil_do_horario(horario(42, dias))
	assert p.permite_intervalo_estendido
	assert any("2h" in a for a in p.avisos)


def test_faixas_de_he_do_horario():
	faixas = [
		{"DiaSemana": 0, "Faixas": [{"Ordem": 1, "Coluna": 50.0}]},
		{"DiaSemana": 2, "Faixas": [{"Ordem": 1, "Coluna": 100.0}]},
		{"DiaSemana": 4, "Faixas": [{"Ordem": 1, "Coluna": 0.0}]},  # sem percentual
		{"DiaSemana": 9, "Faixas": [{"Ordem": 1, "Coluna": 50.0}]},  # noturno: fora do programa
	]
	p = imp.perfil_do_horario(horario(43, SEMANA_44H, faixas))
	assert p.faixas_he == {"Útil": 50.0, "Domingo": 100.0}


def test_divisores():
	assert [imp.divisor_da_carga(h * 60) for h in (44, 42, 40, 36, 30)] == [220, 210, 200, 180, 150]
	assert imp.divisor_da_carga(20 * 60) == 100
	assert imp.divisor_da_carga(1) == 1


def test_horario_sem_numero_e_dia_invalido():
	p = imp.perfil_do_horario({"Numero": None, "Dias": [dia(9, "08:00", "12:00")], "Tipo": 1})
	assert "Horário sem número no Secullum." in p.problemas
	assert any("DiaSemana 9" in x for x in p.problemas)
	assert any("tipo 1" in a for a in p.avisos)
	assert any("sem nenhum dia" in a for a in p.avisos)


def test_horario_com_hora_invalida():
	p = imp.perfil_do_horario(horario(44, [dia(0, "25:00", "26:00")] + [dia(i) for i in range(1, 7)]))
	assert p.problemas


def test_todos_os_horarios_reais_convertem():
	perfis = [imp.perfil_do_horario(h) for h in carregar("horarios")]
	assert len(perfis) == 64
	assert [p for p in perfis if p.problemas] == []
	horistas = [p for p in perfis if p.tipo == imp.HORISTA]
	assert {p.descricao for p in horistas} >= {"HORISTA GINASTICA", "HORISTA ESCOLA"}
	assert all(p.carga_semanal_minutos > 0 for p in perfis if p.tipo == imp.FIXA and p.descricao != "Ajuste")
	assert all(len(p.dias) == 7 for p in perfis)
	assert {p.hora_virada for p in perfis} == {0}


# ------------------------------------------------------------------ CCT sugerida


def test_sugestao_quando_os_horarios_concordam():
	faixas = [
		{"DiaSemana": 0, "Faixas": [{"Ordem": 1, "Coluna": 50.0}]},
		{"DiaSemana": 2, "Faixas": [{"Ordem": 1, "Coluna": 100.0}]},
	]
	perfis = [imp.perfil_do_horario(horario(n, SEMANA_44H, faixas)) for n in (1, 2)]
	s = imp.sugestao_de_cct(perfis)
	assert (s.tolerancia_por_marcacao, s.tolerancia_diaria) == (5, 10)
	assert s.faixas_he == {"Útil": 50.0, "Domingo": 100.0}
	assert s.avisos == []


def test_sugestao_com_divergencia_e_abaixo_do_minimo():
	f30 = [{"DiaSemana": 0, "Faixas": [{"Ordem": 1, "Coluna": 30.0}]}]
	f60 = [{"DiaSemana": 0, "Faixas": [{"Ordem": 1, "Coluna": 60.0}]}]
	perfis = [
		imp.perfil_do_horario(horario(1, SEMANA_44H, f30)),
		imp.perfil_do_horario(horario(2, SEMANA_44H, f30)),
		imp.perfil_do_horario(horario(3, SEMANA_44H, f60)),
	]
	s = imp.sugestao_de_cct(perfis)
	assert s.faixas_he["Útil"] == 50
	assert any("abaixo do mínimo" in a for a in s.avisos)
	assert any("diferentes" in a for a in s.avisos)
	assert imp.sugestao_de_cct([]).faixas_he == {}


def test_sugestao_com_os_horarios_reais():
	s = imp.sugestao_de_cct([imp.perfil_do_horario(h) for h in carregar("horarios")])
	assert s.faixas_he == {"Útil": 50.0, "Sábado": 50.0, "Domingo": 100.0, "Feriado": 100.0, "Folga": 100.0}
	assert s.tolerancia_por_marcacao == 5


# ------------------------------------------------------------------ empresa


def test_empresa_e_sigla():
	e = imp.empresa_do_secullum(
		{
			"Id": 3,
			"Nome": "ES FITNESS LTDA ME - VILA VELHA",
			"Documento": "23.620.822/0002-51",
			"TipoDocumento": 0,
			"Cidade": "VILA VELHA",
			"Uf": "ES",
			"CEI": "1",
		}
	)
	assert (e.documento, e.cidade, e.uf, e.cei) == ("23620822000251", "VILA VELHA", "ES", "1")
	assert e.problemas == []
	assert imp.sugerir_abbr(e.nome, set()) == "EFVV"
	assert imp.sugerir_abbr(e.nome, {"EFVV"}) == "EFVV2"
	assert imp.sugerir_abbr("LTDA", set()) == "EMP"


def test_empresa_com_problema():
	e = imp.empresa_do_secullum(
		{"Nome": "", "Documento": "123", "TipoDocumento": 0, "Cidade": {"Descricao": "SERRA"}}
	)
	assert e.cidade == "SERRA"
	assert "Empresa sem nome no Secullum." in e.problemas
	assert any("dígitos" in p for p in e.problemas)
	assert "Empresa sem CNPJ/CPF no Secullum." in imp.empresa_do_secullum({"Nome": "X"}).problemas


def test_empresas_reais():
	empresas = [imp.empresa_do_secullum(e) for e in carregar("empresas")]
	assert len(empresas) == 7 and all(not e.problemas for e in empresas)
	assert {e.uf for e in empresas} == {"ES", "PR"}


# ------------------------------------------------------------------ funcionário


def funcionario(**extra):
	base = {
		"Id": 10,
		"Nome": "Maria  da Silva",
		"Cpf": "529.982.247-25",
		"NumeroPis": "120.12345.67-2",
		"NumeroFolha": "0007",
		"Nascimento": "1995-09-11T00:00:00",
		"Masculino": False,
		"Admissao": "2023-03-01T00:00:00",
		"Demissao": None,
		"Empresa": {"Documento": "23620822000251"},
		"Horario": {"Numero": 12},
		"Departamento": {"Descricao": "SMART FIT VILA VELHA"},
		"Funcao": {"Descricao": "RECEPCIONISTA"},
		"Endereco": "Rua A",
		"Cidade": {"Descricao": "VILA VELHA"},
		"Uf": "ES",
	}
	return {**base, **extra}


def test_funcionario_ativo():
	c = imp.colaborador_do_secullum(funcionario())
	assert (c.first_name, c.last_name, c.nome) == ("Maria", "da Silva", "Maria da Silva")
	assert (c.cpf, c.pis, c.matricula) == ("52998224725", "12012345672", "0007")
	assert (c.nascimento, c.nascimento_ausente, c.genero) == (date(1995, 9, 11), False, "Female")
	assert (c.admissao, c.demissao, c.status) == (date(2023, 3, 1), None, "Active")
	assert (c.empresa_documento, c.horario_numero, c.departamento, c.funcao) == (
		"23620822000251",
		12,
		"SMART FIT VILA VELHA",
		"RECEPCIONISTA",
	)
	assert c.endereco == "Rua A, VILA VELHA, ES"
	assert c.problemas == [] and c.avisos == []


def test_pis_invalido_entra_sem_pis_e_celular_so_com_digitos():
	c = imp.colaborador_do_secullum(
		funcionario(NumeroPis="815975772782", Celular=f"27 99616{chr(0x2011)}6303")
	)
	assert (c.pis, c.celular, c.problemas) == (None, "27996166303", [])
	assert any("PIS inválido" in a and "2782" in a for a in c.avisos)


def test_funcionario_demitido_e_motivo():
	c = imp.colaborador_do_secullum(
		funcionario(Demissao="2026-05-16T00:00:00", MotivoDemissaoId=4, Masculino=True),
		{4: "PEDIDO DE DEMISSÃO"},
	)
	assert (c.status, c.demissao, c.motivo_demissao, c.genero) == (
		"Left",
		date(2026, 5, 16),
		"PEDIDO DE DEMISSÃO",
		"Male",
	)


def test_funcionario_sem_nascimento_entra_com_1900():
	c = imp.colaborador_do_secullum(funcionario(Nascimento=None))
	assert (c.nascimento, c.nascimento_ausente) == (date(1900, 1, 1), True)
	assert c.problemas == []
	assert any("01/01/1900" in a for a in c.avisos)


def test_funcionario_com_problemas():
	c = imp.colaborador_do_secullum(
		{"Id": None, "Nome": "", "Cpf": "111.111.111-11", "Empresa": {}, "Horario": {}}
	)
	for problema in (
		"Funcionário sem Id no Secullum.",
		"Funcionário sem nome.",
		"CPF inválido no Secullum.",
		"Funcionário sem data de admissão.",
		"Funcionário sem empresa.",
		"Funcionário sem horário.",
	):
		assert problema in c.problemas
	assert "Funcionário sem CPF no Secullum." in imp.colaborador_do_secullum(funcionario(Cpf=None)).problemas
	assert "Funcionário sem função (cargo)." in imp.colaborador_do_secullum(funcionario(Funcao=None)).avisos


def test_selecionar_vinculos_dos_ultimos_12_meses():
	lista = [
		funcionario(Id=1),
		funcionario(Id=2, Demissao="2026-01-10T00:00:00"),
		funcionario(Id=3, Demissao="2025-06-01T00:00:00"),
	]
	assert [f["Id"] for f in imp.selecionar_vinculos(lista, date(2026, 10, 19))] == [1, 2]


def test_funcionarios_reais():
	todos = carregar("funcionarios")
	colaboradores = [imp.colaborador_do_secullum(f) for f in todos]
	assert len(colaboradores) == 120
	assert [c.problemas for c in colaboradores if c.problemas] == []
	ativos = [c for c in colaboradores if c.status == "Active"]
	assert len(ativos) == 90
	assert sum(c.nascimento_ausente for c in ativos) > 0
	horarios = {h["Numero"] for h in carregar("horarios")}
	assert {c.horario_numero for c in colaboradores} <= horarios


# ------------------------------------------------------------------ estruturas


def test_hierarquia_com_estrutura_pai():
	estruturas = [
		{
			"Descricao": "Unidade",
			"EstruturaPaiDescricao": None,
			"Responsaveis": [{"Cpf": "111"}],
			"FuncionariosVinculados": [{"Cpf": "222"}],
		},
		{
			"Descricao": "Recepção",
			"EstruturaPaiDescricao": "Unidade",
			"Responsaveis": [{"Cpf": "222"}],
			"FuncionariosVinculados": [{"Cpf": "333"}, {"Cpf": "222"}],
		},
		{"Descricao": "Vazia", "Responsaveis": [], "FuncionariosVinculados": [{"Cpf": "444"}]},
	]
	chefes, avisos = imp.hierarquia_das_estruturas(estruturas)
	assert chefes == {"222": "111", "333": "222"}
	assert any("Vazia" in a for a in avisos)
	assert imp.hierarquia_das_estruturas([]) == ({}, [])


# ------------------------------------------------------------------ justificativas e afastamentos


def test_efeito_das_justificativas():
	casos = {
		"ATESTAD": imp.ATESTADO,
		"AUXDOEN": imp.INSS,
		"FERIAS": imp.FERIAS,
		"FÉRIAS": imp.FERIAS,
		"FALTA": imp.FALTA,
		"L-MATER": imp.ABONA,
		"RECESSO": imp.ABONA,
	}
	for nome, efeito in casos.items():
		assert imp.efeito_da_justificativa({"NomeAbreviado": nome}) == efeito, nome
	assert imp.efeito_da_justificativa({"NomeAbreviado": "XYZ", "LancarComoHorasFalta": True}) == imp.FALTA
	assert (
		imp.efeito_da_justificativa({"NomeAbreviado": "X", "NomeCompleto": "Afastado pelo INSS"}) == imp.INSS
	)


def test_justificativas_reais():
	efeitos = {j["NomeAbreviado"]: imp.efeito_da_justificativa(j) for j in carregar("justificativas")}
	assert efeitos["ATESTAD"] == imp.ATESTADO
	assert efeitos["FERIAS"] == efeitos["FÉRIAS"] == imp.FERIAS
	assert efeitos["FALTA"] == imp.FALTA
	assert set(efeitos.values()) <= set(imp.EFEITOS)


def test_afastamento():
	a = imp.afastamento_do_secullum(
		{
			"Id": 5,
			"Cpf": "529.982.247-25",
			"Inicio": "2026-08-10T00:00:00",
			"Fim": "2026-08-12T00:00:00",
			"JustificativaNome": "ATESTAD",
			"Motivo": "CID J11",
		},
		{"ATESTAD": imp.ATESTADO},
	)
	assert (a.chave, a.inicio, a.fim, a.efeito) == (
		"52998224725|2026-08-10|2026-08-12",
		date(2026, 8, 10),
		date(2026, 8, 12),
		imp.ATESTADO,
	)
	assert not hasattr(a, "motivo")  # texto livre não é importado (LGPD)
	assert a.problemas == []


def test_afastamento_com_problemas():
	a = imp.afastamento_do_secullum(
		{"Inicio": "2026-08-12", "Fim": "2026-08-10", "JustificativaNome": "NOVA"}, {}
	)
	assert "Afastamento sem CPF." in a.problemas
	assert "Afastamento com fim antes do início." in a.problemas
	assert any("NOVA" in p for p in a.problemas)
	assert "Afastamento sem data de início." in imp.afastamento_do_secullum({"Cpf": "1"}, {}).problemas


def test_afastamentos_reais():
	efeitos = {j["NomeAbreviado"]: imp.efeito_da_justificativa(j) for j in carregar("justificativas")}
	afastamentos = [imp.afastamento_do_secullum(a, efeitos) for a in carregar("afastamentos")]
	assert len(afastamentos) == 80
	assert [a.problemas for a in afastamentos if a.problemas] == []
	assert len({a.chave for a in afastamentos}) == len(afastamentos)


def test_data_secullum():
	assert imp.data_secullum("2023-03-01T00:00:00") == date(2023, 3, 1)
	assert imp.data_secullum(None) is None
