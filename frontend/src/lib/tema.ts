// Tema efetivo = tema padrão da EMPRESA + preferência PESSOAL do usuário (+ preferência do dispositivo).
// Módulo PURO (sem imports de React/Next): roda no servidor (layout), no cliente (BrandingProvider) e no
// `node --test`. Logo e cores NÃO passam por aqui — continuam sempre da empresa.

import type { TemaVisual } from "@/types/personalizacao";

export type { TemaVisual };
/** Preferência pessoal persistida no servidor. `null` = "usar o padrão da empresa". */
export type TemaPreferencia = "claro" | "escuro" | "sistema" | null;

export const TEMAS_PREFERENCIA = ["claro", "escuro", "sistema"] as const;

export function temaPreferenciaValido(valor: unknown): valor is Exclude<TemaPreferencia, null> {
  return typeof valor === "string" && (TEMAS_PREFERENCIA as readonly string[]).includes(valor);
}

/** Normaliza o que vem da API/cookie: qualquer coisa fora da lista vira `null` (herdar a empresa). */
export function normalizarPreferencia(valor: unknown): TemaPreferencia {
  return temaPreferenciaValido(valor) ? valor : null;
}

/**
 * Prioridade (exatamente esta):
 *  - sem usuário autenticado (ou página pública) → tema da empresa
 *  - autenticado + null                          → tema da empresa
 *  - autenticado + claro | escuro                → o escolhido
 *  - autenticado + sistema                       → prefers-color-scheme do dispositivo
 */
export function resolveEffectiveTheme(entrada: {
  temaEmpresa: TemaVisual;
  preferencia: TemaPreferencia;
  sistemaEscuro: boolean;
  autenticado?: boolean;
}): TemaVisual {
  const { temaEmpresa, preferencia, sistemaEscuro, autenticado = true } = entrada;
  if (!autenticado || preferencia === null) return temaEmpresa;
  if (preferencia === "sistema") return sistemaEscuro ? "escuro" : "claro";
  return preferencia;
}

// Cookie-espelho técnico, só para o PRIMEIRO PAINT no servidor (a verdade é o banco). Não sensível: só o tema.
// Ausente = herdar a empresa. O servidor só o honra quando existe a sessão (tf_session) — ver layout.
export const COOKIE_TEMA = "taskflow_tema";

/** Script mínimo (inline, antes da hidratação) para `sistema`: define data-theme a partir do dispositivo, sem
 * ler nada sensível. Só é emitido pelo servidor quando há sessão + preferência `sistema`. */
export const SCRIPT_TEMA_SISTEMA =
  '(function(){try{document.documentElement.setAttribute("data-theme",window.matchMedia("(prefers-color-scheme: dark)").matches?"escuro":"claro")}catch(e){}})()';

export type ConsultaMidia = {
  matches: boolean;
  addEventListener: (tipo: "change", ouvinte: (evento: { matches: boolean }) => void) => void;
  removeEventListener: (tipo: "change", ouvinte: (evento: { matches: boolean }) => void) => void;
};

/** Acompanha `prefers-color-scheme: dark` em tempo de execução (sem polling). Devolve o cleanup. */
export function observarSistemaEscuro(consulta: ConsultaMidia, aoMudar: (escuro: boolean) => void): () => void {
  const ouvinte = (evento: { matches: boolean }) => aoMudar(evento.matches);
  consulta.addEventListener("change", ouvinte);
  aoMudar(consulta.matches);
  return () => consulta.removeEventListener("change", ouvinte);
}

/**
 * Troca otimista: aplica a nova preferência NA HORA, persiste, e se a persistência falhar restaura a anterior
 * (frontend e servidor nunca divergem). Relança o erro para a UI avisar.
 */
export async function trocarPreferencia<T extends TemaPreferencia>(opcoes: {
  anterior: TemaPreferencia;
  nova: T;
  aplicar: (preferencia: TemaPreferencia) => void;
  persistir: (preferencia: T) => Promise<unknown>;
}): Promise<void> {
  const { anterior, nova, aplicar, persistir } = opcoes;
  aplicar(nova);
  try {
    await persistir(nova);
  } catch (erro) {
    aplicar(anterior);
    throw erro;
  }
}
