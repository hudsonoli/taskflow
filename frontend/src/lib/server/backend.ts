import "server-only";

// Só usado dentro de Route Handlers (app/api/**) — nunca importado por código de cliente.
// O token JWT nunca sai daqui: fica só no cookie HttpOnly, o browser não tem acesso via JS.

export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8010";
export const EMPRESA_CODIGO = process.env.EMPRESA_CODIGO ?? "DEMO";
// Público (vai para o navegador) — client_id não é segredo. Lido no servidor (não
// NEXT_PUBLIC_*) pra não ficar fixado em build time: um valor novo em produção só exige
// trocar a variável de ambiente do container, sem rebuild — ver app/login/page.tsx.
export const GOOGLE_OAUTH_CLIENT_ID = process.env.GOOGLE_OAUTH_CLIENT_ID ?? null;

export const SESSION_COOKIE_NAME = "tf_session";
// Alinhado ao default de AUTH_ACCESS_TOKEN_EXPIRE_MINUTES no backend (30min) — se o token
// expirar antes, o backend simplesmente devolve 401 na próxima chamada.
export const SESSION_COOKIE_MAX_AGE_SECONDS = 30 * 60;

export function sessionCookieOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: SESSION_COOKIE_MAX_AGE_SECONDS,
  };
}

// Cookie VISUAL do tenant (slug público da empresa da sessão). Não sensível e SEM poder algum: serve só para o SSR
// escolher a marca certa de quem está logado e para voltar ao login da empresa certa. A empresa de verdade vem da
// sessão no backend. Reconciliado com `/auth/me` a cada login e a cada carregamento de sessão; apagado no logout.
export const TENANT_COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

export function tenantSlugCookieOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: TENANT_COOKIE_MAX_AGE_SECONDS,
  };
}

// Sessão da Administração da Plataforma: cookie PRÓPRIO, separado de `tf_session`. O token tenant e o de plataforma
// nunca se misturam (o backend recusa um no lugar do outro). Escopo de caminho restrito ao BFF da plataforma — o
// navegador não o envia para nenhuma outra rota — e HttpOnly: o JS da página nunca o lê.
export const PLATFORM_COOKIE_NAME = "tf_platform";
export const PLATFORM_COOKIE_PATH = "/api/plataforma";

export function platformCookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict" as const,
    path: PLATFORM_COOKIE_PATH,
    maxAge: maxAgeSeconds,
  };
}
