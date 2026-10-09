import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, EMPRESA_CODIGO, SESSION_COOKIE_NAME, sessionCookieOptions } from "@/lib/server/backend";
import { cabecalhosDoCliente } from "@/lib/server/cliente-http";
import { dadosVisuaisDaSessao, sincronizarCookieTema, sincronizarCookieTenant } from "@/lib/server/tema";
import { normalizarSlug } from "@/lib/tenant";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const email = typeof body?.email === "string" ? body.email : "";
  const idToken = typeof body?.idToken === "string" ? body.idToken : "";

  if (!email || !idToken) {
    return NextResponse.json({ message: "E-mail e identidade Google são obrigatórios" }, { status: 400 });
  }

  // Mesma regra do login local: slug da URL (`/e/<slug>/login`) ou, sem slug, a empresa padrão do servidor (legado).
  const slugInformado = body?.empresaSlug;
  const slug = normalizarSlug(slugInformado);
  if (slugInformado !== undefined && slugInformado !== null && !slug) {
    return NextResponse.json({ message: "Não foi possível entrar com Google" }, { status: 403 });
  }
  const empresa = slug ? { empresaSlug: slug } : { empresaCodigo: EMPRESA_CODIGO };

  const backendResponse = await fetch(`${BACKEND_URL}/auth/google`, {
    method: "POST",
    // IP original e User-Agent do navegador: sem isto a auditoria de acesso registraria o IP do container do BFF.
    headers: { "Content-Type": "application/json", ...cabecalhosDoCliente(request.headers) },
    body: JSON.stringify({ ...empresa, email, idToken }),
    cache: "no-store",
  });

  if (!backendResponse.ok) {
    // Repassa a mensagem genérica que o backend já devolveu (nunca diferencia motivo) e o
    // status real (401 token inválido / 403 sem autorização) — ver AuthService.login_google.
    const data = await backendResponse.json().catch(() => null);
    return NextResponse.json({ message: data?.detail ?? "Não foi possível entrar com Google" }, { status: backendResponse.status });
  }

  const data = await backendResponse.json();
  const cookieStore = await cookies();
  cookieStore.set(SESSION_COOKIE_NAME, data.accessToken, sessionCookieOptions());
  // Sincroniza o cookie-espelho com a preferência REAL do usuário que acabou de entrar (nunca herda a do
  // usuário anterior neste navegador): sem override → cookie removido → vale o tema da empresa.
  const visual = await dadosVisuaisDaSessao(BACKEND_URL, data.accessToken);
  sincronizarCookieTema(cookieStore, visual.preferencia);
  sincronizarCookieTenant(cookieStore, visual.empresaSlug);

  return NextResponse.json({ mustChangePassword: Boolean(data.mustChangePassword) });
}
