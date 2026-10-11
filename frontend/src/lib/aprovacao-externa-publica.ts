// Portal Externo de Aprovação — lado PÚBLICO (Fase 9B). Lógica PURA + cliente do BFF dedicado (`/api/aprovacao/*`), testável com `node --test`.
//
// Superfície do cliente: SEM sessão, SEM cookies (`credentials: "omit"`), SEM headers próprios, SEM `Referer`. O token vem do FRAGMENTO da URL
// (`/e/<slug>/aprovacao#token=…`: o navegador não o envia ao servidor web), vive só em memória e viaja SÓ no corpo JSON dos POSTs — nunca em
// path/query, log, analytics, mensagem de erro ou console. O SLUG da URL também vai no corpo, mas só como CONFERÊNCIA: o backend o compara com a
// empresa do token e, se diferir, responde o mesmo 404 neutro (o slug nunca concede acesso). Artefatos são pedidos pela ORDEM (1..N), nunca por id.
import type {
  AprovacaoPublica,
  DecisaoPublica,
  DecisaoPublicaEntrada,
  EstadoPublicoAprovacao,
} from "../types/aprovacao-externa.ts";

export const MENSAGEM_LINK_INDISPONIVEL = "Este link de aprovação não está mais disponível.";
export const NOME_MIN = 3;
export const NOME_MAX = 120;
export const MOTIVO_MIN = 3;
export const MOTIVO_MAX = 1000;
export const BASE_BFF = "/api/aprovacao";

const TOKEN_REGEX = /^[A-Za-z0-9_-]{43}$/;
const EMAIL_REGEX = /^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$/;

/** `#token=<valor>` → `<valor>` se tiver o formato de um token do portal (43 caracteres base64url); qualquer outra coisa → `null`. */
export function extrairTokenDoFragmento(hash: string): string | null {
  const parametros = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
  const token = parametros.get("token")?.trim() ?? "";
  return TOKEN_REGEX.test(token) ? token : null;
}

// ── validações (espelham o backend, que continua sendo a autoridade) ──────────────────────────────────

function temHtml(texto: string): boolean {
  return texto.includes("<") || texto.includes(">");
}

export function erroDoNome(nome: string): string | null {
  const limpo = nome.trim().replace(/\s+/g, " ");
  if (limpo.length === 0) return "Informe seu nome.";
  if (limpo.length < NOME_MIN) return `O nome precisa ter ao menos ${NOME_MIN} caracteres.`;
  if (limpo.length > NOME_MAX) return `O nome pode ter no máximo ${NOME_MAX} caracteres.`;
  if (temHtml(limpo)) return "O nome não pode conter marcação HTML.";
  return null;
}

/** E-mail é opcional; se informado, precisa ter formato válido. */
export function erroDoEmail(email: string): string | null {
  const limpo = email.trim();
  if (limpo.length === 0) return null;
  if (limpo.length > 254 || !EMAIL_REGEX.test(limpo)) return "Informe um e-mail válido ou deixe em branco.";
  return null;
}

export function erroDoMotivoDeAjustes(motivo: string): string | null {
  const limpo = motivo.trim();
  if (limpo.length === 0) return "Descreva os ajustes necessários.";
  if (limpo.length < MOTIVO_MIN) return `A descrição precisa ter ao menos ${MOTIVO_MIN} caracteres.`;
  if (limpo.length > MOTIVO_MAX) return `A descrição pode ter no máximo ${MOTIVO_MAX} caracteres.`;
  if (temHtml(limpo)) return "A descrição não pode conter marcação HTML.";
  return null;
}

export function erroDaDecisao(entrada: { decisao: DecisaoPublica; nome: string; email: string; motivo: string }): string | null {
  return (
    erroDoNome(entrada.nome) ??
    erroDoEmail(entrada.email) ??
    (entrada.decisao === "solicitar_ajustes" ? erroDoMotivoDeAjustes(entrada.motivo) : null)
  );
}

export function montarDecisao(entrada: { decisao: DecisaoPublica; nome: string; email: string; motivo: string }): DecisaoPublicaEntrada {
  return {
    decisao: entrada.decisao,
    nome: entrada.nome.trim().replace(/\s+/g, " "),
    email: entrada.email.trim() === "" ? null : entrada.email.trim(),
    motivo: entrada.decisao === "solicitar_ajustes" ? entrada.motivo.trim() : null,
  };
}

export function rotuloEstadoPublico(estado: EstadoPublicoAprovacao): string {
  if (estado === "aprovada") return "Aprovado";
  if (estado === "ajustes_solicitados") return "Ajustes solicitados";
  return "Aguardando sua resposta";
}

