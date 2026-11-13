"""Sincronização programa → Secullum (docs/PRD-sincronizacao-secullum.md). Python puro: travas, catálogo de casos de
teste, justificativas por quantidade e as operações (rota, método, corpo) de cada tipo de envio.

O Frappe (ingestion/sincronizacao.py) decide **quando** enviar e grava a fila; aqui fica **o que** enviar.
"""

from dataclasses import dataclass, field
from datetime import date

# ------------------------------------------------------------------ tipos de envio e travas (SS-1)

CARTAO = "cartao"  # correção de batida/abono do cartão (fila própria, docs/PRD-cartao-ponto.md)
FOLGA_ESCALA = "folga_escala"
JUSTIFICATIVA_DIA = "justificativa_dia"
HORISTA = "horista"  # falta/atestado do horista com a quantidade do dia (AT/FT)
AFASTAMENTO = "afastamento"
JUSTIFICATIVA_CADASTRO = "justificativa_cadastro"
ESTRUTURA = "estrutura"
HORARIO_FUNCIONARIO = "horario_funcionario"

TIPOS = (
	CARTAO,
	FOLGA_ESCALA,
	JUSTIFICATIVA_DIA,
	HORISTA,
	AFASTAMENTO,
	JUSTIFICATIVA_CADASTRO,
	ESTRUTURA,
	HORARIO_FUNCIONARIO,
)
NOMES_TIPOS = {
	CARTAO: "Correções do cartão",
	FOLGA_ESCALA: "Folgas da escala",
	JUSTIFICATIVA_DIA: "Licenças do dia",
	HORISTA: "Falta e atestado do horista",
	AFASTAMENTO: "Afastamentos",
	JUSTIFICATIVA_CADASTRO: "Cadastro de justificativas",
	ESTRUTURA: "Estrutura (gestor da unidade)",
	HORARIO_FUNCIONARIO: "Troca de horário do funcionário",
}

# tipos desligados no código (decisão do RH): a trava não sai de Bloqueado e nem o caso de teste envia; para religar,
# tirar daqui. Estrutura (04/11/2026): os gestores não usam o Secullum, trabalham no painel do programa.
DESATIVADOS = {
	ESTRUTURA: "Envio da estrutura (gestor da unidade) desativado no programa: os gestores não usam o Secullum.",
}

BLOQUEADO, TESTE, LIGADO = "Bloqueado", "Teste", "Ligado"
MODOS = (BLOQUEADO, TESTE, LIGADO)


def pode_enviar(
	modo: str, *, caso_aberto: bool, empresa_liberada: bool = True, suspenso: bool = False
) -> tuple[bool, str]:
	"""(pode, motivo). Em Teste, só quem tem caso de teste aberto; em Ligado, só as empresas liberadas (SS-9)."""
	if suspenso:
		return False, "Envio ao Secullum suspenso na configuração."
	if modo == BLOQUEADO or modo not in MODOS:
		return False, "Trava em Bloqueado."
	if modo == TESTE:
		return (
			(True, "") if caso_aberto else (False, "Trava em Teste: só para quem tem caso de teste aberto.")
		)
	if not empresa_liberada and not caso_aberto:
		return False, "Empresa ainda não liberada para este envio."
	return True, ""


# ------------------------------------------------------------------ catálogo de casos de teste (10.2)


@dataclass(frozen=True)
class CasoDeTeste:
	codigo: str
	tipo: str
	descricao: str
	esperado: str
	obrigatorio: bool = True
	envia: bool = True  # False = só conferência manual (o envio é de outro fluxo)
	precisa_colaborador: bool = True


