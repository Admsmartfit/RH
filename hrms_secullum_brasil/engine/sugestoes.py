"""O que está errado e como resolver (docs/PRD-cartao-ponto.md, CP-04): explicação em linguagem de RH e sugestões
de correção por tipo de inconsistência. As sugestões só pré-preenchem o cartão; quem corrige confirma (CP-09).

docs/PRD-tratamento-inconsistencias.md (TI-04, TI-05): ações de um clique do balão — batida prevista, jornada
completa e intervalo do termo calculados aqui (o frontend só põe os horários nas células) — e o texto de "Manter"
pelo tipo de remuneração e pelo destino (banco ou folha). "Manter" nunca cria verba (DT-2).

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
# docs/PRD-tratamento-inconsistencias.md
JORNADA_COMPLETA = "jornada_completa"  # preenche todas as batidas previstas (esqueceu de bater o dia, DT-9)
ATESTADO = "atestado"  # modal do atestado (anexo e CID em permlevel 1, DT-5)
ABONO_PARCIAL = "abono_parcial"  # abona só os minutos do atraso (DT-6, TI-06)
FOLGA_COMPENSATORIA = "folga_compensatoria"  # escolher o dia da folga (DT-8)
COBRAR_WHATSAPP = "cobrar_whatsapp"  # cobrar o colaborador pelo WhatsApp (TI-08)

Par = tuple[int, int]


@dataclass(frozen=True)
class Sugestao:
	acao: str
	rotulo: str
	minuto: int | None = None
	referencia: str | None = None
	minutos: tuple[int, ...] = ()  # vários horários para pré-preencher (jornada completa, intervalo do termo)


@dataclass(frozen=True)
class ContextoDia:
	batidas: tuple[Batida, ...] = ()
	previsto: tuple[Par, ...] = ()
	duplicidade_minutos: int = d.DUPLICIDADE_MIN
	intervalo_minimo: int = d.INTERVALO_MINIMO_MIN
	horista: bool = False
	intervalo_curto: int = d.INTERVALO_CURTO_MIN
	jornada_sem_intervalo_ate: int = d.JORNADA_SEM_INTERVALO_ATE_MIN
	jornada_intervalo_curto_ate: int = d.JORNADA_INTERVALO_CURTO_ATE_MIN
	banco_he: bool = False  # as horas extras do dia vão para o banco (participa na data)
	banco_atraso: bool = False  # o atraso do dia é debitado do banco (participa e a CCT debita atrasos)
	falta_horista_desconta_dsr: bool = d.FALTA_HORISTA_DESCONTA_DSR


@dataclass(frozen=True)
class Orientacao:
	explicacao: str
	sugestoes: tuple[Sugestao, ...]


CORRIGIR_BATIDA = Sugestao(EDITAR, "Corrigir uma batida (se foi erro de registro)")
ABONAR_DIA = Sugestao(ABONAR, "Abonar o dia (atestado, declaração, serviço externo...)")

# tipos que não dependem das batidas do dia: (explicação, sugestões)
FIXOS: dict[str, tuple[str, tuple[Sugestao, ...]]] = {
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
		(Sugestao(MANTER, "Manter"),),
	),
	"sete_dias_seguidos": (
		"Trabalhou 7 dias seguidos sem descanso semanal (CLT, art. 67).",
		(Sugestao(MANTER, "Manter: o 7º dia é pago em dobro"),),
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
	"alteracao_jornada": (
		"Alteração do horário fixo parada: recusa, prazo vencido ou horário ainda não criado no Secullum.",
		(Sugestao(DESK, "Abrir a alteração de jornada"),),
	),
	"envio_horario_secullum": (
		"O novo horário vale no programa, mas o Secullum recusou ou não respondeu o envio.",
		(
			Sugestao(SECULLUM, "Trocar o horário direto no Secullum"),
			Sugestao(DESK, "Ver a alteração de jornada"),
		),
	),
	"escala_nao_publicada": (
		"A escala do dia foi mudada no cockpit e não foi publicada: o colaborador não sabe e a apuração usa a antiga.",
		(Sugestao(DESK, "Publicar ou descartar no cockpit de escalas"),),
	),
	# docs/PRD-termo-ocorrencias.md
	"termo_sem_gerente": (
		"O colaborador não tem gestor (Reporta a) ou o gestor não tem e-mail: o termo foi para o e-mail do RH.",
		(Sugestao(DESK, "Preencher o Reporta a no cadastro"),),
	),
	"termo_nao_assinado": (
		"O termo de ocorrências passou do prazo sem a assinatura registrada; o gestor é cobrado todo dia útil.",
		(Sugestao(DESK, "Abrir o termo de ocorrências"),),
	),
	"email_termo_nao_enviado": (
		"O e-mail com o termo não saiu (conta de e-mail de saída ausente ou recusada). O termo continua valendo.",
		(Sugestao(DESK, "Conferir a conta de e-mail (Email Account) e reenviar o termo"),),
	),
	"alteracao_periodo_fechado": (
		"O Secullum mudou um dado de um dia de período já fechado: a mudança não entrou na apuração.",
		(Sugestao(DESK, "Reabrir o fechamento, se a mudança precisar valer"), Sugestao(MANTER, "Manter")),
	),
}

COBRAR = Sugestao(COBRAR_WHATSAPP, "Cobrar pelo WhatsApp")
FOLGA = Sugestao(FOLGA_COMPENSATORIA, "Dar folga compensatória (Escala do mês)")

DO_DIA = ("marcacao_impar", "marcacao_duplicada", "falta", "intrajornada", "atraso", "he_acima_limite")
TIPOS = frozenset(FIXOS) | frozenset(DO_DIA)
COM_FOLGA = ("sete_dias_seguidos", "domingos_sem_folga", "descanso_semanal")  # DT-8


# inconsistências do ponto do dia em que vale avisar o colaborador (TI-08): "Cobrar pelo WhatsApp" entra no fim
COBRAVEIS = frozenset(
	{
		"marcacao_impar",
		"marcacao_duplicada",
		"falta",
		"atraso",
		"he_acima_limite",
		"intrajornada",
		"interjornada",
		"intervalo_superior_2h",
		"aula_nao_registrada",
		"sete_dias_seguidos",
		"descanso_semanal",
		"domingos_sem_folga",
		"excesso_jornada_estagio",
		"excesso_jornada_horista",
	}
)


def orientar(tipo: str, contexto: ContextoDia | None = None) -> Orientacao:
	"""Explicação e sugestões para a inconsistência. Tipo desconhecido: sem correção automática."""
	o = _orientar(tipo, contexto or ContextoDia())
	if tipo in COBRAVEIS and COBRAR not in o.sugestoes:
		return Orientacao(o.explicacao, (*o.sugestoes, COBRAR))
	return o


def _orientar(tipo: str, contexto: ContextoDia) -> Orientacao:
	if tipo == "marcacao_impar":
		return _marcacao_impar(contexto)
	if tipo == "marcacao_duplicada":
		return _marcacao_duplicada(contexto)
	if tipo == "falta":
		return _falta(contexto)
	if tipo == "intrajornada":
		return _intrajornada(contexto)
	if tipo == "atraso":
		return _atraso(contexto)
	if tipo == "he_acima_limite":
		return _he_acima_limite(contexto)
	if tipo in FIXOS:
		explicacao, sugestoes = FIXOS[tipo]
		if tipo in COM_FOLGA:
			sugestoes = (*sugestoes, FOLGA)
		return Orientacao(explicacao, sugestoes)
	return Orientacao("Sem correção automática: confira no Desk.", (Sugestao(DESK, "Abrir no Desk"),))


def _minutos(contexto: ContextoDia) -> list[int]:
	return sorted(b.minuto for b in contexto.batidas)


def _marcacao_impar(contexto: ContextoDia) -> Orientacao:
	minutos = _minutos(contexto)
	sugestoes = []
	previsto = sugerir_horario(contexto.previsto, minutos)
	if previsto is not None:
		sugestoes.append(Sugestao(INCLUIR, f"Inserir a batida prevista {hhmm(previsto)}", minuto=previsto))
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
	sugestoes = [ABONAR_DIA, Sugestao(ATESTADO, "Lançar atestado")]
	completa = jornada_completa(contexto.previsto)
	if completa:
		sugestoes.append(
			Sugestao(
				JORNADA_COMPLETA,
				f"Preencher a jornada prevista ({hhmm(completa[0])} a {hhmm(completa[-1])}): esqueceu de bater",
				minutos=completa,
			)
		)
	sugestoes.append(Sugestao(MANTER, texto_manter_falta(contexto)))
	return Orientacao("Não há batida num dia de trabalho previsto.", tuple(sugestoes))


def texto_manter_falta(contexto: ContextoDia) -> str:
	"""DT-4: o que a apuração já faz com a falta sem tratamento."""
	if not contexto.horista:
		return "Manter a falta: desconta o dia e o DSR da semana (Lei 605/49, art. 6º)"
	if contexto.falta_horista_desconta_dsr:
		return "Manter a falta: o horista não recebe as horas do dia nem o DSR proporcional"
	return "Manter a falta: o horista não recebe as horas do dia"


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
		termo = intervalo_do_termo(minutos, contexto)
		if termo:
			rotulo = f"Incluir o intervalo do termo assinado ({hhmm(termo[0])} às {hhmm(termo[1])})"
			sugestoes.insert(0, Sugestao(INCLUIR_INTERVALO, rotulo, minutos=termo))
	return Orientacao(texto + ".", tuple(sugestoes))


def _atraso(contexto: ContextoDia) -> Orientacao:
	destino = "é debitado do banco de horas" if contexto.banco_atraso else "é descontado na folha"
	return Orientacao(
		"Chegou depois do horário previsto ou saiu antes, além da tolerância.",
		(
			Sugestao(ABONO_PARCIAL, "Abonar só os minutos do atraso"),
			ABONAR_DIA,
			CORRIGIR_BATIDA,
			Sugestao(MANTER, f"Manter: o atraso {destino}"),
		),
	)


def _he_acima_limite(contexto: ContextoDia) -> Orientacao:
	destino = "vão para o banco de horas" if contexto.banco_he else "são pagas como hora extra na folha"
	return Orientacao(
		"Fez mais hora extra no dia do que o limite da CCT (CLT, art. 59: até 2 h).",
		(
			CORRIGIR_BATIDA,
			Sugestao(MANTER, f"Manter: as horas {destino}; confira a autorização da hora extra"),
		),
	)


# ------------------------------------------------------------------ pré-preenchimento (TI-05)


def jornada_completa(previsto: Sequence[Par]) -> tuple[int, ...]:
	"""Todas as batidas previstas do dia, na ordem (DT-9)."""
	return tuple(p for inicio, fim in sorted(previsto) for p in (int(inicio), int(fim)))


def intervalo_exigido(trabalhado: int, contexto: ContextoDia) -> int:
	"""Intervalo do art. 71 para a jornada trabalhada (o mínimo da CCT acima de 6h)."""
	if trabalhado > contexto.jornada_intervalo_curto_ate:
		return contexto.intervalo_minimo
	if trabalhado > contexto.jornada_sem_intervalo_ate:
		return contexto.intervalo_curto
	return 0


def intervalo_do_termo(minutos: Sequence[int], contexto: ContextoDia) -> tuple[int, int] | None:
	"""DT-10: saída e volta do intervalo do termo no meio do expediente, com o intervalo exigido pela jornada do dia
	(07:00-17:00 -> 12:00 às 13:00). Só no dia sem nenhuma pausa (entrada e saída): se já houve pausa, mesmo curta,
	o termo não é sugerido (decisão do RH, 28/10/2026) — fica Corrigir batida, Manter ou Cobrar."""
	marcas = sorted(int(m) for m in minutos)
	if len(marcas) != 2:
		return None
	inicio, fim = marcas
	exigido = intervalo_exigido(fim - inicio, contexto)
	if not exigido:
		return None
	meio = inicio + (fim - inicio) // 2
	if meio + exigido >= fim:
		return None
	return (meio, meio + exigido)


def orientar_varios(tipos: Sequence[str], contexto: ContextoDia | None = None) -> dict[str, Orientacao]:
	return {tipo: orientar(tipo, contexto) for tipo in tipos}
