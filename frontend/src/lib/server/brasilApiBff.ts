import "server-only";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE_NAME } from "@/lib/server/backend";
import { TIMEOUT_SERVIDOR_MS, USER_AGENT_CONSULTA, falhaPorStatus, type FalhaConsulta } from "@/lib/brasilApi";

// Parte do servidor COMPARTILHADA pelas rotas de consulta na BrasilAPI (CNPJ e CEP): exigir sessão, chamar o serviço público
// com User-Agent identificável e timeout, e traduzir qualquer falha em uma falha normalizada. Sem segredo (integração pública),
// sem log e sem guardar nada do usuário — o único dado que sai é o CNPJ/CEP consultado.

/** `null` se há sessão tenant; senão a resposta 401 pronta (a rota existe só para quem está logado: não vira proxy aberto). */
export async function exigirSessaoTenant(): Promise<NextResponse | null> {
  const cookieStore = await cookies();
  return cookieStore.get(SESSION_COOKIE_NAME)?.value ? null : NextResponse.json({ message: "Não autenticado" }, { status: 401 });
}

export type RespostaBrasilApi = { ok: true; corpo: unknown } | { ok: false; falha: FalhaConsulta; status: number };

const STATUS_DA_FALHA: Record<FalhaConsulta, number> = {
  invalido: 422,
  nao_encontrado: 404,
  limite: 429,
  indisponivel: 502,
  timeout: 504,
  rede: 502,
};

export function statusDaFalha(falha: FalhaConsulta): number {
  return STATUS_DA_FALHA[falha];
}

/** Resposta de falha do BFF: `{ falha, mensagem }` (o cliente usa `falha`; a mensagem é do domínio de quem chama). */
export function respostaDeFalha(falha: FalhaConsulta, mensagens: Record<FalhaConsulta, string>): NextResponse {
  return NextResponse.json({ falha, mensagem: mensagens[falha] }, { status: STATUS_DA_FALHA[falha] });
}

export async function chamarBrasilApi(url: string): Promise<RespostaBrasilApi> {
  let resposta: Response;
  try {
    resposta = await fetch(url, {
      headers: { Accept: "application/json", "User-Agent": USER_AGENT_CONSULTA },
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_SERVIDOR_MS),
    });
  } catch (falhou) {
    const estourou = falhou instanceof Error && (falhou.name === "TimeoutError" || falhou.name === "AbortError");
    const falha: FalhaConsulta = estourou ? "timeout" : "rede";
    return { ok: false, falha, status: STATUS_DA_FALHA[falha] };
  }
  if (!resposta.ok) {
    const falha = falhaPorStatus(resposta.status);
    return { ok: false, falha, status: STATUS_DA_FALHA[falha] };
  }
  return { ok: true, corpo: await resposta.json().catch(() => null) };
}
