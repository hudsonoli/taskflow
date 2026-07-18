import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import {
  decideRouteProtection,
  hasSessionCookie,
} from "./lib/auth/route-protection";

export function proxy(request: NextRequest) {
  const decision = decideRouteProtection({
    pathname: request.nextUrl.pathname,
    search: request.nextUrl.search,
    sessionCookiePresent: hasSessionCookie(request.cookies),
  });

  if (decision.action === "allow") {
    return NextResponse.next();
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  loginUrl.searchParams.set("returnTo", decision.returnTo);

  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: [
    "/((?!_next/static(?:/|$)|_next/image(?:/|$)).*)",
  ],
};
