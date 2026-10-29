"""Termo de ocorrências de ponto (docs/PRD-termo-ocorrencias.md, TO-04): o que entra no termo, a regularização
proposta de cada dia (a mesma correção que o cartão sugere), o resumo do WhatsApp, os prazos em dias úteis (DO-7) e a
reincidência (DO-11). Puro: as telas e os jobs só gravam e enviam.

Horários em minutos do dia de trabalho, como em engine/cartao_edicao.py.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta

from hrms_secullum_brasil.engine.cartao_edicao import DESCONSIDERAR, INCLUIR, ORIGINAL, Batida, hhmm
from hrms_secullum_brasil.engine.sugestoes import INCLUIR_INTERVALO, MANTER, ContextoDia, orientar

# nome que o colaborador entende (WhatsApp, e-mail e PDF), na ordem em que o dia é regularizado
NOMES = {
	"marcacao_duplicada": "Batida repetida",
	"marcacao_impar": "Batida faltando (entrada ou saída)",
	"intrajornada": "Intervalo não registrado ou menor que o mínimo",
	"falta": "Falta (dia sem batida)",
	"atraso": "Atraso ou saída antecipada",
	"he_acima_limite": "Hora extra acima do limite do dia",
	"interjornada": "Descanso menor que 11 h entre um dia e outro",
	"intervalo_superior_2h": "Intervalo maior que 2 h",
	"aula_nao_registrada": "Aula sem batida",
	"excesso_jornada_estagio": "Estágio acima da jornada do TCE",
}
TIPOS_DO_TERMO = tuple(NOMES)  # uma linha a confirmar por dia
# da semana ou do mês, sem um dia a corrigir: só como informação no texto (seção 6)
INFORMATIVOS = {
	"sete_dias_seguidos": "7 dias seguidos de trabalho",
	"descanso_semanal": "Descanso semanal menor que 35 h",
	"domingos_sem_folga": "Domingos seguidos sem folga",
	"excesso_jornada_horista": "Mais de 4 h sem intervalo além do limite do mês",
}
CIENTE = "Ciente — mantém o registro"

DE_ACORDO = "De acordo"
ALTERADO = "Alterado"
NAO_RECONHECE = "Não reconhece"
JA_RESOLVIDO = "Já resolvido"
PERIODO_FECHADO = "Período fechado"
RESPOSTAS = (DE_ACORDO, ALTERADO, NAO_RECONHECE)

PRAZO_DIAS_UTEIS = 3
AVISO_RH_DIAS_UTEIS = 10
REINCIDENCIA_LIMITE = 3
REINCIDENCIA_JANELA_DIAS = 90


@dataclass(frozen=True)
class Proposta:
	texto: str
	# o dia inteiro depois da correção; None = ciente, sem mudar o ponto
	horarios: tuple[int, ...] | None = None
	intervalo: tuple[int, int] | None = None  # o intervalo do termo incluído (entra com o motivo do termo)


@dataclass(frozen=True)
class DiaTermo:
	data: date
	ocorrencias: tuple[tuple[str, str], ...]  # (nome da Inconsistencia de Ponto, tipo)
	contexto: ContextoDia


@dataclass(frozen=True)
class ItemTermo:
	data: date
	tipos: tuple[str, ...]
	inconsistencias: tuple[str, ...]
	marcacoes: tuple[int, ...]
	proposta: Proposta


def entra_no_termo(tipo: str) -> bool:
	return tipo in NOMES


def _com_batidas(contexto: ContextoDia, minutos: Sequence[int]) -> ContextoDia:
	antigas = {b.minuto: b for b in contexto.batidas}
	return replace(
		contexto,
		batidas=tuple(antigas.get(m) or Batida(m, ORIGINAL, f"proposta-{m}") for m in sorted(minutos)),
	)


def _ciente(tipo: str, contexto: ContextoDia) -> str:
	"""O "Manter" do cartão dito como ciência (ex.: "Ciente: o atraso é descontado na folha")."""
	manter = next((s for s in orientar(tipo, contexto).sugestoes if s.acao == MANTER), None)
	if not manter:
		return CIENTE
	texto = manter.rotulo
	if texto.startswith("Manter a "):
		return "Ciente da " + texto[len("Manter a ") :]
	if texto.startswith("Manter"):
		return "Ciente" + texto[len("Manter") :]
	return CIENTE


def propor_dia(tipos: Iterable[str], contexto: ContextoDia) -> Proposta:
	"""A regularização do dia, na ordem: tira a batida repetida, põe a que falta (a prevista) e inclui o intervalo do
	termo no dia sem pausa (DT-10). Falta e atraso não têm horário a propor: ficam como ciência (DO-3)."""
	minutos = sorted(b.minuto for b in contexto.batidas)
	partes = []
	intervalo = None
	ordem = sorted(set(tipos), key=lambda t: TIPOS_DO_TERMO.index(t) if t in NOMES else len(NOMES))
	for tipo in ordem:
		atual = _com_batidas(contexto, minutos)
		sugestoes = orientar(tipo, atual).sugestoes
		if tipo == "marcacao_duplicada":
			repetidas = [s.minuto for s in sugestoes if s.acao == DESCONSIDERAR and s.minuto is not None]
			if repetidas:
				for m in repetidas:
					minutos.remove(m)
				partes.append("Desconsiderar a batida repetida " + ", ".join(hhmm(m) for m in repetidas))
				continue
		elif tipo == "marcacao_impar":
			prevista = next((s.minuto for s in sugestoes if s.acao == INCLUIR and s.minuto is not None), None)
			if prevista is not None:
				minutos = sorted([*minutos, prevista])
				partes.append(f"Incluir a batida prevista {hhmm(prevista)}")
				continue
		elif tipo == "intrajornada":
			termo = next((s.minutos for s in sugestoes if s.acao == INCLUIR_INTERVALO and s.minutos), None)
			if termo:
				minutos = sorted([*minutos, *termo])
				intervalo = (termo[0], termo[1])
				partes.append(f"Incluir o intervalo {hhmm(termo[0])} às {hhmm(termo[1])}")
				continue
		partes.append(_ciente(tipo, atual))
	originais = tuple(sorted(b.minuto for b in contexto.batidas))
	horarios = tuple(minutos)
	return Proposta("; ".join(partes) or CIENTE, horarios if horarios != originais else None, intervalo)


def montar_itens(dias: Iterable[DiaTermo]) -> list[ItemTermo]:
	"""Uma linha por dia com as ocorrências que cabem no termo; o resto fica de fora (seção 6)."""
	itens = []
	for dia in sorted(dias, key=lambda d: d.data):
		do_termo = [(nome, tipo) for nome, tipo in dia.ocorrencias if entra_no_termo(tipo)]
		if not do_termo:
			continue
		tipos = tuple(sorted({t for _, t in do_termo}, key=TIPOS_DO_TERMO.index))
		itens.append(
			ItemTermo(
				data=dia.data,
				tipos=tipos,
				inconsistencias=tuple(nome for nome, _ in do_termo),
				marcacoes=tuple(sorted(b.minuto for b in dia.contexto.batidas)),
				proposta=propor_dia(tipos, dia.contexto),
			)
		)
	return itens


def data_curta(data: date) -> str:
	return data.strftime("%d/%m")


def resumo_ocorrencias(
	itens: Sequence[ItemTermo], informativos: Iterable[tuple[str, date | None]] = ()
) -> str:
	"""As ocorrências por tipo com os dias ("• Batida faltando (entrada ou saída): 02/10, 05/10"), para o WhatsApp e o
	e-mail. As informativas entram no fim, sem dias a confirmar."""
	por_tipo: dict[str, list[date]] = {}
	for item in itens:
		for tipo in item.tipos:
			por_tipo.setdefault(tipo, []).append(item.data)
	linhas = [
		f"• {NOMES[tipo]}: {', '.join(data_curta(d) for d in sorted(set(datas)))}"
		for tipo, datas in sorted(por_tipo.items(), key=lambda x: TIPOS_DO_TERMO.index(x[0]))
	]
	vistos = []
	for tipo, _data in informativos:
		if tipo in INFORMATIVOS and tipo not in vistos:
			vistos.append(tipo)
	linhas += [f"• {INFORMATIVOS[tipo]}" for tipo in vistos]
	return "\n".join(linhas)


def texto_marcacoes(minutos: Sequence[int]) -> str:
	return " ".join(hhmm(m) for m in minutos) or "sem batida"


# ------------------------------------------------------------------ prazos em dias úteis (DO-7)


def dia_util(data: date, feriados: set[date]) -> bool:
	return data.weekday() < 5 and data not in feriados


def dias_uteis_entre(inicio: date, fim: date, feriados: set[date]) -> int:
	"""Dias úteis depois de `inicio` até `fim` (inclusive). A emissão não conta."""
	total, dia = 0, inicio + timedelta(days=1)
	while dia <= fim:
		total += dia_util(dia, feriados)
		dia += timedelta(days=1)
	return total


def somar_dias_uteis(inicio: date, dias: int, feriados: set[date]) -> date:
	"""O n-ésimo dia útil depois de `inicio` (o prazo final para assinar)."""
	dia = inicio
	while dias > 0:
		dia += timedelta(days=1)
		dias -= dia_util(dia, feriados)
	return dia


GERENTE = "gerente"
RH = "rh"


def avisos_do_dia(
	emissao: date,
	hoje: date,
	feriados: set[date],
	rh_avisado: bool = False,
	prazo: int = PRAZO_DIAS_UTEIS,
	aviso_rh: int = AVISO_RH_DIAS_UTEIS,
) -> tuple[str, ...]:
	"""Quem cobrar hoje: o gerente todo dia útil depois do prazo; o RH uma vez, no dia útil `aviso_rh` (ou no
	primeiro dia útil depois, se o job não rodou). Fim de semana e feriado: ninguém."""
	if not dia_util(hoje, feriados):
		return ()
	passados = dias_uteis_entre(emissao, hoje, feriados)
	avisos = []
	if passados > prazo:
		avisos.append(GERENTE)
	if passados >= aviso_rh and not rh_avisado:
		avisos.append(RH)
	return tuple(avisos)


# ------------------------------------------------------------------ reincidência (DO-11)


def reincidente(
	emissoes: Iterable[date],
	hoje: date,
	limite: int = REINCIDENCIA_LIMITE,
	janela_dias: int = REINCIDENCIA_JANELA_DIAS,
) -> bool:
	"""Chegou ao limite de termos na janela (contando o de hoje, se já está na lista)."""
	if limite <= 0:
		return False
	desde = hoje - timedelta(days=janela_dias)
	return sum(1 for d in emissoes if desde < d <= hoje) >= limite


# ------------------------------------------------------------------ relatório (TO-12)

CONFORME = "Assinado (conforme)"
COM_ALTERACAO = "Assinado (com alteração)"
RECUSADO = "Recusado"
CANCELADO = "Cancelado"
AGUARDANDO = "Aguardando assinatura"


@dataclass(frozen=True)
class TermoResumo:
	employee: str
	status: str
	emitido: date
	confirmado: date | None = None
	tipos: tuple[str, ...] = ()


def estatisticas(termos: Iterable[TermoResumo]) -> dict[str, dict]:
	"""Por colaborador: quantos termos em cada situação, dias até a assinatura (média, corridos), taxa de recusa
	(recusados / respondidos) e os tipos de ocorrência mais frequentes."""
	saida: dict[str, dict] = {}
	for t in termos:
		linha = saida.setdefault(
			t.employee,
			{
				"emitidos": 0,
				"conforme": 0,
				"com_alteracao": 0,
				"recusados": 0,
				"cancelados": 0,
				"aguardando": 0,
				"_dias": [],
				"_tipos": {},
			},
		)
		linha["emitidos"] += 1
		chave = {
			CONFORME: "conforme",
			COM_ALTERACAO: "com_alteracao",
			RECUSADO: "recusados",
			CANCELADO: "cancelados",
		}.get(t.status, "aguardando")
		linha[chave] += 1
		if t.status in (CONFORME, COM_ALTERACAO) and t.confirmado:
			linha["_dias"].append((t.confirmado - t.emitido).days)
		for tipo in t.tipos:
			linha["_tipos"][tipo] = linha["_tipos"].get(tipo, 0) + 1
	for linha in saida.values():
		dias = linha.pop("_dias")
		tipos = linha.pop("_tipos")
		respondidos = linha["conforme"] + linha["com_alteracao"] + linha["recusados"]
		linha["dias_medio"] = round(sum(dias) / len(dias), 1) if dias else None
		linha["taxa_recusa"] = round(100 * linha["recusados"] / respondidos, 1) if respondidos else None
		linha["tipos"] = ", ".join(
			f"{NOMES.get(tipo, tipo)} ({n})"
			for tipo, n in sorted(tipos.items(), key=lambda x: (-x[1], x[0]))[:3]
		)
	return saida