export function formatarTamanhoPublico(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ── cliente do BFF ───────────────────────────────────────────────────────────────────────────────

/** 404 neutro: link inexistente, revogado, expirado ou obsoleto — a interface não distingue (nem o servidor). */
export class LinkIndisponivelError extends Error {
  constructor() {
    super(MENSAGEM_LINK_INDISPONIVEL);
    this.name = "LinkIndisponivelError";
  }
}

/** 409 `APROVACAO_JA_DECIDIDA`: outra decisão (ou um duplo clique) venceu; a tela recarrega e mostra o estado final. */
export class DecisaoJaRegistradaError extends Error {
  constructor(mensagem = "Esta aprovação já foi respondida.") {
    super(mensagem);
    this.name = "DecisaoJaRegistradaError";
  }
}

/** 409 `SEM_ETAPA_ANTERIOR`: a etapa é a primeira do workflow, não há para onde devolver. */
export class SemEtapaAnteriorError extends Error {
  constructor(mensagem = "Não é possível solicitar ajustes nesta etapa.") {
    super(mensagem);
    this.name = "SemEtapaAnteriorError";
  }
}

type Fetcher = typeof fetch;

async function chamar(acao: "consultar" | "decisao" | "artefato" | "logo", corpo: Record<string, unknown>, fetcher: Fetcher): Promise<Response> {
  return fetcher(`${BASE_BFF}/${acao}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corpo),
    cache: "no-store",
    credentials: "omit", // nenhum cookie (nem tf_session) sai deste cliente
    referrerPolicy: "no-referrer",
  });
}

function mensagemDeErro(dados: unknown, padrao: string): string {
  const detalhe = (dados as { detail?: unknown } | null)?.detail;
  if (typeof detalhe === "string") return detalhe;
  if (Array.isArray(detalhe)) {
    const mensagens = detalhe
      .map((item) => (item && typeof item === "object" ? String((item as { mensagem?: unknown }).mensagem ?? "") : ""))
      .filter(Boolean);
    if (mensagens.length > 0) return mensagens.join(" ");
  }
  if (detalhe && typeof detalhe === "object" && typeof (detalhe as { message?: unknown }).message === "string") {
    return (detalhe as { message: string }).message;
  }
  return padrao;
}

export async function consultarAprovacao(slug: string, token: string, fetcher: Fetcher = fetch): Promise<AprovacaoPublica> {
  const resposta = await chamar("consultar", { slug, token }, fetcher);
  if (resposta.status === 404) throw new LinkIndisponivelError();
  if (!resposta.ok) throw new Error("Não foi possível carregar a aprovação agora. Tente novamente em instantes.");
  return (await resposta.json()) as AprovacaoPublica;
}

export async function decidirAprovacao(
  slug: string,
  token: string,
  entrada: DecisaoPublicaEntrada,
  fetcher: Fetcher = fetch,
): Promise<{ estado: "aprovada" | "ajustes_solicitados"; decididaEm: string }> {
  const resposta = await chamar("decisao", { slug, token, ...entrada }, fetcher);
  const dados = await resposta.json().catch(() => null);
  if (resposta.ok) return dados as { estado: "aprovada" | "ajustes_solicitados"; decididaEm: string };
  if (resposta.status === 404) throw new LinkIndisponivelError();
  const codigo = (dados as { detail?: { code?: string } } | null)?.detail?.code;
  if (resposta.status === 409 && codigo === "APROVACAO_JA_DECIDIDA") throw new DecisaoJaRegistradaError();
  if (resposta.status === 409 && codigo === "SEM_ETAPA_ANTERIOR") throw new SemEtapaAnteriorError(mensagemDeErro(dados, "Não é possível solicitar ajustes nesta etapa."));
  throw new Error(mensagemDeErro(dados, "Não foi possível enviar sua resposta agora. Tente novamente em instantes."));
}

/** Bytes do artefato `ordem` (imagem ou PDF) para exibir/baixar via `Blob` — nunca por URL com token. */
export async function baixarArtefato(slug: string, token: string, ordem: number, fetcher: Fetcher = fetch): Promise<Blob> {
  const resposta = await chamar("artefato", { slug, token, ordem }, fetcher);
  if (resposta.status === 404) throw new LinkIndisponivelError();
  if (!resposta.ok) throw new Error("Não foi possível carregar o arquivo agora.");
  return resposta.blob();
}

/** Logo da empresa DONA do link; `null` se não houver logo (o portal usa a marca padrão). */
export async function baixarLogo(slug: string, token: string, fetcher: Fetcher = fetch): Promise<Blob | null> {
  try {
    const resposta = await chamar("logo", { slug, token }, fetcher);
    return resposta.ok ? await resposta.blob() : null;
  } catch {
    return null;
  }
}
