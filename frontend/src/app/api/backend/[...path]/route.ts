import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL, SESSION_COOKIE_NAME } from "@/lib/server/backend";

// Proxy autenticado genérico — o browser nunca fala direto com o FastAPI nem vê o JWT.
// Lê o cookie HttpOnly, encaminha com Authorization: Bearer, repassa a resposta (status,
// corpo e — importante — os 403 de senha pendente, que o client reage a eles).
async function proxy(request: NextRequest, path: string[]) {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.json({ message: "Não autenticado" }, { status: 401 });
  }

  const targetUrl = `${BACKEND_URL}/${path.join("/")}${request.nextUrl.search}`;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";

  const backendResponse = await fetch(targetUrl, {
    method: request.method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(hasBody ? { "Content-Type": "application/json" } : {}),
    },
    body: hasBody ? await request.text() : undefined,
    cache: "no-store",
  });

  if (backendResponse.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const contentType = backendResponse.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return new NextResponse(await backendResponse.text(), { status: backendResponse.status });
  }

  const data = await backendResponse.json().catch(() => null);
  return NextResponse.json(data, { status: backendResponse.status });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, { params }: RouteContext) {
  const { path } = await params;
  return proxy(request, path);
}
