import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL, PLATFORM_COOKIE_NAME, PLATFORM_COOKIE_PATH } from "@/lib/server/backend";

// Proxy da Administração da Plataforma: lê SOMENTE o cookie HttpOnly `tf_platform` e encaminha a `/plataforma/*` do
// FastAPI. Nunca usa `tf_session` (o backend também recusaria: token tenant não entra em /plataforma). O navegador
// não fala direto com o backend nem enxerga o token. Não existe DELETE de empresa no backend (empresa nunca é
// apagada); o DELETE aqui só serve ao branding (restaurar padrão / remover logo).
async function proxy(request: NextRequest, path: string[]) {
  const cookieStore = await cookies();
  const token = cookieStore.get(PLATFORM_COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ message: "Sessão de plataforma ausente" }, { status: 401 });

  const targetUrl = `${BACKEND_URL}/plataforma/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const contentTypeOriginal = request.headers.get("content-type");
  const ehMultipart = contentTypeOriginal?.includes("multipart/form-data") ?? false;

  const resposta = await fetch(targetUrl, {
    method: request.method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(hasBody ? { "Content-Type": contentTypeOriginal ?? "application/json" } : {}),
    },
    body: hasBody ? (ehMultipart ? await request.arrayBuffer() : await request.text()) : undefined,
    cache: "no-store",
  });

  // Token expirado/inválido (401) ou autoridade revogada (403): derruba o cookie — a próxima tentativa passa por
  // POST /api/plataforma/sessao, que só reemite para quem ainda é administrador ativo.
  if (resposta.status === 401 || resposta.status === 403) {
    cookieStore.delete({ name: PLATFORM_COOKIE_NAME, path: PLATFORM_COOKIE_PATH });
  }

  if (resposta.status === 204) return new NextResponse(null, { status: 204 });

  const contentType = resposta.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    const buffer = await resposta.arrayBuffer();
    const headers = new Headers();
    headers.set("content-type", contentType || "application/octet-stream");
    const nosniff = resposta.headers.get("x-content-type-options");
    if (nosniff) headers.set("x-content-type-options", nosniff);
    const cacheControl = resposta.headers.get("cache-control");
    if (cacheControl) headers.set("cache-control", cacheControl);
    return new NextResponse(buffer, { status: resposta.status, headers });
  }

  const dados = await resposta.json().catch(() => null);
  return NextResponse.json(dados, { status: resposta.status });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

export async function POST(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

export async function PATCH(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}

export async function DELETE(request: NextRequest, { params }: RouteContext) {
  return proxy(request, (await params).path);
}
