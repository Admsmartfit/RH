import json
from datetime import date

import pytest
import requests

from hrms_secullum_brasil.integrations.secullum.client import (
	ConfigSecullum,
	HttpSecullumClient,
	MemoryTokenStore,
)
from hrms_secullum_brasil.integrations.secullum.erros import (
	SecullumAuthError,
	SecullumHttpError,
	SecullumIndisponivelError,
	SecullumValidacaoError,
)

URL_AUTH = "https://autenticador.secullum.com.br"
URL_API = "https://pontowebintegracaoexterna.secullum.com.br/IntegracaoExterna/"
BANCO = "6f9619ff8b86d011b42d00c04fc964ff"


class Resp:
	def __init__(self, status=200, corpo=None, headers=None):
		self.status_code = status
		self.text = "" if corpo is None else corpo if isinstance(corpo, str) else json.dumps(corpo)
		self.headers = headers or {}

	def json(self):
		return json.loads(self.text)


def token(valor="tok-1", expires_in=3600):
	return Resp(200, {"access_token": valor, "token_type": "bearer", "expires_in": expires_in})


class FakeSession:
	"""Responde em ordem; cada item é uma Resp ou uma exceção a levantar."""

	def __init__(self, *respostas):
		self.respostas = list(respostas)
		self.pedidos = []

	def request(self, metodo, url, **kw):
		self.pedidos.append({"metodo": metodo, "url": url, **kw})
		resposta = self.respostas.pop(0)
		if isinstance(resposta, Exception):
			raise resposta
		return resposta


class Relogio:
	def __init__(self):
		self.agora = 1_000_000.0
		self.esperas = []

	def __call__(self):
		return self.agora

	def dormir(self, segundos):
		self.esperas.append(segundos)
		self.agora += segundos


def cliente(*respostas, max_tentativas=3, store=None):
	relogio = Relogio()
	registros = []
	sessao = FakeSession(*respostas)
	c = HttpSecullumClient(
		ConfigSecullum(URL_AUTH, URL_API, "rh@example.com", "s3nh4", BANCO, max_tentativas=max_tentativas),
		session=sessao,
		token_store=store or MemoryTokenStore(),
		registrar=registros.append,
		relogio=relogio,
		dormir=relogio.dormir,
	)
	return c, sessao, relogio, registros


class TestAutenticacao:
	def test_autentica_com_password_grant_e_client_id_3(self):
		c, sessao, _, _ = cliente(token(), Resp(200, []))
		c.listar_funcionarios()
		auth = sessao.pedidos[0]
		assert auth["metodo"] == "POST"
		assert auth["url"] == f"{URL_AUTH}/Token"
		assert auth["data"] == {
			"grant_type": "password",
			"username": "rh@example.com",
			"password": "s3nh4",
			"client_id": "3",
		}
		assert "Authorization" not in auth["headers"]

	def test_headers_da_api(self):
		c, sessao, _, _ = cliente(token("abc"), Resp(200, []))
		c.listar_funcionarios()
		api = sessao.pedidos[1]
		assert api["url"] == f"{URL_API}Funcionarios"
		assert api["headers"]["Authorization"] == "Bearer abc"
		assert api["headers"]["secullumidbancoselecionado"] == BANCO
		assert api["timeout"] == 30

	def test_token_em_cache_entre_chamadas(self):
		c, sessao, _, _ = cliente(token(), Resp(200, []), Resp(200, []))
		c.listar_funcionarios()
		c.listar_funcionarios()
		assert [p["url"].endswith("/Token") for p in sessao.pedidos] == [True, False, False]

	def test_token_expirado_e_renovado_antes_de_chamar(self):
		c, sessao, relogio, _ = cliente(token("t1", 3600), Resp(200, []), token("t2", 3600), Resp(200, []))
		c.listar_funcionarios()
		relogio.agora += 3600 - 30  # dentro da margem de renovação de 60s
		c.listar_funcionarios()
		assert sessao.pedidos[2]["url"].endswith("/Token")
		assert sessao.pedidos[3]["headers"]["Authorization"] == "Bearer t2"

	def test_sem_expires_in_usa_ttl_padrao(self):
		store = MemoryTokenStore()
		c, _, relogio, _ = cliente(Resp(200, {"access_token": "x"}), Resp(200, []), store=store)
		c.listar_funcionarios()
		_, expira_em = store.obter(f"{URL_AUTH}|rh@example.com")
		assert expira_em == relogio.agora + 3600

	def test_401_na_api_descarta_token_e_reautentica_uma_vez(self):
		c, sessao, _, _ = cliente(token("velho"), Resp(401, "expirado"), token("novo"), Resp(200, []))
		assert c.listar_funcionarios() == []
		assert sessao.pedidos[3]["headers"]["Authorization"] == "Bearer novo"

	def test_401_persistente_vira_erro_de_autenticacao(self):
		c, _, _, _ = cliente(token(), Resp(401), token(), Resp(401))
		with pytest.raises(SecullumAuthError):
			c.listar_funcionarios()

	def test_credenciais_recusadas(self):
		c, _, _, _ = cliente(Resp(400, {"error": "invalid_grant"}))
		with pytest.raises(SecullumAuthError):
			c.listar_funcionarios()

	def test_registro_de_auth_nao_contem_senha(self):
		c, _, _, registros = cliente(token(), Resp(200, []))
		c.listar_funcionarios()
		assert registros[0].servico == "auth"
		assert registros[0].payload is None
		assert "s3nh4" not in repr(registros)


