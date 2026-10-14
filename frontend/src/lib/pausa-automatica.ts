// Aviso "Tarefas pausadas automaticamente." (Fase Expediente 3) — lógica PURA (sem React; imports relativos para `node --test`). `npm run test:pausa-automatica`.
//
// A FONTE é o servidor: `GET /expediente/estado` devolve `ultimaPausaAutomatica` ({ eventoId, em, quantidade }) só quando ALGUMA Demanda DESTA pessoa foi realmente pausada
// pelo tick (sem pausa, sem evento, sem aviso). O front só decide se mostra: evento NOVO (id ainda não apresentado), RECENTE (comparando `em` com `agora` do SERVIDOR —
// nunca o relógio do navegador) e com quantidade > 0. A segurança NÃO depende do localStorage: ele só evita repetir o aviso a cada poll/recarga.
import type { UltimaPausaAutomatica } from "../types/regra-expediente.ts";

export const MENSAGEM_PAUSA_AUTOMATICA = "Tarefas pausadas automaticamente.";
export const JANELA_RECENTE_MS = 10 * 60 * 1000;

const PREFIXO_CHAVE = "taskflow.pausaAutomatica.ultimoEvento.";

/** O evento é recente? `em` (instante do corte) comparado com `agoraServidor`, os dois vindos do SERVIDOR. Futuro (relógios dessincronizados) também conta como recente. */
export function pausaRecente(ultima: UltimaPausaAutomatica | null | undefined, agoraServidor: string | null | undefined): boolean {
  if (!ultima || !agoraServidor) return false;
  const em = Date.parse(ultima.em);
  const agora = Date.parse(agoraServidor);
  if (Number.isNaN(em) || Number.isNaN(agora)) return false;
  return agora - em <= JANELA_RECENTE_MS;
}

/** O `eventoId` a avisar agora, ou `null`: evento existente, quantidade > 0, recente e ainda não apresentado. */
export function eventoParaAvisar(
  ultima: UltimaPausaAutomatica | null | undefined,
  agoraServidor: string | null | undefined,
  jaApresentado: string | null,
): string | null {
  if (!ultima || !ultima.eventoId || !(ultima.quantidade > 0)) return null;
  if (!pausaRecente(ultima, agoraServidor)) return null;
  return ultima.eventoId === jaApresentado ? null : ultima.eventoId;
}

type ArmazenamentoMinimo = { getItem(chave: string): string | null; setItem(chave: string, valor: string): void };

// Fallback quando o localStorage não existe/falha (navegação privada, bloqueado, SSR): memória da sessão da página.
const memoriaDaSessao = new Map<string, string>();

function armazenamentoDoNavegador(): ArmazenamentoMinimo | null {
  try {
    return typeof window !== "undefined" && window.localStorage ? window.localStorage : null;
  } catch {
    return null;
  }
}

export function lerEventoApresentado(usuarioId: string, armazenamento: ArmazenamentoMinimo | null = armazenamentoDoNavegador()): string | null {
  const chave = PREFIXO_CHAVE + usuarioId;
  try {
    const valor = armazenamento?.getItem(chave);
    if (valor) return valor;
  } catch {
    // cai na memória
  }
  return memoriaDaSessao.get(chave) ?? null;
}

export function gravarEventoApresentado(usuarioId: string, eventoId: string, armazenamento: ArmazenamentoMinimo | null = armazenamentoDoNavegador()): void {
  const chave = PREFIXO_CHAVE + usuarioId;
  memoriaDaSessao.set(chave, eventoId); // sempre: se o localStorage falhar, a memória da sessão evita repetir
  try {
    armazenamento?.setItem(chave, eventoId);
  } catch {
    // sem localStorage: a memória basta
  }
}

/** Só para testes. */
export function limparMemoriaDaSessao(): void {
  memoriaDaSessao.clear();
}
