"""Cobertura de faltas (engine/cobertura.py, docs/PRD-substituicoes.md CS-E1)."""

from datetime import date, datetime
from decimal import Decimal

from hrms_secullum_brasil.engine import cobertura as c

D = date(2026, 11, 20)
ABRIU = datetime(2026, 11, 20, 6, 0)


def test_cascata_pelo_tempo():
	assert c.nivel_devido(ABRIU, datetime(2026, 11, 20, 6, 14)) == c.UNIDADE
	assert c.nivel_devido(ABRIU, datetime(2026, 11, 20, 6, 15)) == c.REDE
	assert c.nivel_devido(ABRIU, datetime(2026, 11, 20, 6, 30)) == c.BANCO
	p = c.Parametros(t1=5, t2=10)
	assert c.nivel_devido(ABRIU, datetime(2026, 11, 20, 6, 6), p) == c.REDE
	assert c.proximo_nivel(c.UNIDADE) == c.REDE
	assert c.proximo_nivel(c.BANCO) is None
	assert c.niveis_ate(c.BANCO) == c.NIVEIS
	assert c.niveis_ate(c.UNIDADE) == (c.UNIDADE,)


def test_horario_de_envio_das_5_as_22():
	assert c.no_horario_de_envio(datetime(2026, 11, 20, 5, 0))
	assert c.no_horario_de_envio(datetime(2026, 11, 20, 21, 59))
	assert not c.no_horario_de_envio(datetime(2026, 11, 20, 22, 0))
	assert not c.no_horario_de_envio(datetime(2026, 11, 20, 4, 59))


def test_escolher_internos_sem_quebra_menos_horas_primeiro():
	cand = [
		{"employee": "A", "nome": "Ana", "sem_conflito": True, "minutos_semana": 900},
		{"employee": "B", "nome": "Bia", "sem_conflito": True, "minutos_semana": 300},
		{
			"employee": "C",
			"nome": "Caio",
			"sem_conflito": False,
			"minutos_semana": 0,
			"motivo": "interjornada",
		},
		{"employee": "D", "nome": "Davi", "sem_conflito": True, "minutos_semana": 300},
	]
	assert [x["employee"] for x in c.escolher_internos(cand, set())] == ["B", "D", "A"]
	assert [x["employee"] for x in c.escolher_internos(cand, {"B"}, c.Parametros(por_rodada=1))] == ["D"]
	assert [x["employee"] for x in c.bloqueados(cand, set())] == ["C"]
	assert c.bloqueados(cand, {"C"}) == []


def test_turno_inicio_fim_e_minutos():
	periodos = [(480, 600), (615, 780)]
	assert c.inicio_do_turno(D, periodos) == datetime(2026, 11, 20, 8, 0)
	assert c.fim_do_turno(D, periodos) == datetime(2026, 11, 20, 13, 0)
	assert c.minutos_do_turno(periodos) == 285
	assert c.texto_do_horario(periodos) == "08:00 às 10:00 e 10:15 às 13:00"


def test_primeiro_ganha():
	inicio = datetime(2026, 11, 20, 8, 0)
	antes = datetime(2026, 11, 20, 7, 0)
	assert c.motivo_para_nao_aceitar(c.ABERTA, inicio, antes, False) is None
	assert c.motivo_para_nao_aceitar(c.ABERTA, inicio, antes, True) == "a vaga já foi preenchida"
	assert c.motivo_para_nao_aceitar(c.PREENCHIDA, inicio, antes, False) == "a vaga já foi preenchida"
	assert c.motivo_para_nao_aceitar(c.CANCELADA, inicio, antes, False) == "a vaga foi cancelada"
	assert c.motivo_para_nao_aceitar(c.ABERTA, inicio, inicio, False) == "o turno já começou"
	assert c.vence_sem_ninguem(c.ABERTA, inicio, inicio)
	assert not c.vence_sem_ninguem(c.ABERTA, inicio, antes)
	assert not c.vence_sem_ninguem(c.PREENCHIDA, inicio, inicio)


def test_cnpj():
	assert c.cnpj_valido("11.222.333/0001-81")
	assert not c.cnpj_valido("11.222.333/0001-80")
	assert not c.cnpj_valido("11111111111111")
	assert not c.cnpj_valido(None)
	assert not c.cnpj_valido("123")


def _pr(**kw):
	base = {
		"situacao": c.APROVADO,
		"cref_validade": date(2027, 1, 1),
		"termo_versao": 2,
		"cnpj": "11222333000181",
		"conta": True,
	}
	return c.Prestador(**(base | kw))


