import "server-only";
import { COOKIE_TEMA, normalizarPreferencia, type TemaPreferencia } from "@/lib/tema";

// Cookie-espelho da preferência pessoal de tema (primeiro paint no servidor). A VERDADE é o banco
// (usuarios.tema_preferencia); este cookie só evita o flash e é reconciliado a cada login, a cada
// carregamento de sessão (/api/auth/session), a cada troca (/api/auth/tema) e apagado no logout. Valor: só
// "claro" | "escuro" | "sistema" — ausente = herdar a empresa. Nada pessoal.

type Jar = {
  set: (nome: string, valor: string, opcoes: Record<string, unknown>) => unknown;
  delete: (nome: string) => unknown;
};

const UM_ANO_SEGUNDOS = 365 * 24 * 60 * 60;

export function opcoesCookieTema() {
  return {
    httpOnly: true, // o cliente não lê o cookie: recebe a preferência pelo SSR e a altera por /api/auth/tema
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: UM_ANO_SEGUNDOS,
  };
}

export function sincronizarCookieTema(jar: Jar, preferencia: unknown): TemaPreferencia {
  const valor = normalizarPreferencia(preferencia);
  if (valor === null) jar.delete(COOKIE_TEMA);
  else jar.set(COOKIE_TEMA, valor, opcoesCookieTema());
  return valor;
}

/** Busca a preferência real no backend com o token recém-emitido (login). Qualquer falha → herdar a empresa. */
export async function preferenciaDoBackend(backendUrl: string, token: string): Promise<TemaPreferencia> {
  try {
    const resposta = await fetch(`${backendUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(3_000),
    });
    if (!resposta.ok) return null;
    const dados = (await resposta.json().catch(() => null)) as { temaPreferencia?: unknown } | null;
    return normalizarPreferencia(dados?.temaPreferencia);
  } catch {
    return null;
  }
}
