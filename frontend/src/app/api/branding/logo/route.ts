import { NextRequest, NextResponse } from "next/server";
import { obterBranding, urlLogoBackend } from "@/lib/server/branding";

// Logo da Empresa para o navegador (inclusive nas telas de login/recuperação, antes da sessão). Faz proxy do
// endpoint público do backend: a Empresa é SEMPRE a do servidor (EMPRESA_CODIGO), o caminho interno do
// arquivo nunca aparece e o Content-Type vem do backend (canônico, validado pelos bytes) com `nosniff`.
// Os bytes passam crus (arrayBuffer) — um GIF animado chega idêntico, sem recodificar.
export async function GET(request: NextRequest) {
  const branding = await obterBranding();
  if (!branding.logoDisponivel) return new NextResponse(null, { status: 404 });

  try {
    const versaoPedida = request.nextUrl.searchParams.get("v");
    const resposta = await fetch(urlLogoBackend(branding.logoVersao), {
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
        // Versão correta na URL → imutável; sem versão (ou versão antiga) → revalida.
        "Cache-Control":
          versaoPedida && versaoPedida === branding.logoVersao ? "public, max-age=31536000, immutable" : "no-cache",
      },
    });
  } catch {
    return new NextResponse(null, { status: 404 });
  }
}
