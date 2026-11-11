"""Ajuda Nahel: leitura dos guias, busca sem IA e integridade do catálogo (docs/PRD-ajuda-nahel.md, NH-E1/NH-E2)."""

import json
import re
from pathlib import Path

import pytest

from hrms_secullum_brasil.engine import nahel as n

APP = Path(__file__).resolve().parents[2]
RAIZ = APP.parent
GUIAS = n.carregar(APP / "nahel" / "guias")
# DocTypes do Frappe/ERPNext/HRMS que os guias podem citar
CORE = {"User", "Employee", "Company", "Holiday List", "Designation", "Email Account", "Leave Application"}

MINIMO = """---
id: teste
titulo: Conectar o WhatsApp
publico: RH, TI
tema: WhatsApp
palavras_chave: evolution, chip
telas: escalas
---
## Objetivo
Ligar o **chip**.

## Pré-requisitos
- Número de teste {{verificar:whatsapp_numero_teste}}

## Passo a passo
### Abrir a configuração
- O que fazer: preencha a **URL**
  e salve.
- Onde acessar: [[desk:Configuracao Apuracao|Configuração]]

### Testar
- O que fazer: clique em **Enviar**.
- Onde acessar: [[painel:escalas]]

## Como testar
- Ação: envie.
- Resultado esperado: chega.
"""


def _guia(**trocas):
	texto = MINIMO
	for antes, depois in trocas.items():
		texto = texto.replace(antes.replace("_", " "), depois)
	return n.ler_guia(texto, "teste.md")


# ------------------------------------------------------------------ leitura


def test_le_o_guia_com_secoes_trechos_e_passos():
	g = _guia()
	assert (g.id, g.titulo, g.publico, g.telas) == (
		"teste",
		"Conectar o WhatsApp",
		("RH", "TI"),
		("escalas",),
	)
	assert [p.chave for p in g.passos] == ["abrir-a-configuracao", "testar"]
	fazer = g.passos[0].o_que_fazer
	assert [t.tipo for t in fazer] == ["texto", "negrito", "texto"]
	assert fazer[2].valor == " e salve."  # continuação na linha seguinte
	link = g.passos[0].onde[0]
	assert (link.tipo, link.destino, link.alvo, link.valor) == (
		"link",
		"desk",
		"Configuracao Apuracao",
		"Configuração",
	)
	assert g.passos[1].onde[0].valor == "escalas"  # sem rótulo: o próprio alvo
	assert g.verificacoes() == ["whatsapp_numero_teste"]
	assert len(g.links()) == 2


@pytest.mark.parametrize(
	("trocar", "motivo"),
	[
		(("---\nid: teste", "id: teste"), "cabeçalho"),
		(("publico: RH, TI", "publico: Todos"), "público inválido"),
		(("titulo: Conectar o WhatsApp\n", ""), "sem titulo"),
		(("## Como testar", "## Outra"), "falta a seção Como testar"),
		(("- Resultado esperado: chega.", ""), "Ação e Resultado"),
		(("- O que fazer: clique em **Enviar**.", ""), 'sem "O que fazer"'),
		(("whatsapp_numero_teste", "nao_existe"), "verificação desconhecida"),
		(("### Testar", "### Abrir a configuração"), "mesmo nome"),
		(("Ligar o **chip**.", ""), "objetivo vazio"),
	],
)
def test_erros_de_formato(trocar, motivo):
	with pytest.raises(ValueError, match=motivo):
		n.ler_guia(MINIMO.replace(*trocar), "teste.md")


def test_erros_de_estrutura():
	with pytest.raises(ValueError, match="sem o ---"):
		n.ler_guia("---\nid: x\n", "x.md")
	sem_passos = MINIMO.split("### Abrir")[0] + "## Como testar\n- Ação: a\n- Resultado esperado: b\n"
	with pytest.raises(ValueError, match="nenhum passo"):
		n.ler_guia(sem_passos, "x.md")


def test_carregar_recusa_id_repetido(tmp_path):
	(tmp_path / "a.md").write_text(MINIMO, encoding="utf8")
	(tmp_path / "b.md").write_text(MINIMO, encoding="utf8")
	with pytest.raises(ValueError, match="ids repetidos"):
		n.carregar(tmp_path)


# ------------------------------------------------------------------ busca


def ids(r, i=0):
	return r["topicos"][i]["guias"]


def test_normalizacao_sinonimos_e_palavras_vazias():
	assert n.termos("Como eu configuro o Zap?") == ["config", "whatsa"]
	assert n.termos("Relógio de PONTO") == ["ponto"]
	assert n.sem_acento("Configuração") == "Configuracao"


def test_varios_assuntos_numa_frase():
	assert n.dividir_topicos("configurar adicional de risco e testar webhook whatsapp") == [
		"configurar adicional de risco",
		"testar webhook whatsapp",
	]
	assert n.dividir_topicos("secullum, depois folha") == ["secullum", "folha"]
	assert n.dividir_topicos("whatsapp e testar") == ["whatsapp testar"]  # "testar" sozinho junta no anterior
	assert n.dividir_topicos("secullum e liberar") == ["secullum liberar"]
	assert n.dividir_topicos("") == []


def test_busca_do_exemplo_do_rh_traz_um_guia_por_assunto():
	r = n.buscar(GUIAS, "configurar adicional de risco e testar webhook whatsapp", ["RH", "TI"])
	assert not r["fora_do_escopo"]
	assert ids(r, 0)[0] == "adicional-risco"
	assert "whatsapp-conectar" in ids(r, 1)


