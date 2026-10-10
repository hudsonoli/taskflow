// Contexto de empresa (tenant) das telas PÚBLICAS — lógica pura, sem React nem fetch (testável com `node --test`).
//
// O slug da URL (`/e/<slug>/login`) é só a chave PÚBLICA inicial: diz a QUAL empresa pertence a tela de login /
// recuperação de senha e de qual empresa é a marca. NUNCA autoriza dados: depois do login a empresa é a da sessão
// (`current_user.empresa_id` no backend), e nenhuma rota autenticada lê slug, cookie visual ou header para decidir tenant.

/** Header interno que o `proxy.ts` define a partir do caminho (e REMOVE do que vier do navegador). */
export const HEADER_TENANT_SLUG = "x-tf-tenant-slug";
/** Header interno: `plataforma` nas rotas `/plataforma/**` (o console mantém a identidade da plataforma). */
export const HEADER_CONTEXTO = "x-tf-contexto";
/** Cookie VISUAL, não sensível: só lembra qual marca mostrar e para qual login voltar. Nunca autoriza nada. */
export const COOKIE_TENANT_SLUG = "tf_tenant_slug";

export const PAGINAS_PUBLICAS_DO_TENANT = ["login", "esqueci-senha", "redefinir-senha"] as const;
export type PaginaPublicaDoTenant = (typeof PAGINAS_PUBLICAS_DO_TENANT)[number];

// Espelho de `app/core/empresa_slug.py` (3–40, [a-z0-9-], sem hífen nas pontas, fora dos reservados).
const SLUGS_RESERVADOS = ["plataforma", "api", "login", "logout", "admin", "suporte"];
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

export function ehRotaDaPlataforma(pathname: string): boolean {
  return pathname === "/plataforma" || pathname.startsWith("/plataforma/");
}

export function hrefDoTenant(slug: string | null | undefined, pagina: PaginaPublicaDoTenant): string {
  const valido = normalizarSlug(slug);
  return valido ? `/e/${valido}/${pagina}` : `/${pagina}`;
}

export function hrefLogin(slug: string | null | undefined): string {
  return hrefDoTenant(slug, "login");
}

/** Telas públicas "nuas" (legado `/login` ou `/e/<slug>/login`): sem TopNav, redirecionam quem já tem sessão. */
export function ehRotaDeLogin(pathname: string): boolean {
  return pathname === "/login" || rotaDoTenant(pathname)?.pagina === "login";
}

/** Recuperação de senha (legado ou por slug): NÃO redireciona quem já tem sessão; o link do e-mail tem de chegar. */
export function ehRotaDeRecuperacaoDeSenha(pathname: string): boolean {
  if (pathname === "/esqueci-senha" || pathname === "/redefinir-senha") return true;
  const pagina = rotaDoTenant(pathname)?.pagina;
  return pagina === "esqueci-senha" || pagina === "redefinir-senha";
}

/** Portal Externo de Aprovação (Fase 9B): rota PÚBLICA nua, sem sessão do tenant. A empresa vem do TOKEN (capability), nunca de slug/cookie. */
export const ROTA_APROVACAO_EXTERNA = "/aprovacao";
/** Valor de `x-tf-contexto` que o proxy define no portal (e apaga do que vier do navegador). */
export const CONTEXTO_APROVACAO = "aprovacao";

export function ehRotaDeAprovacaoExterna(pathname: string): boolean {
  return pathname === ROTA_APROVACAO_EXTERNA || pathname === `${ROTA_APROVACAO_EXTERNA}/`;
}

/** Rotas que sempre usam o tema da EMPRESA (não há preferência de usuário a aplicar). */
export function usaTemaDaEmpresa(pathname: string): boolean {
  return (
    ehRotaDeLogin(pathname) ||
    ehRotaDeRecuperacaoDeSenha(pathname) ||
    ehRotaDeAprovacaoExterna(pathname) ||
    pathname === "/trocar-senha-inicial"
  );
}

/** Slug que deve valer para o contexto VISUAL da página: o da rota; senão, só com sessão, o cookie visual. */
export function slugVisual(opcoes: { slugDaRota: string | null; slugDoCookie: string | null; autenticado: boolean }): string | null {
  if (opcoes.slugDaRota) return opcoes.slugDaRota;
  return opcoes.autenticado ? opcoes.slugDoCookie : null;
}
