import { NextRequest, NextResponse } from "next/server";
import {
  BackendApiClient,
  resolveAuthenticatedApiContext,
} from "../../../lib/api/backend";
import { apiErrorResponse } from "../../../lib/api/errors";
import {
  parseUsuarioListFilters,
  UsuariosApi,
} from "../../../lib/api/usuarios";

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
