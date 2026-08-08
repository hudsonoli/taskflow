import { EMPRESA_PADRAO_ID, generateId } from "@/lib/ids";
import type { RegraExpediente } from "@/types/regra-expediente";

export { EMPRESA_PADRAO_ID, generateId };

export const regraExpedienteMock: RegraExpediente = {
  id: "regra-expediente-padrao",
  empresaId: EMPRESA_PADRAO_ID,
  ativo: true,
  manhaInicio: "09:00",
  manhaFim: "12:00",
  tardeInicio: "14:00",
  tardeFim: "19:00",
  toleranciaRetomadaMinutos: 30,
  createdAt: "2026-08-02T09:00:00-03:00",
  updatedAt: "2026-08-02T09:00:00-03:00",
};

function paraMinutos(horaMinuto: string): number {
  const [horas, minutos] = horaMinuto.split(":").map(Number);
  return horas * 60 + minutos;
}

function formatarMinutos(totalMinutos: number): string {
  const normalizado = ((totalMinutos % 1440) + 1440) % 1440;
  const horas = Math.floor(normalizado / 60);
  const minutos = normalizado % 60;
  return `${String(horas).padStart(2, "0")}:${String(minutos).padStart(2, "0")}`;
}

/** Início efetivo do bloco da tarde, considerando a tolerância de retomada antecipada. */
export function tardeInicioEfetivo(regra: RegraExpediente): string {
  return formatarMinutos(paraMinutos(regra.tardeInicio) - regra.toleranciaRetomadaMinutos);
}

/** true quando o horário está dentro de algum bloco de expediente (ou a regra está desativada). */
export function isDentroExpediente(data: Date, regra: RegraExpediente): boolean {
  if (!regra.ativo) return true;

  const minutosAgora = data.getHours() * 60 + data.getMinutes();
  const inicioManha = paraMinutos(regra.manhaInicio);
  const fimManha = paraMinutos(regra.manhaFim);
  const inicioTarde = paraMinutos(regra.tardeInicio) - regra.toleranciaRetomadaMinutos;
  const fimTarde = paraMinutos(regra.tardeFim);

  return (minutosAgora >= inicioManha && minutosAgora < fimManha) || (minutosAgora >= inicioTarde && minutosAgora < fimTarde);
}
