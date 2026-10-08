import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import {
  BACKEND_URL,
  PLATFORM_COOKIE_NAME,
  PLATFORM_COOKIE_PATH,
  SESSION_COOKIE_NAME,
  platformCookieOptions,
} from "@/lib/server/backend";

// Abre a sessão de plataforma a partir da sessão TENANT válida (tf_session): o backend troca o token tenant por um
// token curto `tipo="plataforma"` — e só o faz para Administrador da Plataforma ativo (senão 403). O token novo vai
// direto para o cookie HttpOnly `tf_platform`; o corpo da resposta NUNCA o devolve ao navegador.
export async function POST() {
  const cookieStore = await cookies();
  const tokenTenant = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!tokenTenant) return NextResponse.json({ message: "Não autenticado" }, { status: 401 });

  const resposta = await fetch(`${BACKEND_URL}/plataforma/sessao`, {
    method: "POST",
    headers: { Authorization: `Bearer ${tokenTenant}` },
    cache: "no-store",
  });
  if (!resposta.ok) {
    cookieStore.delete({ name: PLATFORM_COOKIE_NAME, path: PLATFORM_COOKIE_PATH });
    return NextResponse.json({ message: "Acesso negado" }, { status: resposta.status === 401 ? 401 : 403 });
  }

  const dados = await resposta.json();
  const segundos = Number.isFinite(dados?.expiresIn) && dados.expiresIn > 0 ? Math.floor(dados.expiresIn) : 15 * 60;
  cookieStore.set(PLATFORM_COOKIE_NAME, dados.accessToken, platformCookieOptions(segundos));
  return NextResponse.json({ ok: true, expiresIn: segundos });
}

// Encerra só a sessão de plataforma (a sessão tenant continua).
export async function DELETE() {
  const cookieStore = await cookies();
  cookieStore.delete({ name: PLATFORM_COOKIE_NAME, path: PLATFORM_COOKIE_PATH });
  return NextResponse.json({ ok: true });
}