CATALOGO = (
	CasoDeTeste(
		"T-J1",
		JUSTIFICATIVA_CADASTRO,
		'Ajustar a justificativa "FOLGA" com "Calcular como folga"',
		"Justificativas → FOLGA: opção Calcular como folga marcada",
		precisa_colaborador=False,
	),
	CasoDeTeste(
		"T-J2",
		JUSTIFICATIVA_CADASTRO,
		"Criar uma licença que não existe (DOASANG — doação de sangue)",
		"Justificativas → DOASANG aparece com Ajuste marcado",
		precisa_colaborador=False,
	),
	CasoDeTeste(
		"T-J3",
		JUSTIFICATIVA_CADASTRO,
		'Atualizar as opções de uma existente (ATESTAD com "Ajuste")',
		"Justificativas → ATESTAD com Ajuste marcado; o resto igual",
		precisa_colaborador=False,
	),
	CasoDeTeste(
		"T-Q1",
		JUSTIFICATIVA_CADASTRO,
		"Criar as justificativas por quantidade (AT0130 e FT0130, valor do dia 01:30)",
		"Justificativas → AT0130 (Ajuste, valor 01:30) e FT0130 (Lançar como falta, valor 01:30)",
		precisa_colaborador=False,
	),
	CasoDeTeste(
		"T-F1",
		FOLGA_ESCALA,
		"Folga num dia futuro de trabalho",
		"Cartão do dia: FOLGA nas colunas do período; sem falta",
	),
	CasoDeTeste(
		"T-F2",
		FOLGA_ESCALA,
		"Folga só no grupo 1 vale para o dia inteiro?",
		"Cartão do dia inteiro como folga (senão: anotar que precisa de todos os grupos)",
	),
	CasoDeTeste("T-F3", FOLGA_ESCALA, "Desfazer a folga", "Cartão do dia volta ao normal"),
	CasoDeTeste(
		"T-F4",
		FOLGA_ESCALA,
		"Folga num dia em que a pessoa bateu ponto",
		"Secullum recusa; o programa mostra o aviso e nada muda no cartão",
	),
	CasoDeTeste("T-F5", FOLGA_ESCALA, "Folga num domingo (revezamento)", "Cartão do domingo: FOLGA"),
	CasoDeTeste(
		"T-L1",
		JUSTIFICATIVA_DIA,
		"Licença legal de um dia (doação de sangue)",
		"Cartão do dia: DOASANG; dia abonado, sem perda de DSR",
	),
	CasoDeTeste("T-A1", AFASTAMENTO, "Afastamento de 3 dias", "Os 3 dias com a justificativa do afastamento"),
	CasoDeTeste("T-A2", AFASTAMENTO, "Desfazer o afastamento", "Os 3 dias voltam ao normal"),
	CasoDeTeste(
		"T-Q2", HORISTA, "Atestado do horista num dia de 1h30 (AT0130)", "Cartão: AT0130; 1:30 abonadas"
	),
	CasoDeTeste("T-Q3", HORISTA, "Falta do horista num dia de 3h (FT0300)", "Cartão: FT0300; 3:00 em FALTAS"),
	CasoDeTeste(
		"T-Q4",
		HORISTA,
		"Desfazer a falta (a batida chegou depois)",
		"Cartão: FT retirado; o dia mostra as horas trabalhadas",
	),
	CasoDeTeste(
		"T-Q5", HORISTA, "Atestado num sábado de escala de 5h (AT0500)", "Cartão: AT0500; 5:00 abonadas"
	),
	CasoDeTeste(
		"T-Q6",
		HORISTA,
		"Carga fora do passo de 30 min (1h15)",
		"Atestado AT0130 / falta FT0100 e o aviso de arredondamento",
	),
	CasoDeTeste(
		"T-M1",
		HORISTA,
		"Musculação: trabalho em horário diferente da referência (ex.: 18h-22h)",
		"Totais do dia: 4:00 normais, sem atraso nem extra",
		envia=False,
	),
	CasoDeTeste(
		"T-H1",
		HORARIO_FUNCIONARIO,
		"Troca de horário na data de início (Alteração de Jornada)",
		"Funcionário com o horário novo a partir da data",
		envia=False,
	),
	CasoDeTeste(
		"T-H2",
		HORARIO_FUNCIONARIO,
		"Dias anteriores à troca não mudam",
		"Totais dos dias anteriores iguais aos de antes da troca",
		envia=False,
	),
	CasoDeTeste(
		"T-C1",
		CARTAO,
		"Inclusão de batida pelo cartão do programa",
		"Batida manual na coluna certa; as batidas do relógio só mudam de coluna (mesma origem, nada desconsiderado)",
		envia=False,
	),
	CasoDeTeste(
		"T-C2", CARTAO, "Desconsiderar batida pelo cartão do programa", "Batida desconsiderada", envia=False
	),
	CasoDeTeste(
		"T-E1",
		ESTRUTURA,
		"Estrutura da unidade com o gestor",
		"Estruturas → a unidade com o responsável e os funcionários",
		precisa_colaborador=False,
	),
	# pausa paga por liberalidade do instrutor (RH, 04/11/2026): não obrigatórios (só se for usar o envio)
	CasoDeTeste(
		"T-P1",
		JUSTIFICATIVA_CADASTRO,
		"Criar a justificativa da pausa paga (PAUSA15, valor do dia 00:15, Ajuste)",
		"Justificativas → PAUSA15 com Ajuste marcado e valor do dia 00:15",
		obrigatorio=False,
		precisa_colaborador=False,
	),
	CasoDeTeste(
		"T-P2",
		JUSTIFICATIVA_DIA,
		"Lançar a PAUSA15 no primeiro grupo livre de um dia trabalhado (as batidas ficam)",
		"Cartão do dia: as batidas iguais e PAUSA15 no grupo livre; Totais do dia: Ajuste com 0:15 a mais e as horas "
		"trabalhadas sem mudar (se o Ajuste não somar, anotar: o Secullum não paga a pausa pela justificativa)",
		obrigatorio=False,
	),
	# o T-P2 lançou só a justificativa e o Ajuste ficou 0:00 (RH, 09/11/2026): o fluxo completo, com o intervalo
	CasoDeTeste(
		"T-P3",
		JUSTIFICATIVA_DIA,
		"Pausa paga completa: a saída vai para a Saída 2, o intervalo de 15 min entra no meio da jornada e a PAUSA15 "
		"no 3º par",
		"Cartão do dia: Entrada 1 e Saída 2 com as batidas do relógio (sem lápis), Saída 1 e Entrada 2 com o intervalo "
		"(manual, 15 min) e PAUSA15 no 3º par; o caso mostra o Ajuste que o Secullum calculou (o certo é 00:15)",
		obrigatorio=False,
	),
)
POR_CODIGO = {c.codigo: c for c in CATALOGO}