@pytest.mark.parametrize(
	("texto", "esperado"),
	[
		("Como configuro a integração do Secullum?", "secullum-conectar"),
		("liberar o zap numa unidade", "whatsapp-liberar-unidade"),
		("procurar substituto quando alguém faltou", "cobertura-falta"),
		("aprovar personal no banco de talentos", "talentos-cadastro"),
		("ativar 5x2", "regime-5x2"),
		("criar turno padrão", "turno-padrao"),
		("lançar atestado", "lancar-ausencia"),
		("ligar o docker", "ambiente-ligar"),
	],
)
def test_buscas_comuns(texto, esperado):
	assert ids(n.buscar(GUIAS, texto, n.PUBLICOS))[0] == esperado


def test_fora_do_escopo_e_sugestoes():
	r = n.buscar(GUIAS, "receita de bolo de cenoura", ["RH"])
	assert r["fora_do_escopo"]
	assert r["mensagem"] == n.MENSAGEM_FORA
	assert len(r["sugestoes"]) == 3
	assert n.buscar(GUIAS, "", ["RH"])["topicos"] == []


def test_tema_amplo_devolve_a_lista_do_tema():
	r = n.buscar(GUIAS, "whatsapp", ["RH", "TI"])
	assert r["topicos"][0]["amplo"]
	assert r["topicos"][0]["tema"] == "WhatsApp"
	assert len(ids(r)) >= 4


def test_publico_nunca_ve_guia_de_outro():
	r = n.buscar(GUIAS, "ligar o docker", ["Gestor"])
	assert "ambiente-ligar" not in [i for t in r["topicos"] for i in t["guias"]]
	assert all("Gestor" in g.publico for g in n.visiveis(GUIAS, ["Gestor"]))


def test_publicos_dos_papeis():
	assert n.publicos_dos_papeis(["System Manager"]) == list(n.PUBLICOS)
	assert n.publicos_dos_papeis(["RH Ponto", "Gestor Ponto"]) == ["RH", "Gestor"]
	assert n.publicos_dos_papeis(["RH Saúde"]) == ["RH"]
	assert n.publicos_dos_papeis(["Employee"]) == []


def test_guias_da_tela():
	assert {g.id for g in n.da_tela(GUIAS, "banco-talentos")} == {"talentos-cadastro", "talentos-plantoes"}
	assert n.da_tela(GUIAS, None) == []


# ------------------------------------------------------------------ resposta e progresso


def test_resposta_e_progresso():
	g = _guia()
	d = n.como_dict(g, feitos=["abrir-a-configuracao", "passo-que-saiu"])
	assert (d["total"], d["feitos"]) == (2, 1)
	assert [p["feito"] for p in d["passos"]] == [True, False]
	assert d["verificacoes"] == ["whatsapp_numero_teste"]
	assert d["teste"]["acao"][0]["valor"] == "envie."
	assert d["aviso"] == n.AVISO_JURIDICO
	assert set(n.como_dict(g, resumo=True)) == {"id", "titulo", "tema", "publico", "total", "feitos"}
	assert n.proximo_passo(g, []) == 0
	assert n.proximo_passo(g, ["abrir-a-configuracao"]) == 1
	assert n.proximo_passo(g, ["abrir-a-configuracao", "testar"]) == 1
	assert n.concluido(g, ["abrir-a-configuracao", "testar"])
	assert not n.concluido(g, ["testar"])


def test_dados_pessoais():
	assert n.dados_pessoais("CPF 529.982.247-25 e fone (27) 99876-1234")
	assert not n.dados_pessoais("dia 25, de 26 a 25, 05h-23h, R$ 30/h")


# ------------------------------------------------------------------ integridade do catálogo (NH-E2)


def _rotas_do_painel() -> set[str]:
	texto = (RAIZ / "frontend" / "src" / "router.js").read_text(encoding="utf8")
	rotas = {
		p.split("/")[0] for p in re.findall(r'path: "([^"]*)"', texto) if p and not p.startswith(("/", ":"))
	}
	return rotas | {"cockpit"}


def _doctypes() -> set[str]:
	nomes = set(CORE)
	for p in APP.glob("**/doctype/*/*.json"):
		d = json.loads(p.read_text(encoding="utf8"))
		if d.get("doctype") == "DocType":
			nomes.add(d["name"])
	return nomes


def test_catalogo_tem_guias_de_todos_os_temas_e_publicos():
	assert len(GUIAS) >= 25
	assert {p for g in GUIAS for p in g.publico} == set(n.PUBLICOS)
	assert {g.id for g in GUIAS} >= {
		"secullum-conectar",
		"whatsapp-liberar-unidade",
		"fechamento-mes",
		"aso",
		"epi",
	}


@pytest.mark.parametrize("guia", GUIAS, ids=lambda g: g.id)
def test_integridade_de_cada_guia(guia):
	rotas, doctypes = _rotas_do_painel(), _doctypes()
	for link in guia.links():
		assert link.destino in n.DESTINOS
		if link.destino == "painel":
			assert link.alvo in rotas, f"{guia.id}: rota {link.alvo} não existe"
		else:
			assert link.alvo in doctypes, f"{guia.id}: DocType {link.alvo} não existe"
	assert set(guia.telas) <= rotas, guia.id
	assert not n.dados_pessoais(guia._texto), guia.id
	if guia.manual:
		assert (RAIZ / "docs" / guia.manual.split("#")[0]).exists(), f"{guia.id}: manual {guia.manual}"
