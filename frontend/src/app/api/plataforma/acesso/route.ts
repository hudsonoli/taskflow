import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, SESSION_COOKIE_NAME } from "@/lib/server/backend";

// Fonte de verdade da UI para mostrar (ou não) a entrada "Administração da Plataforma": pergunta ao backend, com a
// sessão tenant, se o usuário é Administrador da Plataforma ativo. Nunca decide por e-mail, perfil ou conta de
// sistema. Qualquer falha → `false` (a UI esconde a entrada; a API continua sendo a barreira real).
export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ administradorPlataforma: false }, { status: 401 });

  try {
    const resposta = await fetch(`${BACKEND_URL}/plataforma/acesso`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.timeout(4_000),
    });
    if (!resposta.ok) return NextResponse.json({ administradorPlataforma: false });
    const dados = await resposta.json().catch(() => null);
    return NextResponse.json({ administradorPlataforma: dados?.administradorPlataforma === true });
  } catch {
    return NextResponse.json({ administradorPlataforma: false });
  }
}
