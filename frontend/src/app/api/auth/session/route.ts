import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, SESSION_COOKIE_NAME } from "@/lib/server/backend";

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
    return NextResponse.json({ message: "Sessão expirada" }, { status: 401 });
  }

  const data = await backendResponse.json();
  return NextResponse.json(data);
}
