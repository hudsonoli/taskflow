import { NextResponse, type NextRequest } from "next/server";
import { CONTEXTO_APROVACAO, HEADER_CONTEXTO, HEADER_TENANT_SLUG, ehRotaDaPlataforma, ehRotaDeAprovacaoExterna, slugDaRota } from "./lib/tenant";

// Contexto de empresa das telas públicas. O layout raiz (que escreve tema/cores no <html>) não recebe o caminho, então
// este proxy o traduz em headers INTERNOS de requisição:
//   x-tf-tenant-slug  → só em `/e/<slug>/...`, já validado (3–40, [a-z0-9-], não reservado)
//   x-tf-contexto     → `plataforma` em `/plataforma/**` (o console mantém a identidade da plataforma) e `aprovacao` em `/e/<slug>/aprovacao`
//                       (Portal Externo de Aprovação: marca neutra no HTML inicial, sem herdar sessão/cookie do tenant e SEM header de slug —
//                       a empresa do portal vem do token; o slug da URL só é conferido contra ela)
// Os dois são SEMPRE apagados do que chegou do navegador antes de decidir: ninguém forja contexto por header. E nenhum
// dos dois autoriza coisa alguma — só escolhe qual marca pública renderizar.
export function proxy(request: NextRequest) {
  const headers = new Headers(request.headers);
  headers.delete(HEADER_TENANT_SLUG);
  headers.delete(HEADER_CONTEXTO);

  const { pathname } = request.nextUrl;
  const portal = ehRotaDeAprovacaoExterna(pathname);
  const slug = portal ? null : slugDaRota(pathname);
  if (slug) headers.set(HEADER_TENANT_SLUG, slug);
  if (ehRotaDaPlataforma(pathname)) headers.set(HEADER_CONTEXTO, "plataforma");
  if (portal) headers.set(HEADER_CONTEXTO, CONTEXTO_APROVACAO);

  const resposta = NextResponse.next({ request: { headers } });
  if (portal) {
    // O link do portal é uma capability: nada de cache, de indexação nem de Referer (o fragmento nunca sai do navegador, mas a origem também não).
    resposta.headers.set("Cache-Control", "no-store");
    resposta.headers.set("Referrer-Policy", "no-referrer");
    resposta.headers.set("X-Robots-Tag", "noindex, nofollow");
  }
  return resposta;
}

export const config = {
  // Só páginas: nem BFF (`/api`) nem estáticos precisam do contexto.
  matcher: ["/((?!api/|_next/static|_next/image|favicon.ico).*)"],
};
