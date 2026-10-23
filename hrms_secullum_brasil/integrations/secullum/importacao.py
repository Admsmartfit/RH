"""Mapeamento puro Secullum → programa (docs/PRD-importacao-secullum.md, IS-05). Sem frappe.

Converte cada resposta do GET do Secullum (formato real em docs/secullum_api.md) em dados do programa, com a lista
de problemas (impedem a importação do registro) e de avisos (importa e mostra na revisão). O lado Frappe
(ingestion/importacao_secullum.py) só grava o que sai daqui.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import pairwise

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.documentos import cpf_valido, pis_valido, somente_digitos
from hrms_secullum_brasil.engine.jornada_prevista import MAX_PERIODOS, minutos_do_dia, montar_periodos

DIAS_SEMANA = (
	"Segunda-feira",
	"Terça-feira",
	"Quarta-feira",
	"Quinta-feira",
	"Sexta-feira",
	"Sábado",
	"Domingo",
)  # DiaSemana 0..6 do Secullum
NASCIMENTO_AUSENTE = date(1900, 1, 1)  # DI-6
INTERVALO_LONGO_MIN = 120
PERCENTUAL_HE_MINIMO = 50  # CF art. 7º, XVI (a CCT do programa recusa menos que isso)
# FaixasExtras.DiaSemana do Secullum → tipo de dia da CCT do programa
TIPOS_DIA_FAIXA = {
	0: d.TIPO_DIA_UTIL,
	1: d.TIPO_DIA_SABADO,
	2: d.TIPO_DIA_DOMINGO,
	3: d.TIPO_DIA_FERIADO,
	4: d.TIPO_DIA_FOLGA,
}
DIVISORES = {2640: 220, 2520: 210, 2400: 200, 2160: 180, 1800: 150}  # carga semanal (min) → divisor

# efeito de uma justificativa/afastamento no ponto do programa
ABONA = "Abona o dia"
FALTA = "Falta"
FERIAS = "Férias"
ATESTADO = "Atestado"
INSS = "Afastamento INSS"
EFEITOS = (ABONA, FALTA, FERIAS, ATESTADO, INSS)

PALAVRAS_SEM_SIGLA = {"LTDA", "ME", "EPP", "SA", "S/A", "DE", "DA", "DO", "DAS", "DOS", "E", "-", "EIRELI"}


# ------------------------------------------------------------------ utilidades


def _sem_acento(texto: str) -> str:
	return "".join(c for c in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(c))


def data_secullum(valor) -> date | None:
	"""'2023-03-01T00:00:00' (ou '2023-03-01') → date; vazio → None."""
	if not valor:
		return None
	return date.fromisoformat(str(valor)[:10])


def _texto(valor) -> str | None:
	texto = str(valor).strip() if valor is not None else ""
	return texto or None


def _hhmm(minutos: int) -> str:
	return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


# ------------------------------------------------------------------ empresa


@dataclass
class EmpresaImportada:
	id_secullum: int | None
	documento: str
	nome: str
	tipo_documento: int
	uf: str | None
	cidade: str | None
	endereco: str | None
	bairro: str | None
	cep: str | None
	telefone: str | None
	inscricao: str | None
	cei: str | None
	codigo_folha: str | None
	desativada: bool
	problemas: list[str] = field(default_factory=list)


def empresa_do_secullum(e: dict) -> EmpresaImportada:
	documento = somente_digitos(e.get("Documento"))
	empresa = EmpresaImportada(
		id_secullum=e.get("Id"),
		documento=documento,
		nome=(_texto(e.get("Nome")) or "").strip(),
		tipo_documento=int(e.get("TipoDocumento") or 0),
		uf=_texto(e.get("Uf")),
		cidade=_texto(e.get("Cidade"))
		if not isinstance(e.get("Cidade"), dict)
		else _texto(e["Cidade"].get("Descricao")),
		endereco=_texto(e.get("Endereco")),
		bairro=_texto(e.get("Bairro")),
		cep=_texto(e.get("Cep")),
		telefone=_texto(e.get("Telefone")),
		inscricao=_texto(e.get("Inscricao")),
		cei=_texto(e.get("CEI") or e.get("Cei")),
		codigo_folha=_texto(e.get("NFolhaEmpresa")),
		desativada=bool(e.get("Desativada")),
	)
	if not empresa.nome:
		empresa.problemas.append("Empresa sem nome no Secullum.")
	if not documento:
		empresa.problemas.append("Empresa sem CNPJ/CPF no Secullum.")
	elif empresa.tipo_documento == 0 and len(documento) != 14:
		empresa.problemas.append(f"CNPJ com {len(documento)} dígitos.")
	return empresa


def sugerir_abbr(nome: str, usados: set[str]) -> str:
	"""Sigla da empresa (exigida pelo ERPNext): iniciais sem LTDA/ME/DE..., sem repetir as já usadas."""
	palavras = [
		p for p in re.split(r"[\s/]+", _sem_acento(nome).upper()) if p and p not in PALAVRAS_SEM_SIGLA
	]
	base = "".join(p[0] for p in palavras if p[0].isalnum())[:5] or "EMP"
	sigla, n = base, 2
	while sigla in usados:
		sigla = f"{base}{n}"
		n += 1
	return sigla


# ------------------------------------------------------------------ horário → perfil de jornada


@dataclass
class DiaPerfil:
	dia_semana: str
	periodos: list[tuple[str, str]]  # [("08:00", "12:00"), ...] até 3
	neutro: bool = False  # rodízio: horários só de referência, sem falta, horas normais se trabalhar


FIXA = "Fixa"
HORISTA = "Horista"


@dataclass
class PerfilImportado:
	numero: int
	codigo: str
	descricao: str
	tipo: str
	dias: list[DiaPerfil]
	carga_semanal_minutos: int
	divisor: int
	hora_virada: int
	permite_intervalo_estendido: bool
	tolerancia_por_marcacao: int
	faixas_he: dict[str, float]  # tipo de dia → percentual (só o que o Secullum configura)
	problemas: list[str] = field(default_factory=list)
	avisos: list[str] = field(default_factory=list)


def divisor_da_carga(carga_semanal_minutos: int) -> int:
	"""44h → 220, 42h → 210, 40h → 200, 36h → 180, 30h → 150; outras: carga em horas x 5 (mínimo 1)."""
	if carga_semanal_minutos in DIVISORES:
		return DIVISORES[carga_semanal_minutos]
	return max(1, round(carga_semanal_minutos / 60 * 5))


def _periodos_do_dia(dia: dict) -> tuple[list[tuple[int | None, int | None]], list[str]]:
	pares, problemas = [], []
	for n in range(1, 6):
		entrada, saida = dia.get(f"Entrada{n}"), dia.get(f"Saida{n}")
		if not entrada and not saida:
			continue
		try:
			pares.append((minutos_do_dia(entrada), minutos_do_dia(saida)))
		except ValueError as exc:
			problemas.append(str(exc))
	return pares, problemas


def perfil_do_horario(h: dict) -> PerfilImportado:
	numero = int(h.get("Numero") or 0)
	perfil = PerfilImportado(
		numero=numero,
		codigo=f"SEC-{numero}",
		descricao=(_texto(h.get("Descricao")) or f"Horário {numero}")[:140],
		tipo=FIXA,
		dias=[],
		carga_semanal_minutos=0,
		divisor=220,
		hora_virada=0,
		permite_intervalo_estendido=False,
		tolerancia_por_marcacao=d.TOLERANCIA_POR_MARCACAO_MIN,
		faixas_he={},
	)
	if not numero:
		perfil.problemas.append("Horário sem número no Secullum.")
	if int(h.get("Tipo") or 0) != 0:
		perfil.avisos.append(f"Horário de tipo {h.get('Tipo')} no Secullum (não semanal): confira os dias.")

	dias = sorted(h.get("Dias") or [], key=lambda x: int(x.get("DiaSemana") or 0))
	com_horario = [x for x in dias if any(x.get(f"Entrada{n}") for n in range(1, 6))]
	if com_horario and all(x.get("Neutro") for x in com_horario):
		# todos os dias com horário são neutros: horista (recebe o trabalhado, sem falta, como no Secullum)
		perfil.tipo = HORISTA
		perfil.divisor = 1  # convenção do programa: salário-base = valor da hora (docs/regras_por_cargo.md)
		perfil.dias = [DiaPerfil(nome, []) for nome in DIAS_SEMANA]
		perfil.avisos.append(
			"Todos os dias são neutros no Secullum: importado como Horista sem semana padrão (paga as horas "
			"trabalhadas, sem falta). Preencha a semana padrão se quiser falta informativa nos dias previstos."
		)
		perfil.faixas_he = _faixas(h)
		return perfil
	tolerancias, viradas = Counter(), Counter()
	for dia in dias:
		indice = int(dia.get("DiaSemana") or 0)
		nome = DIAS_SEMANA[indice] if 0 <= indice < 7 else None
		if not nome:
			perfil.problemas.append(f"DiaSemana {indice} inválido.")
			continue
		pares, problemas = _periodos_do_dia(dia)
		perfil.problemas += [f"{nome}: {p}" for p in problemas]
		neutro = bool(pares and dia.get("Neutro"))
		if not neutro and (int(dia.get("TipoDia") or 0) == 2 or not pares):
			perfil.dias.append(DiaPerfil(nome, []))
			continue
		if len(pares) > MAX_PERIODOS:
			perfil.avisos.append(
				f"{nome}: {len(pares)} períodos no Secullum; importados os {MAX_PERIODOS} primeiros (DI-4)."
			)
			pares = pares[:MAX_PERIODOS]
		periodos, erros = montar_periodos(pares)
		if erros:
			perfil.problemas += [f"{nome}: {e}" for e in erros]
			perfil.dias.append(DiaPerfil(nome, []))
			continue
		perfil.dias.append(DiaPerfil(nome, [(_hhmm(p.inicio), _hhmm(p.fim)) for p in periodos], neutro))
		if neutro:
			# decisão de 19/10/2026: rodízio — sem falta; quem trabalha faz horas normais (HE acima de 8h/44h)
			continue
		for anterior, seguinte in pairwise(periodos):
			if seguinte.inicio - anterior.fim > INTERVALO_LONGO_MIN:
				perfil.permite_intervalo_estendido = True
		perfil.carga_semanal_minutos += sum(p.duracao for p in periodos)
		tolerancia = max(int(dia.get("ToleranciaExtra") or 0), int(dia.get("ToleranciaFalta") or 0))
		if tolerancia:
			tolerancias[tolerancia] += 1
		viradas[int(dia.get("Fechamento") or 0)] += 1

	if (h.get("Opcoes") or {}).get("ToleranciaArtigo58"):
		perfil.tolerancia_por_marcacao = d.TOLERANCIA_POR_MARCACAO_MIN
	elif tolerancias:
		perfil.tolerancia_por_marcacao = tolerancias.most_common(1)[0][0]
	if viradas:
		perfil.hora_virada = viradas.most_common(1)[0][0]
	if perfil.permite_intervalo_estendido:
		perfil.avisos.append(
			"Intervalo maior que 2h: perfil marcado com 'Permite intervalo superior a 2h' (confira o acordo/CCT)."
		)
	perfil.divisor = divisor_da_carga(perfil.carga_semanal_minutos) if perfil.carga_semanal_minutos else 220
	if not perfil.carga_semanal_minutos:
		perfil.avisos.append("Horário sem nenhum dia de trabalho.")

	perfil.faixas_he = _faixas(h)
	return perfil


def _faixas(h: dict) -> dict[str, float]:
	faixas = {}
	for faixa in h.get("FaixasExtras") or []:
		tipo = TIPOS_DIA_FAIXA.get(int(faixa.get("DiaSemana") or 0))
		itens = sorted(faixa.get("Faixas") or [], key=lambda x: int(x.get("Ordem") or 0))
		if tipo and itens and float(itens[0].get("Coluna") or 0) > 1:  # 0 (e 1) = sem percentual configurado
			faixas[tipo] = float(itens[0]["Coluna"])
	return faixas


# ------------------------------------------------------------------ CCT padrão sugerida


@dataclass
class SugestaoCCT:
	tolerancia_por_marcacao: int
	tolerancia_diaria: int
	faixas_he: dict[str, float]
	avisos: list[str] = field(default_factory=list)


def sugestao_de_cct(perfis: list[PerfilImportado]) -> SugestaoCCT:
	"""Tolerância e faixas de HE para a CCT padrão de uma empresa, a partir dos horários usados por ela (DI-5).

	Valor que todos os horários usam entra direto; havendo divergência entra o mais comum, com aviso. O que nenhum
	horário configura fica no padrão legal.
	"""
	sugestao = SugestaoCCT(d.TOLERANCIA_POR_MARCACAO_MIN, d.TOLERANCIA_DIARIA_MIN, {})
	if not perfis:
		return sugestao
	tolerancias = Counter(p.tolerancia_por_marcacao for p in perfis)
	sugestao.tolerancia_por_marcacao = tolerancias.most_common(1)[0][0]
	if len(tolerancias) > 1:
		sugestao.avisos.append(
			f"Horários com tolerâncias diferentes {dict(tolerancias)}: usada a mais comum."
		)
	sugestao.tolerancia_diaria = max(d.TOLERANCIA_DIARIA_MIN, sugestao.tolerancia_por_marcacao * 2)
	for tipo in TIPOS_DIA_FAIXA.values():
		valores = Counter(p.faixas_he[tipo] for p in perfis if tipo in p.faixas_he)
		if not valores:
			continue
		percentual = valores.most_common(1)[0][0]
		if percentual < PERCENTUAL_HE_MINIMO:
			sugestao.avisos.append(
				f"{tipo}: {percentual:g}% no Secullum, abaixo do mínimo legal; usado {PERCENTUAL_HE_MINIMO}%."
			)
			percentual = PERCENTUAL_HE_MINIMO
		sugestao.faixas_he[tipo] = percentual
		if len(valores) > 1:
			sugestao.avisos.append(
				f"{tipo}: percentuais diferentes nos horários {dict(valores)}; usado {percentual:g}%."
			)
	return sugestao


# ------------------------------------------------------------------ funcionário → colaborador


@dataclass
class ColaboradorImportado:
	id_secullum: int
	cpf: str
	nome: str
	first_name: str
	last_name: str
	pis: str | None
	matricula: str | None
	nascimento: date
	nascimento_ausente: bool
	genero: str
	admissao: date | None
	demissao: date | None
	status: str
	empresa_documento: str
	horario_numero: int | None
	departamento: str | None
	funcao: str | None
	email: str | None
	celular: str | None
	rg: str | None
	ctps: str | None
	endereco: str | None
	codigo_holerite: str | None
	motivo_demissao: str | None
	invisivel: bool
	problemas: list[str] = field(default_factory=list)
	avisos: list[str] = field(default_factory=list)


def _descricao(objeto) -> str | None:
	return _texto(objeto.get("Descricao")) if isinstance(objeto, dict) else None


def colaborador_do_secullum(f: dict, motivos_demissao: dict[int, str] | None = None) -> ColaboradorImportado:
	nome = " ".join((_texto(f.get("Nome")) or "").split())
	primeiro, _, resto = nome.partition(" ")
	nascimento = data_secullum(f.get("Nascimento"))
	demissao = data_secullum(f.get("Demissao"))
	empresa = f.get("Empresa") or {}
	horario = f.get("Horario") or {}
	cidade = _descricao(f.get("Cidade"))
	endereco = ", ".join(
		x
		for x in (
			_texto(f.get("Endereco")),
			_texto(f.get("Bairro")),
			cidade,
			_texto(f.get("Uf")),
			_texto(f.get("Cep")),
		)
		if x
	)
	colaborador = ColaboradorImportado(
		id_secullum=int(f.get("Id") or 0),
		cpf=somente_digitos(f.get("Cpf")),
		nome=nome,
		first_name=primeiro,
		last_name=resto,
		pis=somente_digitos(f.get("NumeroPis")) or None,
		matricula=_texto(f.get("NumeroFolha")),
		nascimento=nascimento or NASCIMENTO_AUSENTE,
		nascimento_ausente=nascimento is None,
		genero="Male" if f.get("Masculino") else "Female",
		admissao=data_secullum(f.get("Admissao")),
		demissao=demissao,
		status="Left" if demissao else "Active",
		empresa_documento=somente_digitos(empresa.get("Documento") or f.get("EmpresaCnpjCpf")),
		horario_numero=int(horario["Numero"])
		if horario.get("Numero") is not None
		else f.get("HorarioNumero"),
		departamento=_descricao(f.get("Departamento")) or _texto(f.get("DepartamentoDescricao")),
		funcao=_descricao(f.get("Funcao")) or _texto(f.get("FuncaoDescricao")),
		email=_texto(f.get("Email")),
		celular=somente_digitos(f.get("Celular") or f.get("Telefone"))
		or None,  # o Frappe recusa hífen especial
		rg=_texto(f.get("Rg")),
		ctps=_texto(f.get("Carteira")),
		endereco=endereco or None,
		codigo_holerite=_texto(f.get("CodigoHolerite")),
		motivo_demissao=(motivos_demissao or {}).get(f.get("MotivoDemissaoId"))
		if f.get("MotivoDemissaoId")
		else None,
		invisivel=bool(f.get("Invisivel")),
	)
	if not colaborador.id_secullum:
		colaborador.problemas.append("Funcionário sem Id no Secullum.")
	if not nome:
		colaborador.problemas.append("Funcionário sem nome.")
	if not colaborador.cpf:
		colaborador.problemas.append("Funcionário sem CPF no Secullum.")
	elif not cpf_valido(colaborador.cpf):
		colaborador.problemas.append("CPF inválido no Secullum.")
	if not colaborador.admissao:
		colaborador.problemas.append("Funcionário sem data de admissão.")
	if not colaborador.empresa_documento:
		colaborador.problemas.append("Funcionário sem empresa.")
	if colaborador.horario_numero is None:
		colaborador.problemas.append("Funcionário sem horário.")
	if colaborador.pis and not pis_valido(colaborador.pis):
		# PIS não é obrigatório: entra sem ele e o RH corrige no Secullum
		colaborador.avisos.append(
			f"PIS inválido no Secullum (final {colaborador.pis[-4:]}): importado sem PIS."
		)
		colaborador.pis = None
	if not colaborador.funcao:
		colaborador.avisos.append("Funcionário sem função (cargo).")
	if colaborador.nascimento_ausente:
		colaborador.avisos.append("Sem data de nascimento no Secullum: importado com 01/01/1900 (DI-6).")
	return colaborador


def selecionar_vinculos(funcionarios: list[dict], hoje: date, meses_demitidos: int = 12) -> list[dict]:
	"""Ativos e demitidos nos últimos `meses_demitidos` meses (DI-7)."""
	limite = hoje - timedelta(days=round(meses_demitidos * 30.44))
	saida = []
	for f in funcionarios:
		demissao = data_secullum(f.get("Demissao"))
		if demissao is None or demissao >= limite:
			saida.append(f)
	return saida


# ------------------------------------------------------------------ estruturas → hierarquia


def hierarquia_das_estruturas(estruturas: list[dict]) -> tuple[dict[str, str], list[str]]:
	"""{CPF do colaborador: CPF do chefe} e avisos. O chefe é o primeiro responsável da estrutura; o responsável de
	uma estrutura filha responde ao responsável da estrutura pai."""
	responsavel: dict[str, str] = {}
	avisos: list[str] = []
	for e in estruturas:
		cpfs = [
			somente_digitos(r.get("Cpf"))
			for r in e.get("Responsaveis") or []
			if somente_digitos(r.get("Cpf"))
		]
		if cpfs:
			responsavel[e.get("Descricao")] = cpfs[0]
		else:
			avisos.append(f"Estrutura '{e.get('Descricao')}' sem responsável com CPF.")
	chefes: dict[str, str] = {}
	for e in estruturas:
		chefe = responsavel.get(e.get("Descricao"))
		if not chefe:
			continue
		for vinculado in e.get("FuncionariosVinculados") or []:
			cpf = somente_digitos(vinculado.get("Cpf"))
			if cpf and cpf != chefe:
				chefes[cpf] = chefe
		pai = responsavel.get(e.get("EstruturaPaiDescricao"))
		if pai and pai != chefe:
			chefes[chefe] = pai
	return chefes, avisos


# ------------------------------------------------------------------ justificativas e afastamentos


def efeito_da_justificativa(j: dict) -> str:
	"""Efeito no ponto do programa, pelas opções e pelo nome da justificativa (o RH confere na revisão)."""
	nome = _sem_acento(f"{j.get('NomeAbreviado') or ''} {j.get('NomeCompleto') or ''}").upper()
	abreviado = _sem_acento(j.get("NomeAbreviado") or "").upper().strip()
	if j.get("LancarComoHorasFalta") or abreviado == "FALTA":
		return FALTA
	if "ATEST" in nome:
		return ATESTADO
	if "AUXDOEN" in nome or "AUXILIO DOENCA" in nome or "INSS" in nome:
		return INSS
	if "FERIAS" in nome:
		return FERIAS
	return ABONA


@dataclass
class AfastamentoImportado:
	chave: str
	id_secullum: int | None
	cpf: str
	pis: str | None
	inicio: date
	fim: date
	justificativa: str
	efeito: str
	data_inclusao: date | None
	problemas: list[str] = field(default_factory=list)


def afastamento_do_secullum(a: dict, efeitos: dict[str, str]) -> AfastamentoImportado:
	"""O texto livre "Motivo" do Secullum não é importado: pode ter dado de saúde (LGPD, minimização)."""
	cpf = somente_digitos(a.get("Cpf"))
	inicio = data_secullum(a.get("Inicio"))
	fim = data_secullum(a.get("Fim")) or inicio
	justificativa = (_texto(a.get("JustificativaNome")) or "").strip()
	afastamento = AfastamentoImportado(
		chave=f"{cpf}|{inicio}|{fim}",
		id_secullum=a.get("Id"),
		cpf=cpf,
		pis=somente_digitos(a.get("NumeroPis")) or None,
		inicio=inicio or date.min,
		fim=fim or date.min,
		justificativa=justificativa,
		efeito=efeitos.get(justificativa, ABONA),
		data_inclusao=data_secullum(a.get("DataInclusao")),
	)
	if not cpf:
		afastamento.problemas.append("Afastamento sem CPF.")
	if not inicio:
		afastamento.problemas.append("Afastamento sem data de início.")
	elif fim < inicio:
		afastamento.problemas.append("Afastamento com fim antes do início.")
	if justificativa and justificativa not in efeitos:
		afastamento.problemas.append(f"Justificativa '{justificativa}' não encontrada no Secullum.")
	return afastamento