def casos_do_tipo(tipo: str) -> list[CasoDeTeste]:
	return [c for c in CATALOGO if c.tipo == tipo]


def faltando_para_ligar(tipo: str, aprovados: set[str]) -> list[str]:
	"""Casos obrigatórios do tipo ainda não aprovados (a trava só vai a Ligado com a lista vazia)."""
	return [c.codigo for c in casos_do_tipo(tipo) if c.obrigatorio and c.codigo not in aprovados]


# ------------------------------------------------------------------ justificativas (seção 6 e 7.3)

PASSO_MIN = 30
MAXIMO_MIN = 480


def hhmm(minutos: int) -> str:
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


def quantidade_arredondada(minutos: int, *, para_cima: bool) -> int:
	"""SS-D8: passos de 30 min, a favor do empregado (atestado para cima, falta para baixo), de 0h30 a 8h."""
	if minutos <= 0:
		return 0
	passos = -(-minutos // PASSO_MIN) if para_cima else minutos // PASSO_MIN
	return min(max(passos * PASSO_MIN, PASSO_MIN), MAXIMO_MIN)


def nome_quantidade(prefixo: str, minutos: int) -> str:
	"""("AT", 90) -> "AT0130"."""
	return f"{prefixo}{minutos // 60:02d}{minutos % 60:02d}"


def justificativa_horista(tipo: str, minutos: int) -> tuple[str, int, bool]:
	"""(nome, minutos enviados, arredondou?) — tipo "atestado" ou "falta"."""
	atestado = tipo == "atestado"
	quantidade = quantidade_arredondada(minutos, para_cima=atestado)
	return nome_quantidade("AT" if atestado else "FT", quantidade), quantidade, quantidade != minutos


@dataclass(frozen=True)
class Justificativa:
	nome: str  # nome abreviado (7)
	nome_completo: str
	opcoes: dict = field(default_factory=dict)  # campos do POST Justificativas (camelCase), só os ligados
	valor_dia: str = ""


def _ajuste(nome, completo, **extra) -> Justificativa:
	return Justificativa(nome, completo, {"ajuste": True, **extra})


# Seção 6: as que já existem no Secullum (lidas em 02/11/2026) mantêm o nome; as outras são criadas.
LEGAIS = (
	Justificativa("FOLGA", "FOLGA", {"calcularComoFolga": True, "naoPermitirFuncionariosUtilizar": True}),
	_ajuste("ATESTAD", "ATESTADO MEDICO"),
	_ajuste("FALECIM", "FALECIMENTO"),
	_ajuste("L-GALA", "LICENCA GALA"),
	_ajuste("L-PATER", "LICENCA PATERNIDADE"),
	_ajuste("DOASANG", "DOACAO DE SANGUE"),
	_ajuste("ELEITOR", "ALISTAMENTO ELEITORAL"),
	_ajuste("JUIZO", "COMPARECIMENTO EM JUIZO"),
	_ajuste("VESTIB", "VESTIBULAR"),
	_ajuste("ACOMPGE", "ACOMPANHAR CONSULTA GESTANTE"),
	_ajuste("FILHO6", "FILHO ATE 6 ANOS AO MEDICO"),
	_ajuste("EXAMECA", "EXAMES PREVENTIVOS DE CANCER"),
)

# Leave Type do programa -> justificativa do Secullum (dia a dia ou afastamento)
LICENCAS = {
	"Casamento": "L-GALA",
	"Falecimento": "FALECIM",
	"Licença-paternidade": "L-PATER",
	"Licença-maternidade": "L-MATER",
	"Doação de sangue": "DOASANG",
	"Alistamento eleitoral": "ELEITOR",
	"Comparecimento em juízo": "JUIZO",
	"Vestibular": "VESTIB",
	"Acompanhar consulta da gestante": "ACOMPGE",
	"Filho até 6 anos ao médico": "FILHO6",
	"Exames preventivos de câncer": "EXAMECA",
	"Férias": "FERIAS",
	"Atestado Médico": "ATESTAD",
}
# acima deste número de dias a licença vai como afastamento (FuncionariosAfastamentos), não dia a dia
DIAS_PARA_AFASTAMENTO = 3


def justificativas_por_quantidade() -> list[Justificativa]:
	saida = []
	for minutos in range(PASSO_MIN, MAXIMO_MIN + 1, PASSO_MIN):
		valor = hhmm(minutos)
		saida.append(
			Justificativa(
				nome_quantidade("AT", minutos), f"ATESTADO HORISTA {valor}", {"ajuste": True}, valor
			)
		)
		saida.append(
			Justificativa(
				nome_quantidade("FT", minutos),
				f"FALTA HORISTA {valor}",
				{"lancarComoHorasFalta": True},
				valor,
			)
		)
	return saida


# pausa paga por liberalidade do instrutor (RH, 04/11/2026): a API não aceita minutos livres (cada justificativa tem
# valor fixo e o cartão só recebe "Justificativa no Grupo"); como a pausa é sempre de 15 min, uma justificativa fixa
# de 0:15 com Ajuste, lançada num grupo livre do dia (as batidas ficam). Precisa dos casos T-P1 e T-P2.
# RH, 13/11/2026: o nome no Secullum nunca fala de pausa paga/remunerada (fica no espelho homologado)
PAUSA_PAGA = Justificativa("PAUSA15", "PAUSA 15 MINUTOS", {"ajuste": True}, "00:15")
# justificativas que podem ir num dia com batida (num grupo livre): nunca cobrem uma batida
PODE_COM_BATIDA = frozenset({PAUSA_PAGA.nome})


def todas_as_justificativas() -> list[Justificativa]:
	return [*LEGAIS, *justificativas_por_quantidade(), PAUSA_PAGA]


OPCOES_GET = {  # campo do POST (camelCase) -> campo do GET (PascalCase)
	"ajuste": "Ajuste",
	"calcularComoFolga": "CalcularComoFolga",
	"lancarComoHorasFalta": "LancarComoHorasFalta",
	"naoPermitirFuncionariosUtilizar": "NaoPermitirFuncionariosUtilizar",
	"descontarDsr": "DescontarDsr",
}


def corpo_justificativa(j: Justificativa, atual: dict | None = None) -> dict:
	"""Corpo do POST Justificativas. Com `atual` (GET), mantém as opções que já estavam e liga as da regra."""
	corpo = {"nomeAbreviado": j.nome, "nomeCompleto": (atual or {}).get("NomeCompleto") or j.nome_completo}
	for chave_post, chave_get in OPCOES_GET.items():
		corpo[chave_post] = bool((atual or {}).get(chave_get))
	corpo.update(j.opcoes)
	if j.valor_dia:
		corpo["valorDia"] = j.valor_dia
	return corpo


def justificativa_diverge(j: Justificativa, atual: dict | None) -> list[str]:
	"""O que falta no Secullum para a justificativa ficar como a regra (vazio = igual)."""
	if not atual:
		return ["não existe"]
	faltas = [f"{chave} desligado" for chave in j.opcoes if not atual.get(OPCOES_GET.get(chave, chave))]
	if j.valor_dia and str(atual.get("ValorDia") or "")[:5] != j.valor_dia:
		faltas.append(f"valor do dia {atual.get('ValorDia') or '—'} (esperado {j.valor_dia})")
	return faltas


# ------------------------------------------------------------------ operações


@dataclass(frozen=True)
class Operacao:
	metodo: str
	rota: str
	corpo: dict | None = None
	params: dict | None = None
	# DELETE de uma batida que o próprio programa incluiu (desfazer do T-P3): só sai se a coluna ainda tem esta hora
	apagar_hora: str | None = None

	def descricao(self) -> str:
		corpo = self.corpo or {}
		alvo = (
			corpo.get("Justificativa")
			or corpo.get("nomeAbreviado")
			or corpo.get("justificativaNome")
			or corpo.get("Hora")
			or (f"{corpo['ColunaOrigem']} → {corpo['ColunaDestino']}" if "ColunaOrigem" in corpo else "")
			or corpo.get("Coluna")
			or ""
		)
		return f"{self.metodo} {self.rota} {alvo}".strip()

	def como_dict(self) -> dict:
		saida = {"metodo": self.metodo, "rota": self.rota, "corpo": self.corpo, "params": self.params}
		if self.apagar_hora:
			saida["apagar_hora"] = self.apagar_hora
		return saida


def op_justificativa_dia(cpf: str, dia: date, nome: str, grupos: int = 1) -> list[Operacao]:
	return [
		Operacao(
			"POST",
			"CartaoPonto/Justificativa",
			{"Cpf": cpf, "Data": dia.isoformat(), "Grupo": grupo, "Justificativa": nome},
		)
		for grupo in range(1, max(grupos, 1) + 1)
	]


def op_justificativa_grupo(cpf: str, dia: date, nome: str, grupo: int) -> Operacao:
	"""Justificativa num grupo só (ex.: PAUSA15 no primeiro grupo livre, depois das batidas)."""
	return Operacao(
		"POST",
		"CartaoPonto/Justificativa",
		{"Cpf": cpf, "Data": dia.isoformat(), "Grupo": grupo, "Justificativa": nome},
	)


def grupo_livre(registro: dict | None, minimo: int = 1) -> int | None:
	"""O primeiro grupo (par Entrada/Saída) sem nada no cartão do Secullum, a partir de `minimo`; None se não houver."""
	registro = registro or {}
	for g in range(max(minimo, 1), 6):
		if (
			not str(registro.get(f"Entrada{g}") or "").strip()
			and not str(registro.get(f"Saida{g}") or "").strip()
		):
			return g
	return None


def cabe_no_dia(registro: dict | None, operacoes: list[dict]) -> tuple[bool, str]:
	"""Pode lançar as justificativas do dia? A regra geral é não lançar em dia com batida; as de PODE_COM_BATIDA vão
	num grupo livre (o grupo da operação precisa estar vazio). (pode, motivo)."""
	justificativas = [
		o["corpo"] for o in operacoes if o.get("rota") == "CartaoPonto/Justificativa" and o.get("corpo")
	]
	if justificativas and all(c.get("Justificativa") in PODE_COM_BATIDA for c in justificativas):
		for c in justificativas:
			g = int(c.get("Grupo") or 1)
			if grupo_livre(registro, g) != g:
				return False, f"o grupo {g} do cartão já está ocupado"
		return True, ""
	if tem_batida(registro):
		return False, "o colaborador bateu ponto no dia"
	return True, ""


# ------------------------------------------------------------------ pausa paga completa (T-P3)

MOTIVO_PAUSA = "Intervalo de {0} min incluído no cartão ponto"  # neutro: vai ao Secullum (RH, 13/11/2026)


def _horas_do_dia(atuais: dict[str, str]) -> list[str]:
	from hrms_secullum_brasil.integrations.secullum import edicao_cartao as ec

	return [atuais[c] for c in ec.COLUNAS if ec.HORA.match(atuais.get(c, ""))]


def horario_da_pausa(entrada: str, saida: str, minutos: int = 15) -> tuple[str, str]:
	"""O intervalo no meio da jornada: (início, fim), com `minutos` de pausa. Ex.: 16:55-21:27 → 19:03-19:18."""

	def m(h: str) -> int:
		hh, mm = (int(x) for x in h.split(":"))
		return hh * 60 + mm

	ini, fim = m(entrada), m(saida)
	if fim <= ini:
		fim += 24 * 60
	if fim - ini <= minutos + 60:
		raise ValueError(
			f"A jornada {entrada}-{saida} é curta demais para um intervalo de {minutos} min no meio."
		)
	inicio = ini + (fim - ini - minutos) // 2

	def h(x: int) -> str:
		x %= 24 * 60
		return f"{x // 60:02d}:{x % 60:02d}"

	return h(inicio), h(inicio + minutos)


def ops_pausa_paga(
	cpf: str, dia: date, registro: dict | None, minutos: int = 15
) -> tuple[list[Operacao], tuple[str, str]]:
	"""T-P3: o dia do Secullum com só a entrada e a saída (do relógio) ganha o intervalo no meio — a saída muda de
	coluna pela Troca (continua original), o intervalo entra como batida manual — e a PAUSA15 no par seguinte.
	(operações na ordem, (início, fim) do intervalo)."""
	from hrms_secullum_brasil.integrations.secullum import edicao_cartao as ec

	atuais = ec.colunas_do_registro(registro)
	horas = _horas_do_dia(atuais)
	if len(horas) != 2 or len(atuais) != 2:
		raise ValueError(
			"Escolha um dia em que o Secullum tem só a entrada e a saída (uma batida em cada, sem justificativa); "
			f"o dia tem: {', '.join(f'{c}={v}' for c, v in atuais.items()) or 'nada'}."
		)
	pausa = horario_da_pausa(horas[0], horas[1], minutos)
	motivo = MOTIVO_PAUSA.format(minutos)
	ops = [
		Operacao(o.metodo, o.rota, ec.com_identificador(o, cpf))
		for o in ec.operacoes(dia, atuais, [horas[0], *pausa, horas[1]], motivo)
	]
	if any(o.metodo == "DELETE" for o in ops):  # nunca tirar batida do relógio para abrir espaço
		raise ValueError("O envio apagaria uma batida do dia: escolha outro dia.")
	return [*ops, op_justificativa_grupo(cpf, dia, PAUSA_PAGA.nome, 3)], pausa


def ops_desfazer_pausa(cpf: str, dia: date, registro: dict | None, pausa: tuple[str, str]) -> list[Operacao]:
	"""Volta o dia do T-P3: tira a PAUSA15 e as duas batidas do intervalo (só elas) e devolve a saída à Saída 1."""
	from hrms_secullum_brasil.integrations.secullum import edicao_cartao as ec

	atuais = ec.colunas_do_registro(registro)
	horas = _horas_do_dia(atuais)
	if len(pausa) != 2 or any(h not in horas for h in pausa):
		raise ValueError(
			f"O cartão do Secullum não tem o intervalo {'-'.join(p or '?' for p in pausa)} do teste: confira na tela."
		)
	ficam = [h for h in horas if h not in pausa]
	saida = []
	for o in ec.operacoes(
		dia, atuais, ficam, "Teste: desfazer a pausa paga", justificativa_retirada=PAUSA_PAGA.nome
	):
		valor = atuais.get(o.corpo.get("Coluna", ""), "") if o.metodo == "DELETE" else ""
		hora = valor if ec.HORA.match(valor) else None
		if hora and hora not in pausa:
			raise ValueError(
				f"O desfazer apagaria a batida {hora}, que não é do intervalo: ajuste no Secullum."
			)
		saida.append(Operacao(o.metodo, o.rota, ec.com_identificador(o, cpf), apagar_hora=hora))
	return saida


def sem_apagar_batida(registro: dict | None, operacoes: list[dict]) -> tuple[list[dict], list[str]]:
	"""Trava da batida do relógio (RH, 04/11/2026): o DELETE CartaoPonto destas filas serve só para tirar uma
	justificativa; numa coluna com horário ele desconsideraria a batida. (operações que podem ir, colunas puladas)."""
	registro = registro or {}
	vao, puladas = [], []
	for op in operacoes:
		coluna = (op.get("corpo") or {}).get("Coluna")
		valor = str(registro.get(coluna) or "")
		if (
			op.get("metodo") == "DELETE"
			and op.get("rota") == "CartaoPonto"
			and ":" in valor
			and op.get("apagar_hora") != valor.zfill(5)  # só a batida que o programa incluiu (T-P3)
		):
			puladas.append(f"{coluna}={registro.get(coluna)}")
			continue
		vao.append(op)
	return vao, puladas


def op_retirar_justificativa_dia(cpf: str, dia: date, motivo: str, grupos: int = 1) -> list[Operacao]:
	"""DELETE CartaoPonto na Entrada do grupo: com justificativa na coluna, o Secullum apaga o grupo."""
	return [
		Operacao(
			"DELETE",
			"CartaoPonto",
			{"Cpf": cpf, "Data": dia.isoformat(), "Coluna": f"Entrada{g}", "Motivo": motivo},
		)
		for g in range(1, max(grupos, 1) + 1)
	]


def op_afastamento(cpf: str, inicio: date, fim: date, justificativa: str, motivo: str) -> Operacao:
	return Operacao(
		"POST",
		"FuncionariosAfastamentos",
		{
			"cpf": cpf,
			"inicio": inicio.isoformat(),
			"fim": fim.isoformat(),
			"motivo": motivo[:100],
			"justificativaNome": justificativa,
		},
	)


def op_retirar_afastamento(cpf: str, inicio: date, fim: date) -> Operacao:
	return Operacao(
		"DELETE",
		"FuncionariosAfastamentos/Cpf",
		params={"dataInicio": inicio.isoformat(), "dataFim": fim.isoformat(), "funcionarioCpf": cpf},
	)


def op_estrutura(descricao: str, responsaveis: list[str], funcionarios: list[str]) -> Operacao:
	return Operacao(
		"POST",
		"Estruturas",
		{
			"descricao": descricao[:100],
			"responsaveis": [{"cpf": c} for c in responsaveis],
			"funcionariosVinculados": [{"cpf": c} for c in funcionarios],
		},
	)


def op_justificativa_cadastro(j: Justificativa, atual: dict | None = None) -> Operacao:
	return Operacao("POST", "Justificativas", corpo_justificativa(j, atual))


# ------------------------------------------------------------------ conferência depois do envio


def justificativa_no_cartao(registro: dict | None, nome: str, grupo: int = 1) -> bool:
	return bool(registro) and str(registro.get(f"Entrada{grupo}") or "").strip().upper() == nome.upper()


def tem_batida(registro: dict | None) -> bool:
	"""O dia tem alguma hora (batida) nas colunas do cartão do Secullum."""
	if not registro:
		return False
	return any(":" in str(registro.get(f"{t}{n}") or "") for n in range(1, 6) for t in ("Entrada", "Saida"))


def afastamento_presente(afastamentos: list[dict], cpf: str, inicio: date, fim: date) -> bool:
	def dig(v):
		return "".join(c for c in str(v or "") if c.isdigit())

	for a in afastamentos:
		mesmo = dig(a.get("Cpf") or a.get("FuncionarioCpf")) == dig(cpf)
		if (
			mesmo
			and str(a.get("Inicio"))[:10] == inicio.isoformat()
			and str(a.get("Fim"))[:10] == fim.isoformat()
		):
			return True
	return False