class TestRetry:
	def test_429_respeita_retry_after(self):
		c, _, relogio, registros = cliente(token(), Resp(429, headers={"Retry-After": "7"}), Resp(200, []))
		assert c.listar_funcionarios() == []
		assert relogio.esperas == [7.0]
		assert registros[-1].tentativas == 2

	def test_500_repete_com_backoff_exponencial(self):
		c, _, relogio, _ = cliente(token(), Resp(500), Resp(502), Resp(200, [{"Cpf": "1"}]))
		assert c.listar_funcionarios() == [{"Cpf": "1"}]
		assert relogio.esperas == [1.0, 2.0]

	def test_500_esgota_tentativas(self):
		c, sessao, relogio, registros = cliente(token(), Resp(500), Resp(500), Resp(503))
		with pytest.raises(SecullumIndisponivelError, match="3 tentativa"):
			c.listar_funcionarios()
		assert len(sessao.pedidos) == 4  # token + 3 tentativas
		assert relogio.esperas == [1.0, 2.0]
		assert registros[-1].status_http == 503
		assert registros[-1].erro.startswith("HTTP 503")

	def test_timeout_e_falha_de_rede_sao_repetidos(self):
		c, _, _, _ = cliente(
			token(), requests.Timeout("lento"), requests.ConnectionError("caiu"), Resp(200, [])
		)
		assert c.listar_funcionarios() == []

	def test_timeout_persistente(self):
		c, _, _, registros = cliente(
			token(), requests.Timeout("a"), requests.Timeout("b"), requests.Timeout("c")
		)
		with pytest.raises(SecullumIndisponivelError, match="Timeout"):
			c.listar_funcionarios()
		assert registros[-1].status_http is None

	def test_400_nao_repete_e_traz_mensagens(self):
		erros = [{"Property": "NumeroPis", "Message": "PIS inválido."}]
		c, sessao, _, _ = cliente(token(), Resp(400, erros))
		with pytest.raises(SecullumValidacaoError) as exc:
			c.salvar_funcionario({"Cpf": "52998224725"})
		assert exc.value.erros == erros
		assert "NumeroPis: PIS inválido." in str(exc.value)
		assert len(sessao.pedidos) == 2

	def test_400_sem_json(self):
		c, _, _, _ = cliente(token(), Resp(400, "erro qualquer"))
		with pytest.raises(SecullumValidacaoError, match="erro qualquer"):
			c.salvar_funcao("Professor")

	def test_outros_4xx_nao_repetem(self):
		c, sessao, _, _ = cliente(token(), Resp(403, "proibido"))
		with pytest.raises(SecullumHttpError) as exc:
			c.listar_funcionarios()
		assert exc.value.status == 403
		assert len(sessao.pedidos) == 2

	def test_retry_after_invalido_usa_backoff(self):
		c, _, relogio, _ = cliente(token(), Resp(429, headers={"Retry-After": "amanhã"}), Resp(200, []))
		c.listar_funcionarios()
		assert relogio.esperas == [1.0]


