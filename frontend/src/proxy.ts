import { NextResponse, type NextRequest } from "next/server";
import { HEADER_CONTEXTO, HEADER_TENANT_SLUG, ehRotaDaPlataforma, slugDaRota } from "./lib/tenant";

// Contexto de empresa das telas públicas. O layout raiz (que escreve tema/cores no <html>) não recebe o caminho, então
// este proxy o traduz em headers INTERNOS de requisição:
//   x-tf-tenant-slug  → só em `/e/<slug>/...`, já validado (3–40, [a-z0-9-], não reservado)
//   x-tf-contexto     → `plataforma` em `/plataforma/**` (o console mantém a identidade da plataforma)
// Os dois são SEMPRE apagados do que chegou do navegador antes de decidir: ninguém forja contexto por header. E nenhum
// dos dois autoriza coisa alguma — só escolhe qual marca pública renderizar.
export function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.delete(HEADER_TENANT_SLUG);
  headers.delete(HEADER_CONTEXTO);

  const { pathname } = request.nextUrl;
  const slug = slugDaRota(pathname);
  if (slug) headers.set(HEADER_TENANT_SLUG, slug);
  if (ehRotaDaPlataforma(pathname)) headers.set(HEADER_CONTEXTO, "plataforma");

  return NextResponse.next({ request: { headers } });
}

export const config = {
  // Só páginas: nem BFF (`/api`) nem estáticos precisam do contexto.
  matcher: ["/((?!api/|_next/static|_next/image|favicon.ico).*)"],
};
