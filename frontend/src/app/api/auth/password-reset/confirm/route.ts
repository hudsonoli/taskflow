import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/server/backend";
import { normalizarSlug } from "@/lib/tenant";

const MENSAGEM_LINK_INVALIDO = "Este link é inválido ou expirou. Solicite uma nova redefinição de senha.";
const TIMEOUT_MS = 15_000;

// Confirma a nova senha com o token do e-mail. NÃO cria sessão (nenhum cookie tf_session): o usuário
// volta ao login e entra com a senha nova.
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const token = typeof body?.token === "string" ? body.token : "";
  const novaSenha = typeof body?.novaSenha === "string" ? body.novaSenha : "";
  const confirmacaoSenha = typeof body?.confirmacaoSenha === "string" ? body.confirmacaoSenha : "";

  if (!token) {
    return NextResponse.json({ message: MENSAGEM_LINK_INVALIDO }, { status: 400 });
  }
  if (!novaSenha || !confirmacaoSenha) {
    return NextResponse.json({ message: "Informe e confirme a nova senha." }, { status: 422 });
  }

  // O link do e-mail aponta para `/e/<slug>/redefinir-senha`: o slug da URL escolhe a empresa e o backend confere que o token pertence a ela
  // (token de outra empresa = mesmo "link inválido"). Fase 9D: sem slug válido não há empresa padrão — mesmo "link inválido".
  const slug = normalizarSlug(body?.empresaSlug);
  if (!slug) {
    return NextResponse.json({ message: MENSAGEM_LINK_INVALIDO }, { status: 400 });
  }
  const empresa = { empresaSlug: slug };

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${BACKEND_URL}/auth/password-reset/confirm`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...empresa, token, novaSenha, confirmacaoSenha }),
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    return NextResponse.json({ message: "Não foi possível redefinir a senha agora. Tente novamente em instantes." }, { status: 502 });
  }

  if (backendResponse.ok) {
    return NextResponse.json({ ok: true });
  }
  if (backendResponse.status === 400) {
    return NextResponse.json({ message: MENSAGEM_LINK_INVALIDO }, { status: 400 });
  }
  if (backendResponse.status === 422) {
    // Política de senha com token válido: a mensagem do backend ("mínimo de 8 caracteres" etc.).
    const data = await backendResponse.json().catch(() => null);
    const detail = typeof data?.detail === "string" ? data.detail : "A nova senha não atende aos requisitos.";
    return NextResponse.json({ message: detail }, { status: 422 });
  }
  return NextResponse.json({ message: "Não foi possível redefinir a senha agora. Tente novamente em instantes." }, { status: 502 });
}
