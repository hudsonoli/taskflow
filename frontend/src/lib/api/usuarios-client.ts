"use client";

import type {
  UsuarioCreatePayload,
  UsuarioErrorCode,
  UsuarioErrorResponse,
  UsuarioListFilters,
  UsuarioUpdatePayload,
} from "../../types/usuario-api";
import type {
  UsuarioClientResult,
  UsuarioDetailResult,
  UsuarioListResult,
} from "../../types/usuario-domain";
import {
  parseUsuarioDetailResult,
  parseUsuarioListResult,
} from "../usuario-api-mappers";

type FetchImplementation = typeof fetch;

function safeError(
  code: UsuarioErrorCode,
  message: string,
): UsuarioErrorResponse {
  return { error: { code, message } };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

async function readError(response: Response): Promise<UsuarioErrorResponse> {
  try {
    const value: unknown = await response.json();
    if (
      isRecord(value) &&
      isRecord(value.error) &&
      typeof value.error.code === "string" &&
      typeof value.error.message === "string"
    ) {
      return value as UsuarioErrorResponse;
    }
  } catch {
    // A resposta é normalizada sem propagar detalhes internos.
  }
  return safeError(
    "INTERNAL_ERROR",
    "Não foi possível concluir a solicitação.",
  );
}

function buildListUrl(filters: UsuarioListFilters): string {
  const searchParams = new URLSearchParams();
  if (filters.status) searchParams.set("status", filters.status);
  if (filters.perfilBase) {
    searchParams.set("perfilBase", filters.perfilBase);
  }
  if (filters.search) searchParams.set("search", filters.search);
  if (filters.limit !== undefined) {
    searchParams.set("limit", String(filters.limit));
  }
  if (filters.offset !== undefined) {
    searchParams.set("offset", String(filters.offset));
  }
  const query = searchParams.toString();
  return query ? `/api/usuarios?${query}` : "/api/usuarios";
}

async function request<T>(
  fetchImplementation: FetchImplementation,
  endpoint: string,
  init: RequestInit,
  parse: (value: unknown) => T,
): Promise<UsuarioClientResult<T>> {
  try {
    const response = await fetchImplementation(endpoint, {
      ...init,
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...init.headers,
      },
    });
    if (!response.ok) {
      return { ok: false, error: await readError(response) };
    }

    try {
      return { ok: true, data: parse(await response.json()) };
    } catch {
      return {
        ok: false,
        error: safeError(
          "INVALID_BACKEND_RESPONSE",
          "Resposta inválida do serviço de usuários.",
        ),
      };
    }
  } catch {
    return {
      ok: false,
      error: safeError(
        "BACKEND_UNAVAILABLE",
        "Serviço de usuários indisponível.",
      ),
    };
  }
}

export function createUsuariosBrowserClient(
  fetchImplementation: FetchImplementation = fetch,
) {
  return {
    listarUsuarios(
      filters: UsuarioListFilters = {},
    ): Promise<UsuarioClientResult<UsuarioListResult>> {
      return request(
        fetchImplementation,
        buildListUrl(filters),
        { method: "GET" },
        parseUsuarioListResult,
      );
    },

    obterUsuario(
      usuarioId: string,
    ): Promise<UsuarioClientResult<UsuarioDetailResult>> {
      return request(
        fetchImplementation,
        `/api/usuarios/${encodeURIComponent(usuarioId)}`,
        { method: "GET" },
        parseUsuarioDetailResult,
      );
    },

    criarUsuario(
      payload: UsuarioCreatePayload,
    ): Promise<UsuarioClientResult<UsuarioDetailResult>> {
      return request(
        fetchImplementation,
        "/api/usuarios",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        parseUsuarioDetailResult,
      );
    },

    atualizarUsuario(
      usuarioId: string,
      payload: UsuarioUpdatePayload,
    ): Promise<UsuarioClientResult<UsuarioDetailResult>> {
      return request(
        fetchImplementation,
        `/api/usuarios/${encodeURIComponent(usuarioId)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        parseUsuarioDetailResult,
      );
    },
  };
}

export const usuariosBrowserClient = createUsuariosBrowserClient();
