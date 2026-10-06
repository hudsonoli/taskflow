import "server-only";
import { BACKEND_URL, EMPRESA_CODIGO } from "@/lib/server/backend";
import { BRANDING_PADRAO, type Branding, normalizarBranding } from "@/lib/branding";

// Branding da Empresa para o layout raiz (SSR) e o logo público. UMA busca centralizada, com timeout e cache
// em memória de curta duração: o layout roda a cada request e a personalização quase nunca muda. Qualquer
// falha (backend fora, timeout, resposta inválida) devolve os padrões — o branding NUNCA pode impedir o login
// nem derrubar a página.

const TTL_MS = 30_000;
const TIMEOUT_MS = 1_500;

// O cache vive em `globalThis`, não numa variável de módulo: o layout (renderização do servidor) e o proxy
// (route handler) são bundles diferentes e podem carregar cópias distintas deste módulo — com uma variável de
// módulo, a invalidação feita pelo proxy não chegaria ao layout.
type Entrada = { valor: Branding; expiraEm: number } | null;
const CHAVE = "__taskflowBrandingCache";
const memoria = globalThis as unknown as Record<string, Entrada>;

/** O proxy autenticado chama isto depois de uma mudança em /configuracoes/personalizacao*, para que o
 * próximo carregamento já veja a nova cor/logo (sem esperar o TTL). */
export function invalidarBranding() {
  memoria[CHAVE] = null;
}

export async function obterBranding(): Promise<Branding> {
  const agora = Date.now();
  const cache = memoria[CHAVE];
  if (cache && cache.expiraEm > agora) return cache.valor;

  let valor: Branding = BRANDING_PADRAO;
  try {
    const resposta = await fetch(
      `${BACKEND_URL}/personalizacao/publica?empresaCodigo=${encodeURIComponent(EMPRESA_CODIGO)}`,
      { cache: "no-store", signal: AbortSignal.timeout(TIMEOUT_MS) },
    );
    if (resposta.ok) valor = normalizarBranding(await resposta.json().catch(() => null));
  } catch {
    // backend indisponível / timeout → padrões; falha curta é cacheada para não martelar o backend.
  }
  memoria[CHAVE] = { valor, expiraEm: agora + (valor === BRANDING_PADRAO ? 5_000 : TTL_MS) };
  return valor;
}

export function urlLogoBackend(versao: string | null): string {
  const v = versao ? `&v=${encodeURIComponent(versao)}` : "";
  return `${BACKEND_URL}/personalizacao/publica/logo?empresaCodigo=${encodeURIComponent(EMPRESA_CODIGO)}${v}`;
}
