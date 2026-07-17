import "server-only";

import { AuthBffError } from "./errors";

const DEFAULT_BACKEND_TIMEOUT_MS = 5_000;

export type AuthBffConfig = {
  apiInternalUrl: string;
  allowedOrigins: ReadonlySet<string>;
  sessionMaxAgeSeconds: number;
  backendTimeoutMs: number;
  production: boolean;
};

type AuthEnvironment = Partial<Pick<
  NodeJS.ProcessEnv,
  | "NODE_ENV"
  | "TASKFLOWW_API_INTERNAL_URL"
  | "TASKFLOWW_AUTH_ALLOWED_ORIGINS"
  | "TASKFLOWW_SESSION_MAX_AGE_SECONDS"
>>;

function configurationError(variable: string): AuthBffError {
  return new AuthBffError(
    500,
    "CONFIGURATION_ERROR",
    `Configuração obrigatória ausente ou inválida: ${variable}.`,
  );
}

function parseInternalUrl(value: string | undefined): string {
  if (!value) {
    throw configurationError("TASKFLOWW_API_INTERNAL_URL");
  }

  try {
    const url = new URL(value);
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    ) {
      throw new Error("URL interna inválida");
    }
    return url.toString().replace(/\/$/, "");
  } catch {
    throw configurationError("TASKFLOWW_API_INTERNAL_URL");
  }
}

function parseAllowedOrigins(value: string | undefined): ReadonlySet<string> {
  if (!value) {
    throw configurationError("TASKFLOWW_AUTH_ALLOWED_ORIGINS");
  }

  const origins = value.split(",").map((item) => item.trim()).filter(Boolean);
  if (origins.length === 0) {
    throw configurationError("TASKFLOWW_AUTH_ALLOWED_ORIGINS");
  }

  try {
    return new Set(
      origins.map((origin) => {
        const url = new URL(origin);
        if (
          !["http:", "https:"].includes(url.protocol) ||
          url.origin !== origin ||
          url.username ||
          url.password
        ) {
          throw new Error("Origin inválido");
        }
        return url.origin;
      }),
    );
  } catch {
    throw configurationError("TASKFLOWW_AUTH_ALLOWED_ORIGINS");
  }
}

function parsePositiveInteger(
  variable: string,
  value: string | undefined,
): number {
  if (!value || !/^\d+$/.test(value)) {
    throw configurationError(variable);
  }

  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed <= 0) {
    throw configurationError(variable);
  }
  return parsed;
}

export function getAuthBffConfig(
  environment: AuthEnvironment = process.env,
): AuthBffConfig {
  return {
    apiInternalUrl: parseInternalUrl(
      environment.TASKFLOWW_API_INTERNAL_URL,
    ),
    allowedOrigins: parseAllowedOrigins(
      environment.TASKFLOWW_AUTH_ALLOWED_ORIGINS,
    ),
    sessionMaxAgeSeconds: parsePositiveInteger(
      "TASKFLOWW_SESSION_MAX_AGE_SECONDS",
      environment.TASKFLOWW_SESSION_MAX_AGE_SECONDS,
    ),
    backendTimeoutMs: DEFAULT_BACKEND_TIMEOUT_MS,
    production: environment.NODE_ENV === "production",
  };
}
