import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE_NAME } from "@/lib/server/backend";
import {
  MENSAGENS_CONSULTA,
  TIMEOUT_SERVIDOR_MS,
  URL_BRASILAPI_CNPJ,
  USER_AGENT_CONSULTA,
  cnpjValido,
  falhaPorStatus,
  mapearRespostaBrasilApi,
  somenteDigitos,
  type FalhaConsulta,
} from "@/lib/brasilApi";

// Consulta de CNPJ na BrasilAPI (pública, sem chave): o navegador pede AQUI, nunca direto ao serviço externo (sem CORS,
// com timeout e erros normalizados). Exige sessão só para não virar proxy aberto; não envia nem guarda nada do usuário —
// o único dado que sai é o CNPJ (que é público). Toda falha vira `{ falha, mensagem }`: o formulário segue manual.
function erro(falha: FalhaConsulta, status: number) {
  return NextResponse.json({ falha, mensagem: MENSAGENS_CONSULTA[falha] }, { status });
}

export async function GET(_request: Request, { params }: { params: Promise<{ cnpj: string }> }) {
  const cookieStore = await cookies();
  if (!cookieStore.get(SESSION_COOKIE_NAME)?.value) return NextResponse.json({ message: "Não autenticado" }, { status: 401 });

  const digitos = somenteDigitos((await params).cnpj);
  if (!cnpjValido(digitos)) return erro("invalido", 422);

  let resposta: Response;
  try {
    resposta = await fetch(`${URL_BRASILAPI_CNPJ}/${digitos}`, {
      headers: { Accept: "application/json", "User-Agent": USER_AGENT_CONSULTA },
      cache: "no-store",
      signal: AbortSignal.timeout(TIMEOUT_SERVIDOR_MS),
    });
  } catch (falhou) {
    const estourou = falhou instanceof Error && (falhou.name === "TimeoutError" || falhou.name === "AbortError");
    return estourou ? erro("timeout", 504) : erro("rede", 502);
  }

  if (!resposta.ok) {
    const falha = falhaPorStatus(resposta.status);
    return erro(falha, falha === "nao_encontrado" ? 404 : falha === "limite" ? 429 : 502);
  }
  const dados = mapearRespostaBrasilApi(await resposta.json().catch(() => null));
  if (!dados) return erro("nao_encontrado", 404);
  return NextResponse.json({ dados });
}
