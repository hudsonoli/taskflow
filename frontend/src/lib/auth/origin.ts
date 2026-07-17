import "server-only";

import type { AuthBffConfig } from "./config";
import { AuthBffError } from "./errors";

function singleHeaderValue(value: string | null): string | null {
  if (!value || value.includes(",")) {
    return null;
  }
  return value.trim() || null;
}

function parseOrigin(value: string | null): string | null {
  if (!value) {
    return null;
  }

  try {
    const url = new URL(value);
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.origin !== value ||
      url.username ||
      url.password
    ) {
      return null;
    }
    return url.origin;
  } catch {
    return null;
  }
}

function requestOrigins(request: Request, config: AuthBffConfig): Set<string> {
  const origins = new Set<string>();
  const requestUrl = new URL(request.url);

  origins.add(requestUrl.origin);

  const host = singleHeaderValue(request.headers.get("host"));
  if (host) {
    const hostOrigin = parseOrigin(`${requestUrl.protocol}//${host}`);
    if (hostOrigin) {
      origins.add(hostOrigin);
    }
  }

  const forwardedHost = singleHeaderValue(
    request.headers.get("x-forwarded-host"),
  );
  const forwardedProto = singleHeaderValue(
    request.headers.get("x-forwarded-proto"),
  );
  if (forwardedHost && forwardedProto && ["http", "https"].includes(forwardedProto)) {
    const forwardedOrigin = parseOrigin(
      `${forwardedProto}://${forwardedHost}`,
    );
    if (forwardedOrigin && config.allowedOrigins.has(forwardedOrigin)) {
      origins.add(forwardedOrigin);
    }
  }

  return origins;
}

export function assertValidMutationOrigin(
  request: Request,
  config: AuthBffConfig,
): void {
  const suppliedOrigin = parseOrigin(request.headers.get("origin"));
  if (
    !suppliedOrigin ||
    !config.allowedOrigins.has(suppliedOrigin) ||
    !requestOrigins(request, config).has(suppliedOrigin)
  ) {
    throw new AuthBffError(
      403,
      "INVALID_ORIGIN",
      "Origem da solicitação não autorizada.",
    );
  }
}
