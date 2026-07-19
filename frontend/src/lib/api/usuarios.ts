import "server-only";

import type {
  UsuarioCreatePayload,
  UsuarioListFilters,
  UsuarioUpdatePayload,
} from "../../types/usuario-api";
import type {
  Usuario,
  UsuarioListResult,
} from "../../types/usuario-domain";
import {
  isPerfilBase,
  isStatusUsuario,
  mapUsuarioApiListToResult,
  mapUsuarioApiResponseToDomain,
} from "../usuario-api-mappers";
import { BackendApiClient } from "./backend";
import { ApiBffError } from "./errors";

const FILTER_KEYS = new Set([
  "status",
  "perfilBase",
  "search",
  "limit",
  "offset",
]);

const CREATE_KEYS = new Set([
  "codigoInterno",
  "nome",
  "email",
  "perfilBase",
  "acessoSistema",
]);

function requiredString(
  value: unknown,
  key: "codigoInterno" | "nome" | "email",
  maxLength: number,
): string {
  if (
    typeof value !== "string" ||
    value.length < 1 ||
    value.length > maxLength
  ) {
    throw new ApiBffError(
      400,
      "INVALID_REQUEST",
      `Campo inválido: ${key}.`,
    );
  }
  return value;
}

export function parseUsuarioCreatePayload(
  body: Record<string, unknown>,
): UsuarioCreatePayload {
  for (const key of Object.keys(body)) {
    if (!CREATE_KEYS.has(key)) {
      throw new ApiBffError(
        400,
        "INVALID_REQUEST",
        `Campo não permitido: ${key}.`,
      );
    }
  }

  const perfilBase = body.perfilBase;
  if (!isPerfilBase(perfilBase)) {
    throw new ApiBffError(400, "INVALID_REQUEST", "Perfil inválido.");
  }
  if (
    body.acessoSistema !== undefined &&
    typeof body.acessoSistema !== "boolean"
  ) {
    throw new ApiBffError(
      400,
      "INVALID_REQUEST",
      "Campo inválido: acessoSistema.",
    );
  }

  return {
    codigoInterno: requiredString(body.codigoInterno, "codigoInterno", 64),
    nome: requiredString(body.nome, "nome", 255),
    email: requiredString(
      typeof body.email === "string" ? body.email.trim() : body.email,
      "email",
      255,
    ),
    perfilBase,
    ...(body.acessoSistema === undefined
      ? {}
      : { acessoSistema: body.acessoSistema }),
  };
}

export function parseUsuarioUpdatePayload(
  body: Record<string, unknown>,
): UsuarioUpdatePayload {
  for (const key of Object.keys(body)) {
    if (!CREATE_KEYS.has(key)) {
      throw new ApiBffError(
        400,
        "INVALID_REQUEST",
        `Campo não permitido: ${key}.`,
      );
    }
  }

  const payload: UsuarioUpdatePayload = {};

  if (Object.hasOwn(body, "codigoInterno")) {
    payload.codigoInterno = requiredString(
      body.codigoInterno,
      "codigoInterno",
      64,
    );
  }
  if (Object.hasOwn(body, "nome")) {
    payload.nome = requiredString(body.nome, "nome", 255);
  }
  if (Object.hasOwn(body, "email")) {
    payload.email = requiredString(
      typeof body.email === "string" ? body.email.trim() : body.email,
      "email",
      255,
    );
  }
  if (Object.hasOwn(body, "perfilBase")) {
    if (!isPerfilBase(body.perfilBase)) {
      throw new ApiBffError(400, "INVALID_REQUEST", "Perfil inválido.");
    }
    payload.perfilBase = body.perfilBase;
  }
  if (Object.hasOwn(body, "acessoSistema")) {
    if (typeof body.acessoSistema !== "boolean") {
      throw new ApiBffError(
        400,
        "INVALID_REQUEST",
        "Campo inválido: acessoSistema.",
      );
    }
    payload.acessoSistema = body.acessoSistema;
  }

  return payload;
}

function singleValue(
  searchParams: URLSearchParams,
  key: string,
): string | undefined {
  const values = searchParams.getAll(key);
  if (values.length > 1) {
    throw new ApiBffError(
      400,
      "INVALID_REQUEST",
      `Parâmetro duplicado: ${key}.`,
    );
  }
  return values[0];
}

