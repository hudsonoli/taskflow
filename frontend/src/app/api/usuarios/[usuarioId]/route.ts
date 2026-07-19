import { NextRequest, NextResponse } from "next/server";
import {
  BackendApiClient,
  resolveAuthenticatedApiContext,
} from "../../../../lib/api/backend";
import { apiErrorResponse } from "../../../../lib/api/errors";
import { UsuariosApi } from "../../../../lib/api/usuarios";

type RouteContext = {
  params: Promise<{ usuarioId: string }>;
};

export async function GET(request: NextRequest, context: RouteContext) {
  try {
    const authenticated = await resolveAuthenticatedApiContext(request);
    const { usuarioId } = await context.params;
    const usuario = await new UsuariosApi(
      new BackendApiClient(authenticated.config),
    ).obter(
      authenticated.accessToken,
      authenticated.empresaId,
      usuarioId,
    );

    return NextResponse.json(
      { data: usuario },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return apiErrorResponse(error);
  }
}
