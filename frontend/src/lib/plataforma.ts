// Administração da Plataforma — lógica pura (sem React, sem fetch): validação AMIGÁVEL de slug/código (o backend e o
// banco continuam sendo a barreira), rótulos e leitura de mensagens de erro da API. Testável com `node --test`.

import type { PlataformaEmpresaStatus } from "../types/plataforma.ts";

export const SLUG_RESERVADOS = ["plataforma", "api", "login", "logout", "admin", "suporte"] as const;
export const SLUG_MIN = 3;
export const SLUG_MAX = 40;
const FORMATO_SLUG = /^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$/;

/** Mensagem de erro do slug digitado, ou `null` se válido. Espelha `app/core/empresa_slug.py`. */
export function erroDoSlug(valor: string): string | null {
  const slug = valor.trim().toLowerCase();
  if (!slug) return "Informe o slug.";
  if (slug.length < SLUG_MIN || slug.length > SLUG_MAX) return `O slug deve ter entre ${SLUG_MIN} e ${SLUG_MAX} caracteres.`;
  if (!FORMATO_SLUG.test(slug)) return "Use só letras minúsculas, números e hífen, sem hífen no começo ou no fim.";
  if ((SLUG_RESERVADOS as readonly string[]).includes(slug)) return `"${slug}" é um nome reservado.`;
  return null;
}

/** Sugestão de slug a partir de um nome/código (sem acentos, minúsculas, hífens). Apenas sugestão: o servidor decide. */
export function sugerirSlug(texto: string): string {
  const base = texto
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, SLUG_MAX)
    .replace(/-+$/g, "");
  return base;
}

/** O código interno é o código de login (hoje maiúsculo): só letras, números, hífen e sublinhado. */
export function erroDoCodigoInterno(valor: string): string | null {
  const codigo = valor.trim();
  if (!codigo) return "Informe o código interno.";
  if (!/^[A-Za-z0-9_-]+$/.test(codigo)) return "O código aceita só letras, números, hífen e sublinhado.";
  return null;
}

export const STATUS_EMPRESA_ROTULO: Record<PlataformaEmpresaStatus, string> = {
  ativa: "Ativa",
  inativa: "Inativa",
  arquivada: "Arquivada",
};

/** Texto de erro de uma resposta da API: `detail` string, lista de validação (422) ou `message` do BFF. */
export function mensagemDeErroDaApi(dados: unknown, padrao: string): string {
  if (!dados || typeof dados !== "object") return padrao;
  const { detail, message } = dados as { detail?: unknown; message?: unknown };
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const primeiro = detail[0] as { msg?: unknown } | undefined;
    if (primeiro && typeof primeiro.msg === "string") return primeiro.msg.replace(/^Value error,\s*/i, "");
  }
  if (detail && typeof detail === "object" && typeof (detail as { message?: unknown }).message === "string") {
    return (detail as { message: string }).message;
  }
  if (typeof message === "string" && message) return message;
  return padrao;
}
