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
import { setSessionCookie } from "../../../../lib/auth/session";
import type { AuthLoginRequest } from "../../../../types/auth";

function parseLoginRequest(body: Record<string, unknown>): AuthLoginRequest {
  if (
    typeof body.empresaCodigo !== "string" ||
    !body.empresaCodigo.trim() ||
    typeof body.email !== "string" ||
    !body.email.trim() ||
    typeof body.senha !== "string" ||
    !body.senha
  ) {
    throw new AuthBffError(
      400,
      "INVALID_REQUEST",
      "Empresa, e-mail e senha são obrigatórios.",
    );
  }

  return {
    empresaCodigo: body.empresaCodigo,
    email: body.email,
    senha: body.senha,
  };
}

export async function POST(request: NextRequest) {
  try {
    const config = getAuthBffConfig();
    assertValidMutationOrigin(request, config);
    requireJsonContentType(request);

    const payload = parseLoginRequest(await readJsonObject(request));
    const backend = new AuthBackendClient(config);
    const login = await backend.login(payload);
    const currentUser = await backend.me(login.accessToken);

    const response = NextResponse.json(currentUser);
    setSessionCookie(response, login.accessToken, config);
    return response;
  } catch (error) {
    return authErrorResponse(error);
  }
}
