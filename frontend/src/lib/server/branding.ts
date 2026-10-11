import "server-only";
import { BACKEND_URL } from "@/lib/server/backend";
import { BRANDING_PADRAO, type Branding, normalizarBranding } from "@/lib/branding";
import { type CachePorChave, criarCachePorChave, resolverComCache } from "@/lib/branding-cache";

// Branding PÚBLICO de uma empresa para o layout raiz (SSR) e para o logo, antes e depois do login. Resolvido SÓ pelo slug da URL
// (`/e/<slug>/...`) — Fase 9D: não existe empresa padrão nem EMPRESA_CODIGO; sem slug a identidade é a neutra do TaskFlow.
//
// CACHE POR TENANT. A chave é o alvo (`slug:<slug>`) — nunca um valor global compartilhado: a
// sequência A → B → A não pode contaminar logo, cores ou tema. Em memória, curto e limitado (TTL + teto de entradas,
// despejando a mais antiga): slugs arbitrários da URL não fazem o cache crescer sem limite. Qualquer falha (backend
// fora, timeout, resposta inválida) devolve os padrões — o branding NUNCA pode impedir o login nem derrubar a página.

export type AlvoBranding = { tipo: "slug"; slug: string };

export type BrandingPublico = {
  branding: Branding;
  /** empresa existe e está ativa */
  disponivel: boolean;
  /** nome de exibição público (fantasia ou razão), só quando disponível */
  nome: string | null;
};

const TTL_MS = 30_000;
const TTL_FALHA_MS = 5_000;
const TIMEOUT_MS = 1_500;
const MAX_ENTRADAS = 100;

// O cache vive em `globalThis`, não numa variável de módulo: o layout (renderização do servidor) e o proxy
// (route handler) são bundles diferentes e podem carregar cópias distintas deste módulo — com uma variável de
// módulo, a invalidação feita pelo proxy não chegaria ao layout.
const CHAVE_CACHE = "__taskflowBrandingPorTenant";
const global = globalThis as unknown as Record<string, CachePorChave<BrandingPublico> | undefined>;

function cache(): CachePorChave<BrandingPublico> {
  let existente = global[CHAVE_CACHE];
  if (!existente) {
    existente = criarCachePorChave<BrandingPublico>(MAX_ENTRADAS);
    global[CHAVE_CACHE] = existente;
  }
  return existente;
}

/** Chave de cache do alvo: sempre distinta por empresa. Exportada só para os testes provarem que não há chave global. */
export function chaveDoAlvo(alvo: AlvoBranding): string {
  return `slug:${alvo.slug}`;
}

/** O proxy autenticado (tenant e plataforma) chama isto depois de mudar a personalização, para que o próximo
 * carregamento já veja a nova cor/logo (sem esperar o TTL). Limpa TODAS as empresas: o cache é pequeno e barato. */
export function invalidarBranding() {
  cache().limpar();
}

const NEUTRO: BrandingPublico = { branding: BRANDING_PADRAO, disponivel: false, nome: null };

async function buscar(alvo: AlvoBranding): Promise<BrandingPublico | null> {
  const resposta = await fetch(`${BACKEND_URL}/publico/empresas/${encodeURIComponent(alvo.slug)}/branding`, {
    cache: "no-store",
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!resposta.ok) return null;
  const dados = (await resposta.json().catch(() => null)) as Record<string, unknown> | null;
  if (!dados || dados.disponivel !== true) return NEUTRO; // inexistente/inativa: identidade neutra, sem nome
  const nome = typeof dados.nomeExibicao === "string" && dados.nomeExibicao ? dados.nomeExibicao.slice(0, 120) : null;
  return { branding: { ...normalizarBranding(dados), slug: alvo.slug }, disponivel: true, nome };
}

export async function obterBrandingPublico(alvo: AlvoBranding): Promise<BrandingPublico> {
  return resolverComCache(cache(), chaveDoAlvo(alvo), Date.now, async () => {
    let valor: BrandingPublico | null = null;
    try {
      valor = await buscar(alvo);
    } catch {
      // backend indisponível / timeout → padrões; falha curta é cacheada para não martelar o backend.
    }
    const resultado = valor ?? NEUTRO;
    return { valor: resultado, ttlMs: valor === null || !resultado.disponivel ? TTL_FALHA_MS : TTL_MS };
  });
}

export function urlLogoBackend(alvo: AlvoBranding, versao: string | null): string {
  const v = versao ? `v=${encodeURIComponent(versao)}` : "";
  return `${BACKEND_URL}/publico/empresas/${encodeURIComponent(alvo.slug)}/branding/logo${v ? `?${v}` : ""}`;
}
