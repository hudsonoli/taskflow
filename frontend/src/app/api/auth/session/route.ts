import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, SESSION_COOKIE_NAME } from "@/lib/server/backend";
import { sincronizarCookieTema, sincronizarCookieTenant } from "@/lib/server/tema";
import { COOKIE_TENANT_SLUG, normalizarSlug } from "@/lib/tenant";
import { COOKIE_TEMA } from "@/lib/tema";

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;

  if (!token) {
    return NextResponse.json({ message: "Não autenticado" }, { status: 401 });
  }

  const backendResponse = await fetch(`${BACKEND_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!backendResponse.ok) {
    // Token inválido/expirado — limpa o cookie pra não ficar tentando de novo.
    cookieStore.delete(SESSION_COOKIE_NAME);
    cookieStore.delete(COOKIE_TEMA);
    // O cookie visual do tenant FICA: é ele que leva o usuário de volta ao login da empresa certa.
    return NextResponse.json({ message: "Sessão expirada" }, { status: 401 });
  }

  const data = await backendResponse.json();
  // Reconcilia o cookie-espelho com o banco (outra aba/computador pode ter mudado a preferência).
  sincronizarCookieTema(cookieStore, data?.temaPreferencia);
  // Reconcilia o cookie visual do tenant com a empresa da SESSÃO (a verdade é o backend, nunca o cookie).
  const slugDaSessao = normalizarSlug(data?.empresaSlug);
  if (slugDaSessao !== normalizarSlug(cookieStore.get(COOKIE_TENANT_SLUG)?.value)) sincronizarCookieTenant(cookieStore, slugDaSessao);
  return NextResponse.json(data);
}