class TestOperacoes:
	def test_salvar_funcionario_envia_json(self):
		c, sessao, _, registros = cliente(token(), Resp(200, "OK"))
		c.salvar_funcionario({"Cpf": "52998224725", "Nome": "Ana"})
		assert sessao.pedidos[1]["metodo"] == "POST"
		assert sessao.pedidos[1]["json"] == {"Cpf": "52998224725", "Nome": "Ana"}
		assert registros[-1].payload == {"Cpf": "52998224725", "Nome": "Ana"}

	def test_departamento_e_funcao(self):
		c, sessao, _, _ = cliente(token(), Resp(200), Resp(200))
		c.salvar_departamento("Pedagógico")
		c.salvar_funcao("Professor")
		assert sessao.pedidos[1]["url"].endswith("/Departamentos")
		assert sessao.pedidos[1]["json"] == {"Descricao": "Pedagógico"}
		assert sessao.pedidos[2]["url"].endswith("/Funcoes")

	@pytest.mark.parametrize(
		("resposta", "esperado"),
		[
			(Resp(200, [{"Id": 5, "Cpf": "52998224725"}]), {"Id": 5, "Cpf": "52998224725"}),
			(Resp(200, {"Id": 5}), {"Id": 5}),
			(Resp(200, []), None),
			(Resp(404, "não encontrado"), None),
		],
	)
	def test_buscar_por_cpf(self, resposta, esperado):
		c, sessao, _, _ = cliente(token(), resposta)
		assert c.buscar_funcionario_por_cpf("52998224725") == esperado
		assert sessao.pedidos[1]["params"] == {"cpf": "52998224725"}
		assert sessao.pedidos[1]["url"].endswith("/Funcionarios/Cpf")

	def test_listar_bancos_filtra_ponto_web_e_normaliza_guid(self):
		bancos = [
			{"id": 1, "identificador": "6F9619FF-8B86-D011-B42D-00C04FC964FF", "clienteId": "3", "nome": "A"},
			{"id": 2, "identificador": "x", "clienteId": "1", "nome": "B"},
		]
		c, sessao, _, _ = cliente(token("t"), Resp(200, bancos))
		resultado = c.listar_bancos()
		assert [b["identificador"] for b in resultado] == [BANCO]
		assert sessao.pedidos[1]["url"] == f"{URL_AUTH}/ContasSecullumExterno/ListarBancos/"
		assert sessao.pedidos[1]["headers"]["Authorization"] == "Bearer t"
		assert "secullumidbancoselecionado" not in sessao.pedidos[1]["headers"]

	def test_listar_bancos_com_erro(self):
		c, _, _, _ = cliente(token(), Resp(403))
		with pytest.raises(SecullumAuthError):
			c.listar_bancos()

	def test_listar_funcionarios_vazio(self):
		c, _, _, _ = cliente(token(), Resp(200, ""))
		assert c.listar_funcionarios() == []

	def test_session_padrao_e_registrador_padrao(self):
		c = HttpSecullumClient(ConfigSecullum(URL_AUTH, URL_API, "u", "s", BANCO))
		assert isinstance(c._session, requests.Session)
		c._registrar(None)  # não falha sem callback

	def test_listar_fonte_dados(self):
		c, sessao, _, _ = cliente(token(), Resp(200, [{"Id": 1}]), Resp(200, ""))
		assert c.listar_fonte_dados(date(2026, 10, 7), date(2026, 10, 14)) == [{"Id": 1}]
		assert sessao.pedidos[1]["url"].endswith("/FonteDados")
		assert sessao.pedidos[1]["params"] == {"dataInicio": "2026-10-07", "dataFim": "2026-10-14"}
		assert c.listar_fonte_dados(date(2026, 10, 7), date(2026, 10, 7)) == []
