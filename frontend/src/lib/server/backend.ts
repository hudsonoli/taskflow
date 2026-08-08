import "server-only";

// Só usado dentro de Route Handlers (app/api/**) — nunca importado por código de cliente.
// O token JWT nunca sai daqui: fica só no cookie HttpOnly, o browser não tem acesso via JS.

export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8010";
export const EMPRESA_CODIGO = process.env.EMPRESA_CODIGO ?? "DEMO";

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
