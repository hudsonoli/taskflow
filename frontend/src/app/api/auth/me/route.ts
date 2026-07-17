import { NextRequest, NextResponse } from "next/server";
import { AuthBackendClient } from "../../../../lib/auth/backend";
import { getAuthBffConfig } from "../../../../lib/auth/config";
import {
  AuthBffError,
  authErrorResponse,
} from "../../../../lib/auth/errors";
import {
  clearSessionCookie,
  readSessionToken,
} from "../../../../lib/auth/session";

export async function GET(request: NextRequest) {
  try {
    const config = getAuthBffConfig();
    const accessToken = readSessionToken(request, config);

    if (!accessToken) {
      throw new AuthBffError(
        401,
        "UNAUTHENTICATED",
        "Sessão não encontrada.",
      );
    }

    try {
      const currentUser = await new AuthBackendClient(config).me(accessToken);
      return NextResponse.json(currentUser);
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
