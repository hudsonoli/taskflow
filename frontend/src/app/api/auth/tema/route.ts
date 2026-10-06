import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, SESSION_COOKIE_NAME } from "@/lib/server/backend";
import { sincronizarCookieTema } from "@/lib/server/tema";
import { temaPreferenciaValido } from "@/lib/tema";

// Preferência PESSOAL de tema do usuário autenticado: grava no backend (PATCH /usuarios/me/preferencias — a
// identidade vem do token, nunca do corpo) e, só se o backend aceitar, atualiza o cookie-espelho do SSR.
// Corpo: { "tema": "claro" | "escuro" | "sistema" | null }  (null = usar o padrão da empresa).
export async function PATCH(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!token) return NextResponse.json({ message: "Não autenticado" }, { status: 401 });

  const corpo = (await request.json().catch(() => null)) as { tema?: unknown } | null;
  const tema = corpo?.tema;
  if (!(tema === null || temaPreferenciaValido(tema))) {
    return NextResponse.json({ message: "Tema inválido" }, { status: 422 });
  }

  const resposta = await fetch(`${BACKEND_URL}/usuarios/me/preferencias`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ tema }),
    cache: "no-store",
  });
  if (!resposta.ok) {
    return NextResponse.json({ message: "Não foi possível salvar o tema" }, { status: resposta.status });
  }
  const dados = (await resposta.json().catch(() => null)) as { temaPreferencia?: unknown } | null;
  const salvo = sincronizarCookieTema(cookieStore, dados?.temaPreferencia);
  return NextResponse.json({ temaPreferencia: salvo });
}
