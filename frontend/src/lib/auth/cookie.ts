const DEVELOPMENT_COOKIE_NAME = "taskfloww_session";
const PRODUCTION_COOKIE_NAME = "__Host-taskfloww_session";

export function getSessionCookieName(
  production = process.env.NODE_ENV === "production",
): string {
  return production ? PRODUCTION_COOKIE_NAME : DEVELOPMENT_COOKIE_NAME;
}

export function isProductionCookie(name: string): boolean {
  return name === PRODUCTION_COOKIE_NAME;
}

export function isDevelopmentCookie(name: string): boolean {
  return name === DEVELOPMENT_COOKIE_NAME;
}
