"""Cobertura de faltas: convocação de substitutos e Banco de Talentos (docs/PRD-substituicoes.md, CS-E1). Python puro.

- **Cascata:** Nível 1 = mesmo cargo na unidade; depois de `t1` minutos sem aceite, Nível 1b = mesmo cargo nas outras
  unidades da rede; depois de `t2` minutos desde a abertura, Nível 2 = prestadores aprovados (PJ).
- **Travas:** o interno só recebe sem nenhuma quebra da CLT com o turno somado (a validação é a do
  `escala_validacao`, feita no Frappe); o prestador só recebe aprovado, com CREF válido, termo aceito na versão
  vigente, CNPJ e conta, e dentro do limite de plantões do mês.
- **Primeiro ganha:** o aceite só vale com a vaga aberta, antes do início do turno e sem vencedor.
- **Pagamento do prestador:** horas realizadas x valor-hora, em `Decimal` com ROUND_HALF_UP.

Horários em minutos do dia; momentos em `datetime` sem fuso (o do servidor).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine.documentos import cpf_valido, somente_digitos

UNIDADE, REDE, BANCO = "Unidade", "Rede", "Banco de Talentos"
NIVEIS = (UNIDADE, REDE, BANCO)
ABERTA, PREENCHIDA, NAO_PREENCHIDA, CANCELADA = "Aberta", "Preenchida", "Não preenchida", "Cancelada"
SITUACOES = (ABERTA, PREENCHIDA, NAO_PREENCHIDA, CANCELADA)
# oferta a cada pessoa
ENVIADA, BLOQUEADA, ACEITOU, NAO_PODE, ENCERRADA = "Enviada", "Bloqueada", "Aceitou", "Não posso", "Encerrada"
# prestador
AGUARDANDO_CODIGO, AGUARDANDO_APROVACAO, APROVADO, RECUSADO, SUSPENSO = (
	"Aguardando código",
	"Aguardando aprovação",
	"Aprovado",
	"Recusado",
	"Suspenso",
)
# plantão
PREVISTO, REALIZADO, NAO_COMPARECEU = "Previsto", "Realizado", "Não compareceu"


@dataclass(frozen=True)
class Parametros:
	"""Os padrões do PRD (Seção 12); a Configuracao Apuracao pode mudar cada um."""

	t1: int = 15  # minutos até chamar a rede
	t2: int = 30  # minutos desde a abertura até chamar os prestadores
	por_rodada: int = 10  # pessoas por nível
	aviso_sem_batida: int = 20  # minutos depois do início sem batida para avisar o gestor
	max_plantoes_mes: int = 6  # por prestador; 0 = sem limite (RH, 11/11/2026)
	valor_hora: Decimal = Decimal("30")  # prestador, por hora trabalhada
	hora_inicio: int = 5  # ofertas saem das 5h...
	hora_fim: int = 22  # ...às 22h
	cref_aviso_dias: int = 15


PADROES = Parametros()


# ------------------------------------------------------------------ cascata


def nivel_devido(aberta_em: datetime, agora: datetime, p: Parametros = PADROES) -> str:
	"""O nível em que a vaga deve estar agora, pelo tempo desde a abertura."""
	passados = (agora - aberta_em).total_seconds() / 60
	if passados >= p.t2:
		return BANCO
	if passados >= p.t1:
		return REDE
	return UNIDADE


def proximo_nivel(nivel: str) -> str | None:
	i = NIVEIS.index(nivel)
	return NIVEIS[i + 1] if i + 1 < len(NIVEIS) else None


def niveis_ate(nivel: str) -> tuple[str, ...]:
	"""Os níveis já alcançados (inclusive): a cascata não pula ninguém quando o job atrasa."""
	return NIVEIS[: NIVEIS.index(nivel) + 1]


def no_horario_de_envio(momento: datetime, p: Parametros = PADROES) -> bool:
	return p.hora_inicio <= momento.hour < p.hora_fim


def escolher_internos(candidatos: list[dict], ja_ofertados: set[str], p: Parametros = PADROES) -> list[dict]:
	"""Quem recebe a oferta interna: sem quebra da CLT, ainda sem oferta nesta vaga; menos horas na semana primeiro
	(equidade), até `por_rodada`. Cada candidato: employee, nome, sem_conflito, minutos_semana."""
	livres = [c for c in candidatos if c.get("sem_conflito") and c["employee"] not in ja_ofertados]
	livres.sort(key=lambda c: (c.get("minutos_semana") or 0, c.get("nome") or ""))
	return livres[: p.por_rodada]


def bloqueados(candidatos: list[dict], ja_ofertados: set[str]) -> list[dict]:
	"""Quem ficou de fora por quebra (o motivo aparece no balão da vaga)."""
	return [c for c in candidatos if not c.get("sem_conflito") and c["employee"] not in ja_ofertados]


def fim_do_turno(data: date, periodos: list[tuple[int, int]]) -> datetime:
	return datetime.combine(data, datetime.min.time()) + timedelta(minutes=max(f for _i, f in periodos))


def inicio_do_turno(data: date, periodos: list[tuple[int, int]]) -> datetime:
	return datetime.combine(data, datetime.min.time()) + timedelta(minutes=min(i for i, _f in periodos))


def minutos_do_turno(periodos: list[tuple[int, int]]) -> int:
	return sum(f - i for i, f in periodos)


def motivo_para_nao_aceitar(
	situacao: str, inicio: datetime, agora: datetime, tem_vencedor: bool
) -> str | None:
	"""Primeiro ganha: None = pode aceitar; senão, o motivo simples para a página."""
	if situacao == CANCELADA:
		return "a vaga foi cancelada"
	if situacao != ABERTA or tem_vencedor:
		return "a vaga já foi preenchida"
	if agora >= inicio:
		return "o turno já começou"
	return None


def vence_sem_ninguem(situacao: str, inicio: datetime, agora: datetime) -> bool:
	"""Chegou o início do turno com a vaga aberta: vira Não preenchida."""
	return situacao == ABERTA and agora >= inicio


# ------------------------------------------------------------------ prestador (PJ)


def cnpj_valido(cnpj: str | None) -> bool:
	d = somente_digitos(cnpj)
	if len(d) != 14 or d == d[0] * 14:
		return False
	n = [int(c) for c in d]
	for tamanho in (12, 13):
		pesos = list(range(tamanho - 7, 1, -1)) + list(range(9, 1, -1))
		soma = sum(a * b for a, b in zip(n[:tamanho], pesos, strict=True))
		dv = 0 if soma % 11 < 2 else 11 - soma % 11
		if dv != n[tamanho]:
			return False
	return True


@dataclass(frozen=True)
class Prestador:
	situacao: str
	cref_validade: date | None
	termo_versao: int | None
	cnpj: str | None
	conta: bool  # conta bancária ou PIX do CNPJ preenchida
	liberado_no_mes: str | None = None  # "AAAA-MM": o RH liberou passar do limite neste mês
	colaborador_ativo: bool = False


def travas_do_prestador(
	pr: Prestador, dia: date, plantoes_no_mes: int, versao_vigente: int | None, p: Parametros = PADROES
) -> list[str]:
	"""Motivos que impedem a oferta ao prestador (lista vazia = pode receber)."""
	motivos = []
	if pr.situacao != APROVADO:
		motivos.append(f"cadastro {pr.situacao.lower()}")
	if not pr.cref_validade or pr.cref_validade < dia:
		motivos.append("CREF vencido ou sem validade")
	if not versao_vigente or pr.termo_versao != versao_vigente:
		motivos.append("termo de credenciamento não aceito na versão vigente")
	if not cnpj_valido(pr.cnpj):
		motivos.append("CNPJ ausente ou inválido")
	if not pr.conta:
		motivos.append("sem conta bancária do CNPJ")
	if pr.colaborador_ativo:
		motivos.append("é colaborador da rede (vai pela equipe interna)")
	if p.max_plantoes_mes and plantoes_no_mes >= p.max_plantoes_mes and pr.liberado_no_mes != f"{dia:%Y-%m}":
		motivos.append(f"já tem {plantoes_no_mes} plantões no mês (limite {p.max_plantoes_mes})")
	return motivos


def perto_do_limite(plantoes_no_mes: int, p: Parametros = PADROES) -> bool:
	"""Aviso ao gestor: o próximo plantão é o último do mês."""
	return bool(p.max_plantoes_mes) and plantoes_no_mes == p.max_plantoes_mes - 1


def cref_vencendo(validade: date | None, hoje: date, p: Parametros = PADROES) -> bool:
	return bool(validade) and hoje <= validade <= hoje + timedelta(days=p.cref_aviso_dias)


def valor_do_plantao(minutos: int, valor_hora: Decimal) -> Decimal:
	return (Decimal(max(0, minutos)) * Decimal(valor_hora) / Decimal(60)).quantize(
		Decimal("0.01"), rounding=ROUND_HALF_UP
	)


def erros_do_cadastro(dados: dict, hoje: date) -> list[str]:
	"""O que falta ou está errado no formulário do QR Code (a página mostra a lista)."""
	erros = []
	for campo, nome in (
		("nome", "nome"),
		("celular", "celular"),
		("cref_numero", "número do CREF"),
		("cref_validade", "validade do CREF"),
		("razao_social", "razão social"),
	):
		if not str(dados.get(campo) or "").strip():
			erros.append(f"Informe o {nome}.")
	if not cpf_valido(dados.get("cpf") or ""):
		erros.append("CPF inválido.")
	if not cnpj_valido(dados.get("cnpj")):
		erros.append("CNPJ inválido.")
	if len(somente_digitos(dados.get("celular"))) not in (10, 11, 12, 13):
		erros.append("Celular inválido (com DDD).")
	validade = dados.get("cref_validade")
	if isinstance(validade, date) and validade < hoje:
		erros.append("O CREF está vencido.")
	if not (
		str(dados.get("pix") or "").strip()
		or (dados.get("banco") and dados.get("agencia") and dados.get("conta"))
	):
		erros.append("Informe a chave PIX ou banco, agência e conta do CNPJ.")
	if not dados.get("foto_cref"):
		erros.append("Envie a foto do CREF.")
	if not dados.get("comprovante_endereco"):
		erros.append("Envie o comprovante de endereço.")
	if not dados.get("aceite"):
		erros.append("Leia e aceite o termo de credenciamento.")
	return erros


# ------------------------------------------------------------------ aviso de falta sem batida (ao gestor)


def avisar_sem_batida(
	inicio: datetime,
	agora: datetime,
	ultima_coleta: datetime | None,
	tem_batida: bool,
	p: Parametros = PADROES,
) -> bool:
	"""Avisa só quando já passou X minutos do início **e** a última coleta é de depois disso (sem coleta nova, a
	falta de batida não diz nada). Só avisa: nunca abre a vaga sozinho."""
	limite = inicio + timedelta(minutes=p.aviso_sem_batida)
	return not tem_batida and agora >= limite and bool(ultima_coleta) and ultima_coleta >= limite


# ------------------------------------------------------------------ textos


def hhmm(minutos: int) -> str:
	return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


def texto_do_horario(periodos: list[tuple[int, int]]) -> str:
	return " e ".join(f"{hhmm(i)} às {hhmm(f)}" for i, f in periodos)


def duracao(minutos: int) -> str:
	h, m = divmod(minutos, 60)
	return f"{h}h{m:02d}" if m else f"{h} horas" if h != 1 else "1 hora"


def reais(valor: Decimal) -> str:
	inteiro, centavos = f"{Decimal(valor):.2f}".split(".")
	return f"{int(inteiro):,}".replace(",", ".") + "," + centavos
