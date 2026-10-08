import { NextRequest, NextResponse } from "next/server";
import { obterBrandingPublico, urlLogoBackend, type AlvoBranding } from "@/lib/server/branding";
import { normalizarSlug } from "@/lib/tenant";

// Logo PÚBLICO de uma empresa para o navegador (inclusive nas telas de login/recuperação, antes da sessão). Dois
// alvos, nenhum deles vindo de autorização: `?slug=<slug>` (rota pública por slug — empresa inativa/inexistente = 404)
// ou, sem `slug`, a empresa padrão do servidor (acesso legado `/login`). O caminho interno do arquivo nunca aparece e o
// Content-Type vem do backend (canônico, validado pelos bytes) com `nosniff`. NÃO é uma rota de arquivos arbitrários:
// só existe o logo da empresa do slug, buscado no endpoint público do backend. Os bytes passam crus (arrayBuffer) —
// um GIF animado chega idêntico, sem recodificar.
export async function GET(request: NextRequest) {
  const parametroSlug = request.nextUrl.searchParams.get("slug");
  let alvo: AlvoBranding = { tipo: "legado" };
  if (parametroSlug !== null) {
    const slug = normalizarSlug(parametroSlug);
    if (!slug) return new NextResponse(null, { status: 404 });
    alvo = { tipo: "slug", slug };
  }

  const publico = await obterBrandingPublico(alvo);
  if (!publico.disponivel || !publico.branding.logoDisponivel) return new NextResponse(null, { status: 404 });

  try {
    const versaoPedida = request.nextUrl.searchParams.get("v");
    const resposta = await fetch(urlLogoBackend(alvo, publico.branding.logoVersao), {
      cache: "no-store",
      signal: AbortSignal.timeout(4_000),
    });
    const tipo = resposta.headers.get("content-type");
    if (!resposta.ok || (tipo !== "image/png" && tipo !== "image/gif")) {
      return new NextResponse(null, { status: 404 });
    }
    return new NextResponse(await resposta.arrayBuffer(), {
      status: 200,
      headers: {
        "Content-Type": tipo,
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": "inline",
        // Versão correta na URL → imutável; sem versão (ou versão antiga) → revalida. A URL já carrega o slug,
        // então o cache do navegador também é por empresa.
        "Cache-Control":
          versaoPedida && versaoPedida === publico.branding.logoVersao ? "public, max-age=31536000, immutable" : "no-cache",
      },
    });
  } catch {
    return new NextResponse(null, { status: 404 });
  }
}
