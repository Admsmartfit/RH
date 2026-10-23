import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica
from hrms_secullum_brasil.configuracao_ponto.regras import (
	carregar_perfis,
	titulo_com_vigencia,
	validar_datas_vigencia,
	validar_edicao_em_periodo_fechado,
	validar_sem_sobreposicao,
)
from hrms_secullum_brasil.engine import defaults_legais
from hrms_secullum_brasil.engine.jornada_prevista import (
	intervalos,
	minutos_do_dia,
	minutos_previstos,
	montar_periodos,
)

TIPOS_COM_HORARIO_OBRIGATORIO = ("Fixa", "Fragmentada")


def _par(linha, n: int) -> tuple[int | None, int | None]:
	return minutos_do_dia(linha.get(f"entrada{n}")), minutos_do_dia(linha.get(f"saida{n}"))


CAMPOS_HORARIO = [f"{tipo}{n}" for n in (1, 2, 3) for tipo in ("entrada", "saida")]


class PerfildeJornada(Document):
	def before_validate(self):
		for linha in self.dias:
			descartar_hora_automatica(linha, CAMPOS_HORARIO)

	def validate(self):
		validar_edicao_em_periodo_fechado(self, [self.company] if self.company else None)
		validar_datas_vigencia(self)
		self.titulo = titulo_com_vigencia(self.codigo, self.vigencia_inicio, self.vigencia_fim)
		erros = self._calcular_dias()
		if cint(self.divisor) <= 0:
			erros.append(_("O divisor deve ser maior que zero."))
		if self.tipo in TIPOS_COM_HORARIO_OBRIGATORIO and not self.minutos_semana_previstos:
			erros.append(
				_("Perfil do tipo {0} precisa de horário previsto em pelo menos um dia.").format(self.tipo)
			)
		if erros:
			frappe.throw(erros, title=_("Perfil de Jornada inválido"), as_list=True)

		validar_sem_sobreposicao(
			self,
			carregar_perfis({"codigo": self.codigo, "name": ["!=", self.name]}),
			escopo=_("código {0}").format(self.codigo),
		)
		self._avisar_carga_semanal()
		self._avisar_intervalo_estendido()

	def _calcular_dias(self) -> list[str]:
		erros = []
		vistos = set()
		total = 0
		self._maior_intervalo = 0
		for linha in self.dias:
			if linha.dia_semana in vistos:
				erros.append(_("{0} aparece mais de uma vez.").format(linha.dia_semana))
			vistos.add(linha.dia_semana)
			pares = [_par(linha, n) for n in (1, 2, 3)]
			periodos, erros_dia = montar_periodos(pares)
			erros += [f"{linha.dia_semana}: {e}" for e in erros_dia]
			self._maior_intervalo = max([self._maior_intervalo, *intervalos(periodos)])
			linha.minutos_previstos = 0 if cint(linha.neutro) else minutos_previstos(periodos)
			total += linha.minutos_previstos
		self.minutos_semana_previstos = total
		return erros

	def _avisar_carga_semanal(self):
		carga = cint(self.carga_semanal_minutos)
		if carga > defaults_legais.CARGA_SEMANAL_MAXIMA_MIN:
			frappe.msgprint(
				_("Carga semanal de {0} min ultrapassa 44h (Art. 7º, XIII CF).").format(carga),
				title=_("Atenção: risco jurídico"),
				indicator="orange",
			)
		if carga and self.minutos_semana_previstos and carga != self.minutos_semana_previstos:
			frappe.msgprint(
				_("A carga semanal ({0} min) difere do total dos horários previstos ({1} min).").format(
					carga, self.minutos_semana_previstos
				),
				indicator="orange",
			)

	def _avisar_intervalo_estendido(self):
		"""Jornada fragmentada (instrutores): intervalo > 2h só com acordo escrito ou CCT (Art. 71; PRD 5.5)."""
		limite = defaults_legais.INTERVALO_MAXIMO_MIN
		if self._maior_intervalo > limite and not self.permite_intervalo_estendido:
			frappe.msgprint(
				_(
					'O perfil tem intervalo de {0} min, acima de {1} min, sem "Permite intervalo superior a 2h". '
					"Cada dia apurado gerará a inconsistência intervalo_superior_2h, salvo se o cargo tiver "
					'"Jornada fragmentada" na CCT.'
				).format(self._maior_intervalo, limite),
				title=_("Atenção: risco jurídico"),
				indicator="orange",
			)
