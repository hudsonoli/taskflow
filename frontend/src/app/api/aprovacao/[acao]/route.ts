import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/server/backend";
import { normalizarSlug } from "@/lib/tenant";

// BFF DEDICADO do Portal Externo de Aprovação (Fase 9B). NÃO é o `/api/backend`:
//   - não exige nem lê `tf_session` (nenhum cookie é repassado ao backend e nenhum `Authorization` é enviado: o cliente do portal não tem sessão);
//   - não repassa headers arbitrários do navegador (só o `Content-Type` fixo);
//   - só existem 4 ações fechadas, cada uma com um corpo JSON ESTRITO — campos desconhecidos são descartados aqui e recusados no backend;
//   - o token vai SÓ no corpo (nunca em path/query, que acabariam em log de acesso/proxy) e nunca é registrado.
// A empresa, a Demanda e os arquivos são resolvidos no backend a partir do token; este arquivo não conhece nenhum deles. O `slug` só é conferido lá.

export const dynamic = "force-dynamic";

const ACOES = ["consultar", "decisao", "artefato", "logo"] as const;
type Acao = (typeof ACOES)[number];

const TIMEOUT_MS = 20_000;
const CORPO_MAX = 16 * 1024;
const TOKEN = /^[A-Za-z0-9_-]{43}$/;
const MENSAGEM_INDISPONIVEL = "Este link de aprovação não está mais disponível.";
const NEUTROS = { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff" };

function json(corpo: unknown, status: number) {
  return NextResponse.json(corpo, { status, headers: NEUTROS });
}

function corpoDaAcao(acao: Acao, bruto: Record<string, unknown>): Record<string, unknown> | null {
  const token = bruto.token;
  if (typeof token !== "string" || !TOKEN.test(token)) return null;
  // Fase 9D: o slug da URL `/e/<slug>/aprovacao` vai junto como CONFERÊNCIA (o backend compara com a empresa do token). Sem slug válido = link inexistente.
  const slug = normalizarSlug(bruto.slug);
  if (!slug) return null;
  if (acao === "consultar" || acao === "logo") return { slug, token };
  if (acao === "artefato") {
    const ordem = bruto.ordem;
    return typeof ordem === "number" && Number.isInteger(ordem) ? { slug, token, ordem } : { slug, token, ordem: 0 };
  }
  return {
    slug,
    token,
    decisao: bruto.decisao,
    nome: bruto.nome,
    email: bruto.email ?? null,
    motivo: bruto.motivo ?? null,
  };
}

export async function POST(request: Request, contexto: { params: Promise<{ acao: string }> }) {
  const { acao } = await contexto.params;
  if (!(ACOES as readonly string[]).includes(acao)) return json({ detail: MENSAGEM_INDISPONIVEL }, 404);

  const texto = await request.text().catch(() => "");
  if (texto.length > CORPO_MAX) return json({ detail: "Requisição inválida" }, 413);
  let bruto: unknown = null;
  try {
    bruto = JSON.parse(texto);
  } catch {
    return json({ detail: "Requisição inválida" }, 422);
  }
  if (!bruto || typeof bruto !== "object" || Array.isArray(bruto)) return json({ detail: "Requisição inválida" }, 422);

  const corpo = corpoDaAcao(acao as Acao, bruto as Record<string, unknown>);
  if (!corpo) return json({ detail: MENSAGEM_INDISPONIVEL }, 404); // token malformado = link inexistente

  let resposta: Response;
  try {
    resposta = await fetch(`${BACKEND_URL}/publico/aprovacoes/${acao}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    return json({ detail: "Não foi possível falar com o servidor agora. Tente novamente em instantes." }, 502);
  }

  if (acao === "artefato" || acao === "logo") {
    if (!resposta.ok || !resposta.body) return json({ detail: MENSAGEM_INDISPONIVEL }, resposta.status === 404 ? 404 : 502);
    const cabecalhos: Record<string, string> = { ...NEUTROS, "Content-Security-Policy": "default-src 'none'; sandbox" };
    for (const nome of ["content-type", "content-disposition"]) {
      const valor = resposta.headers.get(nome);
      if (valor) cabecalhos[nome] = valor;
    }
    return new NextResponse(resposta.body, { status: 200, headers: cabecalhos });
  }

  const dados = await resposta.json().catch(() => null);
  if (resposta.ok) return json(dados, 200);
  if (resposta.status === 404) return json({ detail: MENSAGEM_INDISPONIVEL }, 404);
  if (resposta.status === 409 || resposta.status === 422) return json({ detail: dados?.detail ?? "Requisição inválida" }, resposta.status);
  return json({ detail: "Não foi possível concluir agora. Tente novamente em instantes." }, 502);
}
