import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, SESSION_COOKIE_NAME, sessionCookieOptions } from "@/lib/server/backend";
import { cabecalhosDoCliente } from "@/lib/server/cliente-http";
import { dadosVisuaisDaSessao, sincronizarCookieTema } from "@/lib/server/tema";
import { normalizarSlug } from "@/lib/tenant";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const email = typeof body?.email === "string" ? body.email : "";
  const senha = typeof body?.senha === "string" ? body.senha : "";

  if (!email || !senha) {
    return NextResponse.json({ message: "E-mail e senha são obrigatórios" }, { status: 400 });
  }

  // Fase 9D: a empresa do login vem de UMA fonte — o slug da URL (`/e/<slug>/login`). Sem slug (ou inválido) NÃO existe empresa padrão
  // nem EMPRESA_CODIGO: recusa com a mesma mensagem genérica. `empresaCodigo` nunca é aceito do navegador.
  const slug = normalizarSlug(body?.empresaSlug);
  if (!slug) {
    return NextResponse.json({ message: "Credenciais inválidas" }, { status: 401 });
  }
  const empresa = { empresaSlug: slug };

  const backendResponse = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    // IP original e User-Agent do navegador: sem isto a auditoria de acesso registraria o IP do container do BFF.
    headers: { "Content-Type": "application/json", ...cabecalhosDoCliente(request.headers) },
    body: JSON.stringify({ ...empresa, email, senha }),
    cache: "no-store",
  });

  if (!backendResponse.ok) {
    return NextResponse.json({ message: "Credenciais inválidas" }, { status: backendResponse.status });
  }

  const data = await backendResponse.json();
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE_NAME, data.accessToken, sessionCookieOptions());
  // Sincroniza o cookie-espelho com a preferência REAL do usuário que acabou de entrar (nunca herda a do
  // usuário anterior neste navegador): sem override → cookie removido → vale o tema da empresa.
  const visual = await dadosVisuaisDaSessao(BACKEND_URL, data.accessToken);
  sincronizarCookieTema(cookieStore, visual.preferencia);

  return NextResponse.json({ mustChangePassword: Boolean(data.mustChangePassword) });
}
