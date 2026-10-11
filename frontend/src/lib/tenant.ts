// Contexto de empresa (tenant) das telas PÚBLICAS — lógica pura, sem React nem fetch (testável com `node --test`).
//
// O slug da URL (`/e/<slug>/login`) é só a chave PÚBLICA inicial: diz a QUAL empresa pertence a tela de login /
// recuperação de senha e de qual empresa é a marca. NUNCA autoriza dados: depois do login a empresa é a da sessão
// (`current_user.empresa_id` no backend), e nenhuma rota autenticada lê slug ou header para decidir tenant. Fase 9D: o slug da URL é a ÚNICA
// fonte do contexto de empresa no navegador — não há cookie, empresa padrão nem EMPRESA_CODIGO como fallback.

/** Header interno que o `proxy.ts` define a partir do caminho (e REMOVE do que vier do navegador). */
export const HEADER_TENANT_SLUG = "x-tf-tenant-slug";
/** Header interno: `gestao` nas rotas `/gestao/**` (a Gestão da plataforma mantém a identidade do PRODUTO, nunca a de uma empresa). */
export const HEADER_CONTEXTO = "x-tf-contexto";
export const CONTEXTO_GESTAO = "gestao";

export const PAGINAS_PUBLICAS_DO_TENANT = ["login", "esqueci-senha", "redefinir-senha", "aprovacao"] as const;
export type PaginaPublicaDoTenant = (typeof PAGINAS_PUBLICAS_DO_TENANT)[number];

// Espelho de `app/core/empresa_slug.py` (3–40, [a-z0-9-], sem hífen nas pontas, fora dos reservados).
const SLUGS_RESERVADOS = ["plataforma", "gestao", "api", "e", "aprovacao", "login", "logout", "admin", "suporte"];
const FORMATO_SLUG = /^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$/;

/** Slug normalizado (minúsculas, sem espaços) ou `null` se malformado/reservado. Nunca lança. */
export function normalizarSlug(bruto: unknown): string | null {
  if (typeof bruto !== "string") return null;
  let texto = bruto;
  try {
    texto = decodeURIComponent(bruto);
  } catch {
    return null;
  }
  const slug = texto.trim().toLowerCase();
  if (!FORMATO_SLUG.test(slug) || SLUGS_RESERVADOS.includes(slug)) return null;
  return slug;
}

/** `/e/<slug>/<pagina>` → `{ slug, pagina }` (slug JÁ validado) ou `null`. */
export function rotaDoTenant(pathname: string): { slug: string; pagina: string } | null {
  const partes = pathname.split("/").filter(Boolean);
  if (partes.length < 2 || partes[0] !== "e") return null;
  const slug = normalizarSlug(partes[1]);
  if (!slug) return null;
  return { slug, pagina: partes[2] ?? "" };
}

export function slugDaRota(pathname: string): string | null {
  return rotaDoTenant(pathname)?.slug ?? null;
}

/** Gestão da plataforma (Fase 10A): `/gestao/**`. Fora de qualquer empresa — não tem slug nem sessão tenant implícita. `/plataforma` deixou de existir. */
export function ehRotaDeGestao(pathname: string): boolean {
  return pathname === "/gestao" || pathname.startsWith("/gestao/");
}

/**
 * Caminho CANÔNICO de uma página de empresa: `/e/<slug>/<caminho>`. Fase 9D: NÃO existe empresa implícita — sem slug válido não há destino de
 * tenant e o resultado é `/` (404 neutro; nunca uma empresa "padrão"). `caminho` aceita com ou sem a barra inicial.
 */
export function caminhoDoTenant(slug: string | null | undefined, caminho: string): string {
  const valido = normalizarSlug(slug);
  if (!valido) return "/";
  const limpo = caminho.replace(/^\/+/, "");
  return limpo ? `/e/${valido}/${limpo}` : `/e/${valido}`;
}

export function hrefDoTenant(slug: string | null | undefined, pagina: PaginaPublicaDoTenant | "trocar-senha-inicial"): string {
  return caminhoDoTenant(slug, pagina);
}

export function hrefLogin(slug: string | null | undefined): string {
  return hrefDoTenant(slug, "login");
}

/** Pathname SEM o prefixo `/e/<slug>` (`/e/boxcom/tarefas` → `/tarefas`; `/e/boxcom` → `/`); `null` fora de uma rota tenant. */
export function caminhoSemTenant(pathname: string): string | null {
  const rota = rotaDoTenant(pathname);
  if (!rota) return null;
  return rota.pagina ? `/${pathname.split("/").filter(Boolean).slice(2).join("/")}` : "/";
}

/** Telas públicas "nuas" (legado `/login` ou `/e/<slug>/login`): sem TopNav, redirecionam quem já tem sessão. */
export function ehRotaDeLogin(pathname: string): boolean {
  return rotaDoTenant(pathname)?.pagina === "login";
}

/** Recuperação de senha (legado ou por slug): NÃO redireciona quem já tem sessão; o link do e-mail tem de chegar. */
export function ehRotaDeRecuperacaoDeSenha(pathname: string): boolean {
  const pagina = rotaDoTenant(pathname)?.pagina;
  return pagina === "esqueci-senha" || pagina === "redefinir-senha";
}

/** Troca obrigatória da senha inicial: `/e/<slug>/trocar-senha-inicial` (exige sessão da PRÓPRIA empresa). */
export function ehRotaDeTrocaDeSenhaInicial(pathname: string): boolean {
  return rotaDoTenant(pathname)?.pagina === "trocar-senha-inicial";
}

/** Portal Externo de Aprovação (Fase 9B/9D): rota PÚBLICA nua `/e/<slug>/aprovacao`, sem sessão do tenant. A empresa vem do TOKEN (capability); o
 * slug da URL só é CONFERIDO contra a empresa do token (diferente → "link indisponível") — nunca concede acesso. */
export const PAGINA_APROVACAO_EXTERNA = "aprovacao";
/** Valor de `x-tf-contexto` que o proxy define no portal (e apaga do que vier do navegador). */
export const CONTEXTO_APROVACAO = "aprovacao";

export function ehRotaDeAprovacaoExterna(pathname: string): boolean {
  const rota = rotaDoTenant(pathname);
  if (!rota || rota.pagina !== PAGINA_APROVACAO_EXTERNA) return false;
  return pathname.split("/").filter(Boolean).length === 3; // `/e/<slug>/aprovacao` (e a barra final), sem subcaminhos
}

/** Rotas que sempre usam o tema da EMPRESA (não há preferência de usuário a aplicar). */
export function usaTemaDaEmpresa(pathname: string): boolean {
  return (
    ehRotaDeLogin(pathname) ||
    ehRotaDeRecuperacaoDeSenha(pathname) ||
    ehRotaDeAprovacaoExterna(pathname) ||
    ehRotaDeTrocaDeSenhaInicial(pathname)
  );
}

/** Slug que vale para o contexto VISUAL da página. Fase 9D: SÓ o da rota `/e/<slug>/...` — sem fallback por cookie nem por empresa padrão. */
export function slugVisual(opcoes: { slugDaRota: string | null }): string | null {
  return opcoes.slugDaRota;
}
