import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { BACKEND_URL, SESSION_COOKIE_NAME } from "@/lib/server/backend";

// Troca OBRIGATÓRIA do primeiro acesso (Fase 10B.1). A sessão (cookie HttpOnly `tf_session`) já existe — o usuário entrou com a senha temporária —, então o corpo
// leva SÓ `novaSenha` e `confirmacaoSenha`: o BFF repassa exatamente esses dois campos (qualquer outro é descartado aqui e, de qualquer forma, o backend os rejeita).
// A senha nunca é registrada, e a resposta nunca é cacheada.
export async function POST(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ message: "Não autenticado" }, { status: 401, headers: { "Cache-Control": "no-store" } });
  }

  const bruto = await request.json().catch(() => null);
  const novaSenha = typeof bruto?.novaSenha === "string" ? bruto.novaSenha : "";
  const confirmacaoSenha = typeof bruto?.confirmacaoSenha === "string" ? bruto.confirmacaoSenha : "";

  const backendResponse = await fetch(`${BACKEND_URL}/auth/definir-senha-inicial`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ novaSenha, confirmacaoSenha }),
    cache: "no-store",
  });

  if (backendResponse.status === 204) {
    return new NextResponse(null, { status: 204, headers: { "Cache-Control": "no-store" } });
  }
  const data = await backendResponse.json().catch(() => null);
  return NextResponse.json(data, { status: backendResponse.status, headers: { "Cache-Control": "no-store" } });
}
