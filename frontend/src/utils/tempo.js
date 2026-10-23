// Formatação de tempo (só exibição: os números vêm prontos do servidor).

export function hhmm(minutos) {
	if (minutos === null || minutos === undefined || minutos === "") return "—";
	const total = Math.round(Number(minutos));
	const sinal = total < 0 ? "-" : "";
	const absoluto = Math.abs(total);
	const horas = Math.floor(absoluto / 60);
	return `${sinal}${String(horas).padStart(2, "0")}:${String(absoluto % 60).padStart(2, "0")}`;
}

export function porExtenso(minutos) {
	if (minutos === null || minutos === undefined || minutos === "") return "sem valor";
	const total = Math.abs(Math.round(Number(minutos)));
	const horas = Math.floor(total / 60);
	const resto = total % 60;
	const partes = [];
	if (horas) partes.push(`${horas} ${horas === 1 ? "hora" : "horas"}`);
	if (resto || !horas) partes.push(`${resto} ${resto === 1 ? "minuto" : "minutos"}`);
	return (Number(minutos) < 0 ? "menos " : "") + partes.join(" e ");
}

export function competenciaAtual() {
	const hoje = new Date();
	return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}`;
}

const MESES = [
	"janeiro",
	"fevereiro",
	"março",
	"abril",
	"maio",
	"junho",
	"julho",
	"agosto",
	"setembro",
	"outubro",
	"novembro",
	"dezembro",
];

export function nomeDaCompetencia(competencia) {
	const [ano, mes] = String(competencia || "").split("-");
	return MESES[Number(mes) - 1] ? `${MESES[Number(mes) - 1]} de ${ano}` : competencia;
}

export function dataBR(iso) {
	if (!iso) return "—";
	const [ano, mes, dia] = String(iso).slice(0, 10).split("-");
	return `${dia}/${mes}/${ano}`;
}
