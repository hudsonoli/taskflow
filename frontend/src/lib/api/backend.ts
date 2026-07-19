import "server-only";

import type { NextRequest } from "next/server";
import { AuthBackendClient } from "../auth/backend";
import type { AuthBffConfig } from "../auth/config";
import { getAuthBffConfig } from "../auth/config";
import { AuthBffError } from "../auth/errors";
import { readSessionToken } from "../auth/session";
import { ApiBffError, mapBackendApiStatus } from "./errors";

type FetchImplementation = typeof fetch;

export type AuthenticatedApiContext = {
  config: AuthBffConfig;
  accessToken: string;
  empresaId: string;
};

export async function resolveAuthenticatedApiContext(
  request: NextRequest,
): Promise<AuthenticatedApiContext> {
  const config = getAuthBffConfig();
  const accessToken = readSessionToken(request, config);
  if (!accessToken) {
    throw new AuthBffError(
      401,
      "UNAUTHENTICATED",
      "Sessão não encontrada.",
    );
  }

  const currentUser = await new AuthBackendClient(config).me(accessToken);
  return {
    config,
    accessToken,
    empresaId: currentUser.empresaId,
  };
}

export class BackendApiClient {
  private readonly config: AuthBffConfig;
  private readonly fetchImplementation: FetchImplementation;

  constructor(
    config: AuthBffConfig,
    fetchImplementation: FetchImplementation = fetch,
  ) {
    this.config = config;
    this.fetchImplementation = fetchImplementation;
  }

  async getJson(path: string, accessToken: string): Promise<unknown> {
    return this.requestJson(path, accessToken, {
      method: "GET",
    });
  }

  private async requestJson(
    path: string,
    accessToken: string,
    init: RequestInit,
  ): Promise<unknown> {
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
            Authorization: `Bearer ${accessToken}`,
            ...init.headers,
          },
          signal: controller.signal,
        },
      );
      if (!response.ok) {
        throw mapBackendApiStatus(response.status);
      }

      try {
        return await response.json();
      } catch (error) {
        throw new ApiBffError(
          502,
          "INVALID_BACKEND_RESPONSE",
          "Resposta inválida do serviço de usuários.",
          { cause: error },
        );
      }
    } catch (error) {
      if (error instanceof ApiBffError) {
        throw error;
      }
      if (controller.signal.aborted) {
        throw new ApiBffError(
          504,
          "BACKEND_TIMEOUT",
          "O serviço de usuários excedeu o tempo de resposta.",
          { cause: error },
        );
      }
      throw new ApiBffError(
        502,
        "BACKEND_UNAVAILABLE",
        "Serviço de usuários indisponível.",
        { cause: error },
      );
    } finally {
      clearTimeout(timeout);
    }
  }
}
