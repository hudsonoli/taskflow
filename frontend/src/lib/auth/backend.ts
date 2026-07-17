import "server-only";

import type {
  AuthChangePasswordRequest,
  AuthCurrentUser,
  AuthLoginBackendResponse,
  AuthLoginRequest,
  AuthPerfilBase,
  AuthUsuarioStatus,
} from "../../types/auth";
import type { AuthBffConfig } from "./config";
import { AuthBffError } from "./errors";

type FetchImplementation = typeof fetch;
type BackendOperation = "login" | "me" | "changePassword";

const AUTH_PATHS = {
  login: "/auth/login",
  me: "/auth/me",
  changePassword: "/auth/alterar-senha",
} as const;

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

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function invalidBackendResponse(): AuthBffError {
  return new AuthBffError(
    502,
    "INVALID_BACKEND_RESPONSE",
    "Resposta inválida do serviço de autenticação.",
  );
}

function mapBackendStatus(
  status: number,
  operation: BackendOperation,
): AuthBffError {
  if (status === 400) {
    return new AuthBffError(400, "INVALID_REQUEST", "Solicitação inválida.");
  }
  if (status === 401) {
    return operation === "login"
      ? new AuthBffError(
          401,
          "INVALID_CREDENTIALS",
          "Empresa, e-mail ou senha inválidos.",
        )
      : new AuthBffError(
          401,
          "UNAUTHENTICATED",
          "Sessão inválida ou expirada.",
        );
  }
  if (status === 403) {
    return new AuthBffError(403, "FORBIDDEN", "Acesso não autorizado.");
  }
  if (status === 422) {
    return new AuthBffError(
      422,
      "VALIDATION_ERROR",
      "Dados de autenticação inválidos.",
    );
  }
  if (status === 429) {
    return new AuthBffError(
      429,
      "RATE_LIMITED",
      "Muitas tentativas. Tente novamente mais tarde.",
    );
  }
  return new AuthBffError(
    502,
    "BACKEND_UNAVAILABLE",
    "Serviço de autenticação indisponível.",
  );
}

function parseLoginResponse(value: unknown): AuthLoginBackendResponse {
  if (
    !isRecord(value) ||
    typeof value.accessToken !== "string" ||
    !value.accessToken ||
    value.tokenType !== "bearer"
  ) {
    throw invalidBackendResponse();
  }

  return {
    accessToken: value.accessToken,
    tokenType: value.tokenType,
  };
}

function parseCurrentUser(value: unknown): AuthCurrentUser {
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
    throw invalidBackendResponse();
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

export class AuthBackendClient {
  private readonly config: AuthBffConfig;
  private readonly fetchImplementation: FetchImplementation;

  constructor(
    config: AuthBffConfig,
    fetchImplementation: FetchImplementation = fetch,
  ) {
    this.config = config;
    this.fetchImplementation = fetchImplementation;
  }

  async login(payload: AuthLoginRequest): Promise<AuthLoginBackendResponse> {
    const response = await this.request(
      AUTH_PATHS.login,
      "login",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
    return parseLoginResponse(await this.readJson(response));
  }

  async me(accessToken: string): Promise<AuthCurrentUser> {
    const response = await this.request(AUTH_PATHS.me, "me", {
      method: "GET",
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    return parseCurrentUser(await this.readJson(response));
  }

  async changePassword(
    accessToken: string,
    payload: AuthChangePasswordRequest,
  ): Promise<void> {
    await this.request(AUTH_PATHS.changePassword, "changePassword", {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify(payload),
    });
  }

  private async request(
    path: (typeof AUTH_PATHS)[keyof typeof AUTH_PATHS],
    operation: BackendOperation,
    init: RequestInit,
  ): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      this.config.backendTimeoutMs,
    );

    try {
      const response = await this.fetchImplementation(
        `${this.config.apiInternalUrl}${path}`,
        {
          ...init,
          cache: "no-store",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
            ...init.headers,
          },
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        throw mapBackendStatus(response.status, operation);
      }
      return response;
    } catch (error) {
      if (error instanceof AuthBffError) {
        throw error;
      }
      if (controller.signal.aborted) {
        throw new AuthBffError(
          504,
          "BACKEND_TIMEOUT",
          "O serviço de autenticação excedeu o tempo de resposta.",
          { cause: error },
        );
      }
      throw new AuthBffError(
        502,
        "BACKEND_UNAVAILABLE",
        "Serviço de autenticação indisponível.",
        { cause: error },
      );
    } finally {
      clearTimeout(timeout);
    }
  }

  private async readJson(response: Response): Promise<unknown> {
    try {
      return await response.json();
    } catch (error) {
      throw new AuthBffError(
        502,
        "INVALID_BACKEND_RESPONSE",
        "Resposta inválida do serviço de autenticação.",
        { cause: error },
      );
    }
  }
}
