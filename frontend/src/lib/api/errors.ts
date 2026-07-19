import "server-only";

import { NextResponse } from "next/server";
import type {
  UsuarioErrorCode,
  UsuarioErrorResponse,
} from "../../types/usuario-api";
import { AuthBffError, authErrorResponse } from "../auth/errors";

export class ApiBffError extends Error {
  readonly status: number;
  readonly code: UsuarioErrorCode;
  readonly safeMessage: string;

  constructor(
    status: number,
    code: UsuarioErrorCode,
    safeMessage: string,
    options?: ErrorOptions,
  ) {
    super(safeMessage, options);
    this.name = "ApiBffError";
    this.status = status;
    this.code = code;
    this.safeMessage = safeMessage;
  }
}

export function apiErrorResponse(
  error: unknown,
): NextResponse<UsuarioErrorResponse> {
  if (error instanceof AuthBffError) {
    const response = authErrorResponse(error) as NextResponse<UsuarioErrorResponse>;
    response.headers.set("Cache-Control", "no-store");
    return response;
  }

  const resolved =
    error instanceof ApiBffError
      ? error
      : new ApiBffError(
          500,
          "INTERNAL_ERROR",
          "Não foi possível concluir a solicitação.",
        );

  return NextResponse.json(
    {
      error: {
        code: resolved.code,
        message: resolved.safeMessage,
      },
    },
    {
      status: resolved.status,
      headers: { "Cache-Control": "no-store" },
    },
  );
}

export function mapBackendApiStatus(status: number): ApiBffError {
  if (status === 401) {
    return new ApiBffError(
      401,
      "UNAUTHENTICATED",
      "Sessão inválida ou expirada.",
    );
  }
  if (status === 403) {
    return new ApiBffError(403, "FORBIDDEN", "Acesso não autorizado.");
  }
  if (status === 404) {
    return new ApiBffError(404, "NOT_FOUND", "Usuário não encontrado.");
  }
  if (status === 422) {
    return new ApiBffError(
      422,
      "VALIDATION_ERROR",
      "Parâmetros de consulta inválidos.",
    );
  }
  return new ApiBffError(
    502,
    "BACKEND_UNAVAILABLE",
    "Serviço de usuários indisponível.",
  );
}
