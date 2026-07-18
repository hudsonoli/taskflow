"use client";

import type {
  AuthCurrentUser,
  AuthErrorCode,
  AuthErrorResponse,
  AuthPerfilBase,
  AuthUsuarioStatus,
} from "../../types/auth";

const CURRENT_USER_ENDPOINT = "/api/auth/me";
const LOGOUT_ENDPOINT = "/api/auth/logout";

const PERFIS_BASE: ReadonlySet<AuthPerfilBase> = new Set([
  "admin",
  "gestor",
  "operador",
]);
const USUARIO_STATUSES: ReadonlySet<AuthUsuarioStatus> = new Set([
  "ativo",
  "inativo",
  "bloqueado",
  "arquivado",
]);

export type AuthClientResult =
  | { status: "authenticated"; user: AuthCurrentUser }
  | { status: "unauthenticated"; error: AuthErrorResponse | null }
  | { status: "error"; error: AuthErrorResponse };

type FetchImplementation = typeof fetch;

function safeError(code: AuthErrorCode, message: string): AuthErrorResponse {
  return { error: { code, message } };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function parseCurrentUser(value: unknown): AuthCurrentUser | null {
  if (
    !isRecord(value) ||
    typeof value.usuarioId !== "string" ||
    typeof value.empresaId !== "string" ||
    typeof value.nome !== "string" ||
    typeof value.perfilBase !== "string" ||
    !PERFIS_BASE.has(value.perfilBase as AuthPerfilBase) ||
    typeof value.acessoSistema !== "boolean" ||
    typeof value.status !== "string" ||
    !USUARIO_STATUSES.has(value.status as AuthUsuarioStatus)
  ) {
    return null;
  }

  return {
    usuarioId: value.usuarioId,
    empresaId: value.empresaId,
    nome: value.nome,
    perfilBase: value.perfilBase as AuthPerfilBase,
    acessoSistema: value.acessoSistema,
    status: value.status as AuthUsuarioStatus,
  };
}

export async function readAuthErrorResponse(
  response: Response,
): Promise<AuthErrorResponse> {
  try {
    const value: unknown = await response.json();
    if (
      isRecord(value) &&
      isRecord(value.error) &&
      typeof value.error.code === "string" &&
      typeof value.error.message === "string"
    ) {
      return value as AuthErrorResponse;
    }
  } catch {
    // Respostas inválidas são normalizadas sem expor detalhes internos.
  }

  return safeError(
    "INTERNAL_ERROR",
    "Não foi possível concluir a solicitação.",
  );
}

async function requestCurrentUser(
  fetchImplementation: FetchImplementation,
): Promise<AuthClientResult> {
  try {
    const response = await fetchImplementation(CURRENT_USER_ENDPOINT, {
      method: "GET",
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });

    if (response.status === 401) {
      return {
        status: "unauthenticated",
        error: await readAuthErrorResponse(response),
      };
    }

    if (!response.ok) {
      return {
        status: "error",
        error: await readAuthErrorResponse(response),
      };
    }

    const currentUser = parseCurrentUser(await response.json());
    if (!currentUser) {
      return {
        status: "error",
        error: safeError(
          "INVALID_BACKEND_RESPONSE",
          "Resposta inválida do serviço de autenticação.",
        ),
      };
    }

    return { status: "authenticated", user: currentUser };
  } catch {
    return {
      status: "error",
      error: safeError(
        "BACKEND_UNAVAILABLE",
        "Serviço de autenticação indisponível.",
      ),
    };
  }
}

export function createAuthBrowserClient(
  fetchImplementation: FetchImplementation = fetch,
) {
  let initialRequest: Promise<AuthClientResult> | null = null;

  return {
    getInitialUser(): Promise<AuthClientResult> {
      initialRequest ??= requestCurrentUser(fetchImplementation);
      return initialRequest;
    },

    refresh(): Promise<AuthClientResult> {
      initialRequest = requestCurrentUser(fetchImplementation);
      return initialRequest;
    },

    async logout(): Promise<AuthClientResult> {
      try {
        const response = await fetchImplementation(LOGOUT_ENDPOINT, {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
        });

        if (!response.ok && response.status !== 401) {
          return {
            status: "error",
            error: await readAuthErrorResponse(response),
          };
        }

        const result: AuthClientResult = {
          status: "unauthenticated",
          error: null,
        };
        initialRequest = Promise.resolve(result);
        return result;
      } catch {
        return {
          status: "error",
          error: safeError(
            "BACKEND_UNAVAILABLE",
            "Não foi possível encerrar a sessão.",
          ),
        };
      }
    },
  };
}

export const authBrowserClient = createAuthBrowserClient();
