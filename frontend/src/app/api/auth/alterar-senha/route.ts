import { NextRequest, NextResponse } from "next/server";
import { AuthBackendClient } from "../../../../lib/auth/backend";
import { getAuthBffConfig } from "../../../../lib/auth/config";
import {
  AuthBffError,
  authErrorResponse,
  readJsonObject,
  requireJsonContentType,
} from "../../../../lib/auth/errors";
import { assertValidMutationOrigin } from "../../../../lib/auth/origin";
import {
  clearSessionCookie,
  readSessionToken,
} from "../../../../lib/auth/session";
import type { AuthChangePasswordRequest } from "../../../../types/auth";

function parseChangePasswordRequest(
  body: Record<string, unknown>,
): AuthChangePasswordRequest {
  if (
    typeof body.senhaAtual !== "string" ||
    !body.senhaAtual ||
    typeof body.novaSenha !== "string" ||
    !body.novaSenha ||
    typeof body.confirmacaoSenha !== "string" ||
    !body.confirmacaoSenha
  ) {
    throw new AuthBffError(
      400,
      "INVALID_REQUEST",
      "Os campos de senha são obrigatórios.",
    );
  }

  return {
    senhaAtual: body.senhaAtual,
    novaSenha: body.novaSenha,
    confirmacaoSenha: body.confirmacaoSenha,
  };
}

export async function POST(request: NextRequest) {
  try {
    const config = getAuthBffConfig();
    assertValidMutationOrigin(request, config);
    requireJsonContentType(request);

    const accessToken = readSessionToken(request, config);
    if (!accessToken) {
      throw new AuthBffError(
        401,
        "UNAUTHENTICATED",
        "Sessão não encontrada.",
      );
    }

    try {
      const payload = parseChangePasswordRequest(
        await readJsonObject(request),
      );
      await new AuthBackendClient(config).changePassword(accessToken, payload);
      return new NextResponse(null, { status: 204 });
    } catch (error) {
      const response = authErrorResponse(error);
      if (error instanceof AuthBffError && error.status === 401) {
        clearSessionCookie(response, config);
      }
      return response;
    }
  } catch (error) {
    return authErrorResponse(error);
  }
}
