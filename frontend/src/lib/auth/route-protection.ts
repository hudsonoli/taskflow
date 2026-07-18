import { getSessionCookieName } from "./cookie";

const PUBLIC_EXACT_PATHS = new Set([
  "/login",
  "/login/",
  "/favicon.ico",
  "/robots.txt",
  "/sitemap.xml",
  "/manifest.webmanifest",
  "/file.svg",
  "/globe.svg",
  "/next.svg",
  "/vercel.svg",
  "/window.svg",
]);
const AUTH_API_PATH = "/api/auth";
const NEXT_INTERNAL_PATH = "/_next";

type CookieReader = {
  get: (name: string) => { value: string } | undefined;
};

export type RouteProtectionDecision =
  | { action: "allow"; reason: "public-route" | "session-cookie-present" }
  | { action: "redirect"; returnTo: string };

function isPathOrDescendant(pathname: string, path: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`);
}

export function isPublicRoute(pathname: string): boolean {
  return (
    PUBLIC_EXACT_PATHS.has(pathname) ||
    isPathOrDescendant(pathname, AUTH_API_PATH) ||
    isPathOrDescendant(pathname, NEXT_INTERNAL_PATH)
  );
}

export function buildReturnTo(pathname: string, search: string): string {
  if (!search) {
    return pathname;
  }

  return `${pathname}${search.startsWith("?") ? search : `?${search}`}`;
}

export function hasSessionCookie(
  cookies: CookieReader,
  production = process.env.NODE_ENV === "production",
): boolean {
  const cookie = cookies.get(getSessionCookieName(production));
  return typeof cookie?.value === "string" && cookie.value.trim().length > 0;
}

export function decideRouteProtection({
  pathname,
  search,
  sessionCookiePresent,
}: {
  pathname: string;
  search: string;
  sessionCookiePresent: boolean;
}): RouteProtectionDecision {
  if (isPublicRoute(pathname)) {
    return { action: "allow", reason: "public-route" };
  }

  if (sessionCookiePresent) {
    return { action: "allow", reason: "session-cookie-present" };
  }

  return {
    action: "redirect",
    returnTo: buildReturnTo(pathname, search),
  };
}