function parseInteger(
  value: string | undefined,
  key: "limit" | "offset",
): number | undefined {
  if (value === undefined) return undefined;
  if (!/^\d+$/.test(value)) {
    throw new ApiBffError(
      400,
      "INVALID_REQUEST",
      `Parâmetro inválido: ${key}.`,
    );
  }
  const parsed = Number(value);
  const valid =
    Number.isSafeInteger(parsed) &&
    (key === "limit" ? parsed >= 1 && parsed <= 200 : parsed >= 0);
  if (!valid) {
    throw new ApiBffError(
      400,
      "INVALID_REQUEST",
      `Parâmetro inválido: ${key}.`,
    );
  }
  return parsed;
}

export function parseUsuarioListFilters(
  searchParams: URLSearchParams,
): UsuarioListFilters {
  for (const key of searchParams.keys()) {
    if (!FILTER_KEYS.has(key)) {
      throw new ApiBffError(
        400,
        "INVALID_REQUEST",
        `Parâmetro não permitido: ${key}.`,
      );
    }
  }

  const status = singleValue(searchParams, "status");
  const perfilBase = singleValue(searchParams, "perfilBase");
  if (status !== undefined && !isStatusUsuario(status)) {
    throw new ApiBffError(400, "INVALID_REQUEST", "Status inválido.");
  }
  if (perfilBase !== undefined && !isPerfilBase(perfilBase)) {
    throw new ApiBffError(400, "INVALID_REQUEST", "Perfil inválido.");
  }

  const search = singleValue(searchParams, "search")?.trim();
  return {
    ...(status ? { status } : {}),
    ...(perfilBase ? { perfilBase } : {}),
    ...(search ? { search } : {}),
    ...(() => {
      const limit = parseInteger(singleValue(searchParams, "limit"), "limit");
      return limit === undefined ? {} : { limit };
    })(),
    ...(() => {
      const offset = parseInteger(
        singleValue(searchParams, "offset"),
        "offset",
      );
      return offset === undefined ? {} : { offset };
    })(),
  };
}

function appendFilters(
  searchParams: URLSearchParams,
  filters: UsuarioListFilters,
): void {
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
}

export class UsuariosApi {
  private readonly backend: BackendApiClient;

  constructor(backend: BackendApiClient) {
    this.backend = backend;
  }

  async criar(
    accessToken: string,
    empresaId: string,
    payload: UsuarioCreatePayload,
  ): Promise<Usuario> {
    const response = await this.backend.postJson(
      "/usuarios",
      accessToken,
      {
        ...payload,
        empresaId,
      },
    );
    try {
      return mapUsuarioApiResponseToDomain(response, empresaId);
    } catch (error) {
      throw new ApiBffError(
        502,
        "INVALID_BACKEND_RESPONSE",
        "Resposta inválida do serviço de usuários.",
        { cause: error },
      );
    }
  }

  async listar(
    accessToken: string,
    empresaId: string,
    filters: UsuarioListFilters,
  ): Promise<UsuarioListResult> {
    const searchParams = new URLSearchParams({ empresaId });
    appendFilters(searchParams, filters);
    const payload = await this.backend.getJson(
      `/usuarios?${searchParams.toString()}`,
      accessToken,
    );

    try {
      return mapUsuarioApiListToResult(payload, empresaId);
    } catch (error) {
      throw new ApiBffError(
        502,
        "INVALID_BACKEND_RESPONSE",
        "Resposta inválida do serviço de usuários.",
        { cause: error },
      );
    }
  }

  async obter(
    accessToken: string,
    empresaId: string,
    usuarioId: string,
  ): Promise<Usuario> {
    const payload = await this.backend.getJson(
      `/usuarios/${encodeURIComponent(usuarioId)}`,
      accessToken,
    );
    try {
      return mapUsuarioApiResponseToDomain(payload, empresaId);
    } catch (error) {
      throw new ApiBffError(
        502,
        "INVALID_BACKEND_RESPONSE",
        "Resposta inválida do serviço de usuários.",
        { cause: error },
      );
    }
  }

  async atualizar(
    accessToken: string,
    empresaId: string,
    usuarioId: string,
    payload: UsuarioUpdatePayload,
  ): Promise<Usuario> {
    const response = await this.backend.patchJson(
      `/usuarios/${encodeURIComponent(usuarioId)}`,
      accessToken,
      payload,
    );
    try {
      return mapUsuarioApiResponseToDomain(response, empresaId);
    } catch (error) {
      throw new ApiBffError(
        502,
        "INVALID_BACKEND_RESPONSE",
        "Resposta inválida do serviço de usuários.",
        { cause: error },
      );
    }
  }
}
