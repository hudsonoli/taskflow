import { NextRequest, NextResponse } from "next/server";
import { getAuthBffConfig } from "../../../../lib/auth/config";
import {
  readJsonObject,
  requireJsonContentType,
} from "../../../../lib/auth/errors";
import { assertValidMutationOrigin } from "../../../../lib/auth/origin";
import {
  BackendApiClient,
  resolveAuthenticatedApiContext,
} from "../../../../lib/api/backend";
import { apiErrorResponse } from "../../../../lib/api/errors";
import {
  parseUsuarioUpdatePayload,
  UsuariosApi,
} from "../../../../lib/api/usuarios";

type RouteContext = {
  params: Promise<{ usuarioId: string }>;
};

export async function PATCH(request: NextRequest, context: RouteContext) {
  try {
    const config = getAuthBffConfig();
    assertValidMutationOrigin(request, config);
    requireJsonContentType(request);

    const payload = parseUsuarioUpdatePayload(
      await readJsonObject(request),
    );
    const authenticated = await resolveAuthenticatedApiContext(request);
    const { usuarioId } = await context.params;
    const usuario = await new UsuariosApi(
      new BackendApiClient(authenticated.config),
    ).atualizar(
      authenticated.accessToken,
      authenticated.empresaId,
      usuarioId,
      payload,
    );

    return NextResponse.json(
      { data: usuario },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return apiErrorResponse(error);
  }
}

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
