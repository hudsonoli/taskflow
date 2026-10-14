// Acesso fora do expediente (Fase Expediente 2) — lógica PURA (sem React; imports relativos para rodar em `node --test`). `npm run test:expediente-acesso`.
//
// O SERVIDOR decide (fuso da empresa, relógio do servidor): o navegador só apresenta. Duas fontes dizem a mesma coisa:
//   • `403 FORA_DO_EXPEDIENTE` em qualquer chamada autenticada do tenant (sessão VÁLIDA; a política recusa o uso agora) — NUNCA vira login (isso é o 401);
//   • `GET /expediente/estado` (o polling único de ~30 s) com `acessoPermitido=false` — a pessoa parada na tela descobre sozinha; e com `acessoPermitido=true` volta
//     sozinha, SEM novo login (o 13:00 é que libera o TRABALHO; o 12:30 só devolve o ACESSO).
import type { DetalheForaDoExpediente, EstadoExpediente } from "../types/regra-expediente.ts";

export const CODIGO_FORA_DO_EXPEDIENTE = "FORA_DO_EXPEDIENTE";

/** O que a tela "Fora do horário de expediente" precisa — vem do 403 ou do estado. */
export type BloqueioExpediente = {
  proximoAcesso: string | null;
  proximoTrabalho: string | null;
  proximoTrabalhoFim: string | null;
  timezone: string | null;
};

/** Corpo de um 403 do proxy → detalhe estruturado, ou `null` se NÃO for o bloqueio de expediente (outros 403 seguem o tratamento normal de cada tela). */
export function detalheDeForaDoExpediente(corpo: unknown): DetalheForaDoExpediente | null {
  if (typeof corpo !== "object" || corpo === null) return null;
  const detail = (corpo as { detail?: unknown }).detail;
  if (typeof detail !== "object" || detail === null) return null;
  const d = detail as Record<string, unknown>;
  if (d.code !== CODIGO_FORA_DO_EXPEDIENTE) return null;
  const texto = (valor: unknown) => (typeof valor === "string" && valor.length > 0 ? valor : null);
  return {
    code: CODIGO_FORA_DO_EXPEDIENTE,
    message: typeof d.message === "string" ? d.message : "Fora do horário de expediente",
    proximoAcesso: texto(d.proximoAcesso),
    proximoTrabalho: texto(d.proximoTrabalho),
    proximoTrabalhoFim: texto(d.proximoTrabalhoFim),
    timezone: texto(d.timezone),
  };
}

export function bloqueioDoDetalhe(detalhe: DetalheForaDoExpediente): BloqueioExpediente {
  return { proximoAcesso: detalhe.proximoAcesso, proximoTrabalho: detalhe.proximoTrabalho, proximoTrabalhoFim: detalhe.proximoTrabalhoFim, timezone: detalhe.timezone };
}

/** O estado do servidor diz que ESTA pessoa está sem acesso agora? */
export function bloqueioDoEstado(estado: EstadoExpediente | null | undefined): BloqueioExpediente | null {
  if (!estado || estado.acessoPermitido !== false) return null;
  return { proximoAcesso: estado.proximoAcesso, proximoTrabalho: estado.proximoTrabalho, proximoTrabalhoFim: estado.proximoTrabalhoFim, timezone: estado.timezone };
}

/**
 * Qual bloqueio mostrar: vale a informação MAIS RECENTE entre o último 403 (`erro.em`) e o último estado do servidor (`estadoEm`). Um poll mais novo que o 403 é a verdade
 * (`acessoPermitido=true` DERRUBA o bloqueio — o acesso voltou, sem novo login; `false` o confirma); um 403 mais novo que o poll vale já (não espera os 30 s).
 */
export function bloqueioVigente(
  estado: EstadoExpediente | null | undefined,
  estadoEm: number,
  erro: { bloqueio: BloqueioExpediente; em: number } | null,
): BloqueioExpediente | null {
  if (erro && (!estado || erro.em >= estadoEm)) return erro.bloqueio;
  return bloqueioDoEstado(estado);
}

function partesNoFuso(iso: string, timezone: string | null) {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return null;
  const formatador = new Intl.DateTimeFormat("pt-BR", {
    timeZone: timezone ?? undefined,
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const partes = Object.fromEntries(formatador.formatToParts(data).map((p) => [p.type, p.value]));
  return { data, diaChave: `${partes.day}/${partes.month}`, dia: `${partes.day}/${partes.month}`, semana: partes.weekday, hora: `${partes.hour}:${partes.minute}` };
}

/** "HH:MM" no fuso da EMPRESA (não do navegador). Vazio se inválido. */
export function horaNoFuso(iso: string | null | undefined, timezone: string | null): string {
  if (!iso) return "";
  return partesNoFuso(iso, timezone)?.hora ?? "";
}

/**
 * "às 12:30" quando é HOJE (no fuso da empresa, em relação a `agora`), senão "na segunda-feira (12/10) às 08:30". `agora` é injetável (testes).
 */
export function quandoNoFuso(iso: string | null | undefined, timezone: string | null, agora: Date = new Date()): string {
  if (!iso) return "";
  const alvo = partesNoFuso(iso, timezone);
  const hoje = partesNoFuso(agora.toISOString(), timezone);
  if (!alvo || !hoje) return "";
  if (alvo.diaChave === hoje.diaChave) return `às ${alvo.hora}`;
  return `na ${alvo.semana} (${alvo.dia}) às ${alvo.hora}`;
}

export type TextosForaDoExpediente = {
  titulo: string;
  /** "Seu próximo acesso estará disponível às 12:30." — `null` quando o servidor não informou. */
  proximoAcesso: string | null;
  /** "Próximo período de trabalho: 13:00–18:00." — `null` quando não informado. */
  proximoTrabalho: string | null;
};

export function textosForaDoExpediente(bloqueio: BloqueioExpediente, agora: Date = new Date()): TextosForaDoExpediente {
  const acesso = bloqueio.proximoAcesso ? quandoNoFuso(bloqueio.proximoAcesso, bloqueio.timezone, agora) : "";
  const inicio = horaNoFuso(bloqueio.proximoTrabalho, bloqueio.timezone);
  const fim = horaNoFuso(bloqueio.proximoTrabalhoFim, bloqueio.timezone);
  let proximoTrabalho: string | null = null;
  if (inicio && fim) {
    const quando = bloqueio.proximoTrabalho ? quandoNoFuso(bloqueio.proximoTrabalho, bloqueio.timezone, agora) : "";
    proximoTrabalho = quando.startsWith("na ") ? `Próximo período de trabalho: ${quando.replace(/^na /, "").replace(/ às .*$/, "")}, ${inicio}–${fim}.` : `Próximo período de trabalho: ${inicio}–${fim}.`;
  }
  return {
    titulo: "Fora do horário de expediente",
    proximoAcesso: acesso ? `Seu próximo acesso estará disponível ${acesso}.` : null,
    proximoTrabalho,
  };
}
