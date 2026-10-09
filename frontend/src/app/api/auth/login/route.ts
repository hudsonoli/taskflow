import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, EMPRESA_CODIGO, SESSION_COOKIE_NAME, sessionCookieOptions } from "@/lib/server/backend";
import { cabecalhosDoCliente } from "@/lib/server/cliente-http";
import { dadosVisuaisDaSessao, sincronizarCookieTema, sincronizarCookieTenant } from "@/lib/server/tema";
import { normalizarSlug } from "@/lib/tenant";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const email = typeof body?.email === "string" ? body.email : "";
  const senha = typeof body?.senha === "string" ? body.senha : "";

  if (!email || !senha) {
    return NextResponse.json({ message: "E-mail e senha são obrigatórios" }, { status: 400 });
  }

  // A empresa do login vem de UMA fonte: o slug da URL (`/e/<slug>/login`, a chave pública inicial) ou, SEM slug, o
  // acesso legado `/login` com a empresa padrão do servidor (EMPRESA_CODIGO). Slug presente porém inválido NÃO cai no
  // legado: é recusado com a mesma mensagem genérica. `empresaCodigo` nunca é aceito do navegador.
  const slugInformado = body?.empresaSlug;
  const slug = normalizarSlug(slugInformado);
  if (slugInformado !== undefined && slugInformado !== null && !slug) {
    return NextResponse.json({ message: "Credenciais inválidas" }, { status: 401 });
  }
  const empresa = slug ? { empresaSlug: slug } : { empresaCodigo: EMPRESA_CODIGO };

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
  // O cookie visual do tenant espelha a empresa da SESSÃO que o backend acabou de emitir (não o slug digitado).
  sincronizarCookieTenant(cookieStore, visual.empresaSlug);

  return NextResponse.json({ mustChangePassword: Boolean(data.mustChangePassword) });
}
