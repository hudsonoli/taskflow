import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, EMPRESA_CODIGO, SESSION_COOKIE_NAME, sessionCookieOptions } from "@/lib/server/backend";
import { preferenciaDoBackend, sincronizarCookieTema } from "@/lib/server/tema";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const email = typeof body?.email === "string" ? body.email : "";
  const senha = typeof body?.senha === "string" ? body.senha : "";

  if (!email || !senha) {
    return NextResponse.json({ message: "E-mail e senha são obrigatórios" }, { status: 400 });
  }

  const backendResponse = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ empresaCodigo: EMPRESA_CODIGO, email, senha }),
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
  sincronizarCookieTema(cookieStore, await preferenciaDoBackend(BACKEND_URL, data.accessToken));

  return NextResponse.json({ mustChangePassword: Boolean(data.mustChangePassword) });
}
