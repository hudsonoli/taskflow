import { NextRequest, NextResponse } from "next/server";
import {
  readJsonObject,
  requireJsonContentType,
} from "../../../lib/auth/errors";
import { getAuthBffConfig } from "../../../lib/auth/config";
import { assertValidMutationOrigin } from "../../../lib/auth/origin";
import {
  BackendApiClient,
  resolveAuthenticatedApiContext,
} from "../../../lib/api/backend";
import { apiErrorResponse } from "../../../lib/api/errors";
import {
  parseUsuarioCreatePayload,
  parseUsuarioListFilters,
  UsuariosApi,
} from "../../../lib/api/usuarios";

export async function POST(request: NextRequest) {
  try {
    const config = getAuthBffConfig();
    assertValidMutationOrigin(request, config);
    requireJsonContentType(request);

    const payload = parseUsuarioCreatePayload(
      await readJsonObject(request),
    );
    const context = await resolveAuthenticatedApiContext(request);
    const usuario = await new UsuariosApi(
      new BackendApiClient(context.config),
    ).criar(context.accessToken, context.empresaId, payload);

    return NextResponse.json(
      { data: usuario },
      {
        status: 201,
        headers: { "Cache-Control": "no-store" },
      },
    );
  } catch (error) {
    return apiErrorResponse(error);
  }
}

export async function GET(request: NextRequest) {
  try {
    const context = await resolveAuthenticatedApiContext(request);
    const filters = parseUsuarioListFilters(request.nextUrl.searchParams);
    const result = await new UsuariosApi(
      new BackendApiClient(context.config),
    ).listar(context.accessToken, context.empresaId, filters);

    return NextResponse.json(result, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return apiErrorResponse(error);
  }
}
