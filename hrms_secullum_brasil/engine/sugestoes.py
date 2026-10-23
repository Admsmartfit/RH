"""O que está errado e como resolver (docs/PRD-cartao-ponto.md, CP-04): explicação em linguagem de RH e sugestões
de correção por tipo de inconsistência. As sugestões só pré-preenchem o cartão; quem corrige confirma (CP-09).

Todo tipo do Select de Inconsistencia de Ponto tem uma entrada aqui (há teste).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import pairwise

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.cartao_edicao import ABONAR, DESCONSIDERAR, INCLUIR, Batida, hhmm
from hrms_secullum_brasil.engine.painel import sugerir_horario

# ações das sugestões, além de INCLUIR, DESCONSIDERAR e ABONAR do cartão
EDITAR = "editar"  # leva o foco para as batidas do dia no cartão
MANTER = "manter"  # nada a corrigir no ponto: fica para o fechamento
JORNADA_FRAGMENTADA = "jornada_fragmentada"  # libera o cargo na CCT (CP-06)
DESK = "desk"  # corrigir um cadastro no Desk
SECULLUM = "secullum"  # o dado vem do Secullum: corrigir lá
REENVIAR = "reenviar"  # manda de novo ao Secullum a correção que falhou (CP-10)
# docs/PRD-monitoramento-horistas.md
INCLUIR_INTERVALO = "incluir_intervalo"  # duas células livres para o intervalo do termo assinado (MH-06)
TERMO = "termo"  # imprime o Termo de Ajuste de Intervalo (MH-05)
CIENTE = "ciente"  # RH ciente: não há termo, paga a indenização (DH-3)
REENVIAR_WHATSAPP = "reenviar_whatsapp"

Par = tuple[int, int]


@dataclass(frozen=True)
class Sugestao:
	acao: str
	rotulo: str
	minuto: int | None = None
	referencia: str | None = None


@dataclass(frozen=True)
class ContextoDia:
	batidas: tuple[Batida, ...] = ()
	previsto: tuple[Par, ...] = ()
	duplicidade_minutos: int = d.DUPLICIDADE_MIN
	intervalo_minimo: int = d.INTERVALO_MINIMO_MIN
	horista: bool = False


@dataclass(frozen=True)
class Orientacao:
	explicacao: str
	sugestoes: tuple[Sugestao, ...]


CORRIGIR_BATIDA = Sugestao(EDITAR, "Corrigir uma batida (se foi erro de registro)")
ABONAR_DIA = Sugestao(ABONAR, "Abonar o dia (atestado, declaração, serviço externo...)")

# tipos que não dependem das batidas do dia: (explicação, sugestões)
FIXOS: dict[str, tuple[str, tuple[Sugestao, ...]]] = {
	"atraso": (
		"Chegou depois do horário previsto, além da tolerância.",
		(
			ABONAR_DIA,
			CORRIGIR_BATIDA,
			Sugestao(MANTER, "Manter: o atraso é descontado ou vai para o banco de horas"),
		),
	),
	"he_acima_limite": (
		"Fez mais hora extra no dia do que o limite da CCT (CLT, art. 59: até 2 h).",
		(
			CORRIGIR_BATIDA,
			Sugestao(MANTER, "Manter: as horas são pagas; confira a autorização da hora extra"),
		),
	),
	"interjornada": (
		"Descansou menos de 11 h entre o fim de um dia e o começo do seguinte (CLT, art. 66).",
		(CORRIGIR_BATIDA, Sugestao(MANTER, "Manter: as horas que faltaram são pagas como extra")),
	),
	"intervalo_superior_2h": (
		"O intervalo do dia passou de 2 h. Só vale com acordo escrito ou CCT (CLT, art. 71). Para quem trabalha em "
		"dois turnos (ex.: ginástica de manhã e à noite), libere o cargo.",
		(Sugestao(JORNADA_FRAGMENTADA, "Permitir para o cargo (jornada fragmentada)"), CORRIGIR_BATIDA),
	),
	"aula_nao_registrada": (
		"O professor tinha aula na grade e não há batida no horário.",
		(
			Sugestao(INCLUIR, "Incluir a batida da aula"),
			ABONAR_DIA,
			Sugestao(MANTER, "Manter a falta da aula"),
		),
	),
	"limite_aulas_excedido": (
		"O professor deu mais aulas no dia do que o limite da CCT.",
		(Sugestao(DESK, "Conferir a Grade de Aulas"), Sugestao(MANTER, "Manter")),
	),
	"cref_vencido": (
		"O CREF do colaborador está vencido.",
		(Sugestao(DESK, "Atualizar o CREF no cadastro"),),
	),
	"erro_sync_cadastro": (
		"O cadastro não foi enviado ao Secullum.",
		(Sugestao(DESK, "Ver o erro no registro de sincronização"),),
	),
	"batida_periodo_fechado": (
		"Chegou uma batida num dia de período já fechado: ela não entra na apuração.",
		(Sugestao(DESK, "Reabrir o fechamento, se a batida precisar valer"), Sugestao(MANTER, "Manter")),
	),
	"configuracao_ausente": (
		"Falta configuração para apurar o dia (perfil de jornada ou CCT vigente).",
		(Sugestao(DESK, "Completar o cadastro do colaborador"),),
	),
	"banco_horas_rescisao": (
		"O colaborador saiu com saldo no banco de horas: o saldo vai para a rescisão.",
		(Sugestao(DESK, "Conferir o Fechamento do Banco de Horas"),),
	),
	"domingos_sem_folga": (
		"Trabalhou domingos seguidos sem folga num domingo (escala de revezamento).",
		(Sugestao(DESK, "Ajustar a Escala do Mês"), Sugestao(MANTER, "Manter")),
	),
	"sete_dias_seguidos": (
		"Trabalhou 7 dias seguidos sem descanso semanal (CLT, art. 67).",
		(Sugestao(DESK, "Ajustar a Escala do Mês"), Sugestao(MANTER, "Manter: o 7º dia é pago em dobro")),
	),
	"descanso_semanal": (
		"O descanso da semana ficou menor que 35 h (24 h do repouso + 11 h da interjornada).",
		(CORRIGIR_BATIDA, Sugestao(MANTER, "Manter: as horas que faltaram são pagas como extra")),
	),
	"epi_sem_entrega": (
		"O cargo exige EPI e não há entrega registrada.",
		(Sugestao(DESK, "Registrar a entrega do EPI"),),
	),
	"epi_troca_vencida": ("A troca do EPI está vencida.", (Sugestao(DESK, "Registrar a troca do EPI"),)),
	"epi_ca_vencido": ("O CA do EPI entregue está vencido.", (Sugestao(DESK, "Trocar o EPI"),)),
	"epi_devolucao_pendente": (
		"O colaborador saiu sem devolver o EPI.",
		(Sugestao(DESK, "Registrar a devolução do EPI"),),
	),
	"aso_vencido": (
		"O ASO do colaborador está vencido.",
		(Sugestao(DESK, "Agendar o exame e registrar o ASO"),),
	),
	"treinamento_vencido": (
		"Um treinamento obrigatório está vencido.",
		(Sugestao(DESK, "Registrar o treinamento"),),
	),
	"excesso_jornada_estagio": (
		"O estagiário passou da jornada diária do TCE (Lei 11.788, art. 10).",
		(CORRIGIR_BATIDA, Sugestao(MANTER, "Manter: oriente o supervisor do estágio")),
	),
	"excesso_semanal_estagio": (
		"O estagiário passou da carga semanal do TCE.",
		(Sugestao(MANTER, "Manter: oriente o supervisor do estágio"),),
	),
	"tce_vencido": ("O TCE do estagiário está vencido.", (Sugestao(DESK, "Renovar ou encerrar o TCE"),)),
	"relatorio_estagio_pendente": (
		"O relatório semestral do estágio não foi entregue.",
		(Sugestao(DESK, "Registrar o relatório no TCE"),),
	),
	"seguro_estagio_vencido": (
		"O seguro do estagiário está vencido.",
		(Sugestao(DESK, "Atualizar o seguro no TCE"),),
	),
	"nascimento_ausente": (
		"O Secullum não informa a data de nascimento.",
		(Sugestao(SECULLUM, "Preencher no Secullum (vem na próxima importação)"),),
	),
	"colaborador_nao_encontrado_secullum": (
		"O colaborador não está mais no Secullum.",
		(Sugestao(SECULLUM, "Conferir no Secullum se foi excluído ou transferido"),),
	),
	"excesso_jornada_horista": (
		"O horista passou de 4h sem registrar o intervalo no limite de vezes do mês. Se a pausa foi feita, colha o "
		"termo assinado e inclua o intervalo de cada dia no cartão; sem termo, o intervalo é pago como indenização.",
		(
			Sugestao(TERMO, "Imprimir o termo de ajuste"),
			Sugestao(EDITAR, "Incluir os intervalos no cartão"),
			Sugestao(CIENTE, "Ciente: pagar a indenização"),
		),
	),
	"whatsapp_nao_enviado": (
		"O aviso pelo WhatsApp não foi entregue (sem celular, número inválido ou a Evolution API não respondeu).",
		(
			Sugestao(REENVIAR_WHATSAPP, "Reenviar o WhatsApp"),
			Sugestao(DESK, "Conferir o celular no cadastro"),
		),
	),
	"envio_cartao_secullum": (
		"A correção foi gravada no programa, mas o Secullum recusou ou não respondeu. O cálculo do programa já vale.",
		(Sugestao(REENVIAR, "Reenviar ao Secullum"), Sugestao(SECULLUM, "Corrigir direto no Secullum")),
	),
	"alteracao_periodo_fechado": (
		"O Secullum mudou um dado de um dia de período já fechado: a mudança não entrou na apuração.",
		(Sugestao(DESK, "Reabrir o fechamento, se a mudança precisar valer"), Sugestao(MANTER, "Manter")),
	),
}

DO_DIA = ("marcacao_impar", "marcacao_duplicada", "falta", "intrajornada")
TIPOS = frozenset(FIXOS) | frozenset(DO_DIA)


def orientar(tipo: str, contexto: ContextoDia | None = None) -> Orientacao:
	"""Explicação e sugestões para a inconsistência. Tipo desconhecido: sem correção automática."""
	contexto = contexto or ContextoDia()
	if tipo == "marcacao_impar":
		return _marcacao_impar(contexto)
	if tipo == "marcacao_duplicada":
		return _marcacao_duplicada(contexto)
	if tipo == "falta":
		return _falta(contexto)
	if tipo == "intrajornada":
		return _intrajornada(contexto)
	if tipo in FIXOS:
		explicacao, sugestoes = FIXOS[tipo]
		return Orientacao(explicacao, sugestoes)
	return Orientacao("Sem correção automática: confira no Desk.", (Sugestao(DESK, "Abrir no Desk"),))


def _minutos(contexto: ContextoDia) -> list[int]:
	return sorted(b.minuto for b in contexto.batidas)


def _marcacao_impar(contexto: ContextoDia) -> Orientacao:
	minutos = _minutos(contexto)
	sugestoes = []
	previsto = sugerir_horario(contexto.previsto, minutos)
	if previsto is not None:
		sugestoes.append(Sugestao(INCLUIR, f"Incluir {hhmm(previsto)} (horário previsto)", minuto=previsto))
	sugestoes.append(Sugestao(INCLUIR, "Incluir outro horário"))
	if minutos:
		ultima = max(contexto.batidas, key=lambda b: b.minuto)
		sugestoes.append(
			Sugestao(
				DESCONSIDERAR,
				f"Desconsiderar {hhmm(ultima.minuto)} (bateu a mais)",
				ultima.minuto,
				ultima.referencia,
			)
		)
	return Orientacao(
		f"Falta uma batida: o dia tem {len(minutos)} batida{'s' if len(minutos) != 1 else ''} "
		"(esqueceu de bater a entrada ou a saída).",
		tuple(sugestoes),
	)


def _marcacao_duplicada(contexto: ContextoDia) -> Orientacao:
	batidas = sorted(contexto.batidas, key=lambda b: b.minuto)
	repetidas = [
		depois
		for antes, depois in pairwise(batidas)
		if depois.minuto - antes.minuto <= contexto.duplicidade_minutos
	]
	sugestoes = tuple(
		Sugestao(DESCONSIDERAR, f"Desconsiderar a repetida {hhmm(b.minuto)}", b.minuto, b.referencia)
		for b in repetidas
	)
	return Orientacao(
		f"Bateu o ponto duas vezes em até {contexto.duplicidade_minutos} min.",
		sugestoes or (CORRIGIR_BATIDA,),
	)


def _falta(contexto: ContextoDia) -> Orientacao:
	sugestoes = [ABONAR_DIA]
	if contexto.previsto:
		inicio, fim = contexto.previsto[0][0], contexto.previsto[-1][1]
		sugestoes.append(
			Sugestao(
				INCLUIR,
				f"Incluir as batidas (esqueceu de bater; previsto {hhmm(inicio)} a {hhmm(fim)})",
				inicio,
			)
		)
	sugestoes.append(Sugestao(MANTER, "Manter a falta (desconta o dia e o DSR)"))
	return Orientacao("Não há batida num dia de trabalho previsto.", tuple(sugestoes))


def _intrajornada(contexto: ContextoDia) -> Orientacao:
	minutos = _minutos(contexto)
	intervalos = [minutos[i + 1] - minutos[i] for i in range(1, len(minutos) - 1, 2)]
	texto = "O intervalo de almoço ficou menor que o mínimo"
	if intervalos:
		texto += f": {min(intervalos)} min (mínimo {contexto.intervalo_minimo})"
	elif minutos:
		texto = "Passou do limite da jornada sem registrar intervalo"
	sugestoes = [
		CORRIGIR_BATIDA,
		Sugestao(MANTER, "Manter: o intervalo que faltou é pago (CLT, art. 71, § 4º)"),
	]
	if contexto.horista:  # MH-06: a pausa feita e não registrada entra pelo termo assinado
		sugestoes.insert(0, Sugestao(INCLUIR_INTERVALO, "Incluir o intervalo do termo assinado"))
	return Orientacao(texto + ".", tuple(sugestoes))


def orientar_varios(tipos: Sequence[str], contexto: ContextoDia | None = None) -> dict[str, Orientacao]:
	return {tipo: orientar(tipo, contexto) for tipo in tipos}