def test_travas_do_prestador():
	assert c.travas_do_prestador(_pr(), D, 0, 2) == []
	assert c.travas_do_prestador(_pr(situacao=c.AGUARDANDO_APROVACAO), D, 0, 2) == [
		"cadastro aguardando aprovação"
	]
	assert c.travas_do_prestador(_pr(cref_validade=date(2026, 11, 19)), D, 0, 2) == [
		"CREF vencido ou sem validade"
	]
	assert c.travas_do_prestador(_pr(termo_versao=1), D, 0, 2) == [
		"termo de credenciamento não aceito na versão vigente"
	]
	assert c.travas_do_prestador(_pr(), D, 0, None) == [
		"termo de credenciamento não aceito na versão vigente"
	]
	assert c.travas_do_prestador(_pr(cnpj="1"), D, 0, 2) == ["CNPJ ausente ou inválido"]
	assert c.travas_do_prestador(_pr(conta=False), D, 0, 2) == ["sem conta bancária do CNPJ"]
	assert c.travas_do_prestador(_pr(colaborador_ativo=True), D, 0, 2) == [
		"é colaborador da rede (vai pela equipe interna)"
	]


def test_trava_de_frequencia_e_liberacao_do_rh():
	assert c.PADROES.max_plantoes_mes == 6
	assert c.travas_do_prestador(_pr(), D, 6, 2) == ["já tem 6 plantões no mês (limite 6)"]
	assert c.travas_do_prestador(_pr(), D, 5, 2) == []
	assert c.travas_do_prestador(_pr(liberado_no_mes="2026-11"), D, 6, 2) == []
	assert c.travas_do_prestador(_pr(liberado_no_mes="2026-10"), D, 6, 2) != []
	assert c.perto_do_limite(5)
	assert not c.perto_do_limite(4)


def test_limite_zero_e_sem_limite():
	sem = c.Parametros(max_plantoes_mes=0)
	assert c.travas_do_prestador(_pr(), D, 40, 2, sem) == []
	assert not c.perto_do_limite(0, sem)
	assert not c.perto_do_limite(40, sem)


def test_cref_vencendo():
	hoje = date(2026, 11, 11)
	assert c.cref_vencendo(date(2026, 11, 26), hoje)
	assert not c.cref_vencendo(date(2026, 11, 27), hoje)
	assert not c.cref_vencendo(date(2026, 11, 10), hoje)
	assert not c.cref_vencendo(None, hoje)


def test_valor_do_plantao_por_hora():
	assert c.valor_do_plantao(240, Decimal("30")) == Decimal("120.00")
	assert c.valor_do_plantao(250, Decimal("30")) == Decimal("125.00")
	assert c.valor_do_plantao(1, Decimal("25")) == Decimal("0.42")
	assert c.valor_do_plantao(-5, Decimal("30")) == Decimal("0.00")
	assert c.reais(Decimal("1234.5")) == "1.234,50"


def test_erros_do_cadastro():
	ok = {
		"nome": "Ana",
		"cpf": "529.982.247-25",
		"celular": "(27) 99999-0000",
		"cref_numero": "012345-G/ES",
		"cref_validade": date(2027, 1, 1),
		"razao_social": "Ana ME",
		"cnpj": "11.222.333/0001-81",
		"pix": "11222333000181",
		"foto_cref": "x",
		"comprovante_endereco": "y",
		"aceite": True,
	}
	hoje = date(2026, 11, 11)
	assert c.erros_do_cadastro(ok, hoje) == []
	ruim = ok | {"cpf": "1", "cnpj": "2", "celular": "12", "cref_validade": date(2026, 1, 1), "pix": ""}
	ruim |= {"foto_cref": None, "comprovante_endereco": None, "aceite": False, "nome": " "}
	erros = c.erros_do_cadastro(ruim, hoje)
	assert "Informe o nome." in erros
	assert "CPF inválido." in erros
	assert "CNPJ inválido." in erros
	assert "Celular inválido (com DDD)." in erros
	assert "O CREF está vencido." in erros
	assert "Informe a chave PIX ou banco, agência e conta do CNPJ." in erros
	assert "Envie a foto do CREF." in erros
	assert "Envie o comprovante de endereço." in erros
	assert "Leia e aceite o termo de credenciamento." in erros
	assert c.erros_do_cadastro(ok | {"pix": "", "banco": "001", "agencia": "1", "conta": "2"}, hoje) == []


def test_aviso_sem_batida_so_com_coleta_nova():
	inicio = datetime(2026, 11, 20, 5, 0)
	agora = datetime(2026, 11, 20, 5, 30)
	assert c.avisar_sem_batida(inicio, agora, datetime(2026, 11, 20, 5, 25), False)
	assert not c.avisar_sem_batida(inicio, agora, datetime(2026, 11, 20, 5, 10), False)  # coleta antiga
	assert not c.avisar_sem_batida(inicio, agora, None, False)
	assert not c.avisar_sem_batida(inicio, agora, datetime(2026, 11, 20, 5, 25), True)
	assert not c.avisar_sem_batida(
		inicio, datetime(2026, 11, 20, 5, 10), datetime(2026, 11, 20, 5, 10), False
	)


def test_textos():
	assert c.hhmm(1440) == "00:00"
	assert c.duracao(240) == "4 horas"
	assert c.duracao(60) == "1 hora"
	assert c.duracao(270) == "4h30"
