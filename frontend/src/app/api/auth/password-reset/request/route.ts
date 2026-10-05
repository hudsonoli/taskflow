import { NextResponse } from "next/server";
import { BACKEND_URL, EMPRESA_CODIGO } from "@/lib/server/backend";

// Mesma mensagem que o backend devolve — o BFF nunca a varia por conta/e-mail (anti-enumeration).
const MENSAGEM_PUBLICA =
  "Se existir uma conta habilitada para este e-mail, você receberá as instruções para redefinir a senha.";
// O backend envia o e-mail DENTRO do pedido (SMTP com timeout de poucos segundos): folga para isso.
const TIMEOUT_MS = 20_000;

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const email = typeof body?.email === "string" ? body.email.trim() : "";

  if (!email || email.length > 255) {
    return NextResponse.json({ message: "Informe um e-mail válido." }, { status: 400 });
  }

  // `empresaCodigo` é SEMPRE o do servidor (EMPRESA_CODIGO) — nunca aceito do navegador.
  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${BACKEND_URL}/auth/password-reset/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ empresaCodigo: EMPRESA_CODIGO, email }),
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    return NextResponse.json({ message: "Não foi possível processar o pedido agora. Tente novamente em instantes." }, { status: 502 });
  }

  // Só falha TÉCNICA (backend fora do ar/5xx) vira erro; todo pedido de formato válido recebe a
  // mesma resposta, exista a conta ou não.
  if (backendResponse.status >= 500) {
    return NextResponse.json({ message: "Não foi possível processar o pedido agora. Tente novamente em instantes." }, { status: 502 });
  }
  if (!backendResponse.ok) {
    return NextResponse.json({ message: "Informe um e-mail válido." }, { status: 400 });
  }
  return NextResponse.json({ message: MENSAGEM_PUBLICA });
}
