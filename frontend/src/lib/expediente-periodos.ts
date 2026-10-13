// Expediente — regras PURAS da tela de configuração (sem DOM, sem alias de import em runtime): normalizar/validar/ordenar períodos, resumir o dia e montar o envio.
// `npm run test:expediente`. A tela só desenha; as decisões ficam aqui para serem testadas de verdade.
import type { DiaSemana, DiaSemanaWrite, JanelaDia, PeriodoExpediente } from "../types/regra-expediente.ts";

export const DIAS_ORDEM: DiaSemana[] = [0, 1, 2, 3, 4, 5, 6];
export const DIAS_NOME: Record<DiaSemana, string> = {
  0: "Segunda",
  1: "Terça",
  2: "Quarta",
  3: "Quinta",
  4: "Sexta",
  5: "Sábado",
  6: "Domingo",
};
export const DIAS_SIGLA: Record<DiaSemana, string> = { 0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom" };

/** Mesmo teto do backend (MAX_PERIODOS_POR_DIA). */
export const MAX_PERIODOS_POR_DIA = 8;

/** "09:00:00" (API) ou "09:00" → "09:00". Vazio/ inválido → "". */
export function normalizarHora(valor: string | null | undefined): string {
  if (!valor) return "";
  const partes = valor.split(":");
  if (partes.length < 2) return "";
  const [h, m] = partes;
  return /^\d{1,2}$/.test(h) && /^\d{2}$/.test(m) ? `${h.padStart(2, "0")}:${m}` : "";
}

export function paraMinutos(hora: string): number {
  const [h, m] = hora.split(":").map(Number);
  return h * 60 + m;
}

export function normalizarPeriodo(periodo: PeriodoExpediente): PeriodoExpediente {
  return { inicio: normalizarHora(periodo.inicio), fim: normalizarHora(periodo.fim) };
}

/** Ordena pelo horário de início (estável para início igual: pelo fim). Não muda o original. */
export function ordenarPeriodos(periodos: readonly PeriodoExpediente[]): PeriodoExpediente[] {
  return [...periodos].sort((a, b) => (a.inicio < b.inicio ? -1 : a.inicio > b.inicio ? 1 : a.fim < b.fim ? -1 : a.fim > b.fim ? 1 : 0));
}

/**
 * Valida os períodos de UM dia (a lista pode estar em qualquer ordem): horas preenchidas, início antes do fim (sem atravessar a meia-noite nesta versão), sem
 * sobreposição (períodos que apenas se tocam são aceitos) e dentro do limite. Devolve a PRIMEIRA mensagem de erro, ou `null`.
 */
export function validarPeriodos(periodos: readonly PeriodoExpediente[]): string | null {
  if (periodos.length > MAX_PERIODOS_POR_DIA) return `No máximo ${MAX_PERIODOS_POR_DIA} períodos por dia.`;
  for (const periodo of periodos) {
    if (!periodo.inicio || !periodo.fim) return "Preencha o início e o fim de cada período.";
    if (paraMinutos(periodo.inicio) >= paraMinutos(periodo.fim)) {
      return `O período ${periodo.inicio}–${periodo.fim} precisa começar antes de terminar (não pode atravessar a meia-noite).`;
    }
  }
  const ordenados = ordenarPeriodos(periodos);
  for (let i = 1; i < ordenados.length; i += 1) {
    if (paraMinutos(ordenados[i].inicio) < paraMinutos(ordenados[i - 1].fim)) {
      return `Os períodos ${ordenados[i - 1].inicio}–${ordenados[i - 1].fim} e ${ordenados[i].inicio}–${ordenados[i].fim} se sobrepõem.`;
    }
  }
  return null;
}

/** Erros por dia (só os dias com problema) — o botão Salvar fica desabilitado enquanto houver algum. */
export function errosDaSemana(dias: readonly Pick<JanelaDia, "diaSemana" | "periodos">[]): Partial<Record<DiaSemana, string>> {
  const erros: Partial<Record<DiaSemana, string>> = {};
  for (const dia of dias) {
    const erro = validarPeriodos(dia.periodos);
    if (erro) erros[dia.diaSemana] = erro;
  }
  return erros;
}

/** Sugestão para o botão "+ período": logo depois do último (4 h), ou 08:00–12:00 num dia fechado. Sem espaço no dia (último termina às 23:xx) → `null`. */
export function sugerirNovoPeriodo(periodos: readonly PeriodoExpediente[]): PeriodoExpediente | null {
  if (periodos.length >= MAX_PERIODOS_POR_DIA) return null;
  if (periodos.length === 0) return { inicio: "08:00", fim: "12:00" };
  const ultimo = ordenarPeriodos(periodos)[periodos.length - 1];
  const inicio = paraMinutos(ultimo.fim || "00:00");
  if (inicio >= 23 * 60) return null;
  const fim = Math.min(inicio + 240, 23 * 60 + 59);
  const hhmm = (total: number) => `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  return { inicio: hhmm(inicio), fim: hhmm(fim) };
}

/** "08:00–12:00 · 13:00–18:00" ou "Fechado". */
export function resumoDoDia(periodos: readonly PeriodoExpediente[]): string {
  return periodos.length === 0 ? "Fechado" : ordenarPeriodos(periodos).map((p) => `${p.inicio}–${p.fim}`).join(" · ");
}

/** Horas de trabalho no dia (soma dos períodos), com uma casa. */
export function horasDoDia(periodos: readonly PeriodoExpediente[]): number {
  const minutos = periodos.reduce((soma, p) => (p.inicio && p.fim ? soma + Math.max(0, paraMinutos(p.fim) - paraMinutos(p.inicio)) : soma), 0);
  return Math.round((minutos / 60) * 10) / 10;
}

/** Os 7 dias, sempre completos e em ordem, com horas normalizadas ("HH:MM") — o que a tela edita. */
export function diasNormalizados(dias: readonly Pick<JanelaDia, "diaSemana" | "periodos">[]): { diaSemana: DiaSemana; periodos: PeriodoExpediente[] }[] {
  return DIAS_ORDEM.map((diaSemana) => {
    const dia = dias.find((item) => item.diaSemana === diaSemana);
    return { diaSemana, periodos: ordenarPeriodos((dia?.periodos ?? []).map(normalizarPeriodo)) };
  });
}

/** O corpo `dias` do PATCH: 7 dias, períodos ordenados, nada de campo legado. */
export function diasParaEnvio(dias: readonly Pick<JanelaDia, "diaSemana" | "periodos">[]): DiaSemanaWrite[] {
  return diasNormalizados(dias);
}

/** Fusos oferecidos (IANA). O fuso atual da empresa sempre aparece, mesmo que não esteja na lista. */
export const FUSOS_BRASIL: { value: string; label: string }[] = [
  { value: "America/Sao_Paulo", label: "Brasília (America/Sao_Paulo)" },
  { value: "America/Manaus", label: "Amazonas (America/Manaus)" },
  { value: "America/Cuiaba", label: "Mato Grosso (America/Cuiaba)" },
  { value: "America/Campo_Grande", label: "Mato Grosso do Sul (America/Campo_Grande)" },
  { value: "America/Belem", label: "Pará/Amapá (America/Belem)" },
  { value: "America/Fortaleza", label: "Nordeste (America/Fortaleza)" },
  { value: "America/Recife", label: "Pernambuco (America/Recife)" },
  { value: "America/Bahia", label: "Bahia (America/Bahia)" },
  { value: "America/Porto_Velho", label: "Rondônia (America/Porto_Velho)" },
  { value: "America/Rio_Branco", label: "Acre (America/Rio_Branco)" },
  { value: "America/Noronha", label: "Fernando de Noronha (America/Noronha)" },
];

export function opcoesDeFuso(atual: string): { value: string; label: string }[] {
  return FUSOS_BRASIL.some((fuso) => fuso.value === atual) ? FUSOS_BRASIL : [{ value: atual, label: atual }, ...FUSOS_BRASIL];
}

/** "2026-10-12" → "12/10/2026" (sem passar por `Date`, que deslocaria o dia pelo fuso do navegador). */
export function formatarDataIso(data: string): string {
  const [ano, mes, dia] = data.split("-");
  return ano && mes && dia ? `${dia}/${mes}/${ano}` : data;
}

/** Dia da semana (0 = segunda) de uma data ISO, calculado em UTC — independente do fuso do navegador. */
export function diaDaSemanaDe(data: string): DiaSemana {
  const [ano, mes, dia] = data.split("-").map(Number);
  const js = new Date(Date.UTC(ano, mes - 1, dia)).getUTCDay(); // 0 = domingo
  return ((js + 6) % 7) as DiaSemana;
}

export const TIPO_DIA_ESPECIAL_ROTULO: Record<string, string> = {
  feriado: "Feriado",
  recesso: "Recesso",
  trabalho_excepcional: "Trabalho excepcional",
  ignorado: "Ignorado (sem efeito)",
};

export const TIPO_DIA_ESPECIAL_DESCRICAO: Record<string, string> = {
  feriado: "O dia fica FECHADO.",
  recesso: "O dia fica FECHADO (recesso da empresa).",
  trabalho_excepcional: "O dia usa os períodos informados abaixo, no lugar dos da semana.",
  ignorado: "Neutraliza a data (útil para ignorar um feriado importado): vale a regra da semana.",
};
