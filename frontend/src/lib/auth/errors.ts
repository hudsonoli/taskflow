import "server-only";

import { NextResponse } from "next/server";
import type {
  AuthErrorCode,
  AuthErrorResponse,
} from "../../types/auth";

const DEFAULT_ERROR = {
  status: 500,
  code: "INTERNAL_ERROR",
  message: "Não foi possível concluir a solicitação.",
} as const;

export class AuthBffError extends Error {
  readonly status: number;
  readonly code: AuthErrorCode;
  readonly safeMessage: string;

  constructor(
    status: number,
    code: AuthErrorCode,
    safeMessage: string,
    options?: ErrorOptions,
  ) {
    super(safeMessage, options);
    this.name = "AuthBffError";
    this.status = status;
    this.code = code;
    this.safeMessage = safeMessage;
  }
}

export function authErrorResponse(error: unknown): NextResponse<AuthErrorResponse> {
  const resolved =
    error instanceof AuthBffError
      ? error
      : new AuthBffError(
          DEFAULT_ERROR.status,
          DEFAULT_ERROR.code,
          DEFAULT_ERROR.message,
        );

  return NextResponse.json(
    {
      error: {
        code: resolved.code,
        message: resolved.safeMessage,
      },
    },
    { status: resolved.status },
  );
}

export function requireJsonContentType(request: Request): void {
  const contentType = request.headers.get("content-type");
  if (!contentType?.toLowerCase().startsWith("application/json")) {
    throw new AuthBffError(
      415,
      "UNSUPPORTED_MEDIA_TYPE",
      "A solicitação deve usar Content-Type application/json.",
    );
  }
}

export async function readJsonObject(
  request: Request,
): Promise<Record<string, unknown>> {
  try {
    const body: unknown = await request.json();
    if (body === null || typeof body !== "object" || Array.isArray(body)) {
      throw new Error("JSON deve ser um objeto");
    }
    return body as Record<string, unknown>;
  } catch (error) {
    throw new AuthBffError(
      400,
      "INVALID_REQUEST",
      "Corpo JSON inválido.",
      { cause: error },
    );
  }
}
