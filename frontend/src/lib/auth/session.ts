import "server-only";

import type { NextRequest, NextResponse } from "next/server";
import type { AuthBffConfig } from "./config";
import { getSessionCookieName } from "./cookie";

export type SessionCookiePolicy = {
  name: string;
  httpOnly: true;
  sameSite: "lax";
  path: "/";
  secure: boolean;
  maxAge: number;
};

export function getSessionCookiePolicy(
  config: AuthBffConfig,
): SessionCookiePolicy {
  return {
    name: getSessionCookieName(config.production),
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: config.production,
    maxAge: config.sessionMaxAgeSeconds,
  };
}

export function readSessionToken(
  request: NextRequest,
  config: AuthBffConfig,
): string | null {
  const policy = getSessionCookiePolicy(config);
  return request.cookies.get(policy.name)?.value ?? null;
}

export function setSessionCookie(
  response: NextResponse,
  accessToken: string,
  config: AuthBffConfig,
): void {
  const policy = getSessionCookiePolicy(config);
  response.cookies.set({
    ...policy,
    value: accessToken,
  });
}

export function clearSessionCookie(
  response: NextResponse,
  config: AuthBffConfig,
): void {
  const policy = getSessionCookiePolicy(config);
  response.cookies.set({
    ...policy,
    value: "",
    maxAge: 0,
  });
}
