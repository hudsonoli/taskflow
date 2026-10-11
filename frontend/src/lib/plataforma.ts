// Administração da Plataforma — lógica pura (sem React, sem fetch): validação AMIGÁVEL de slug/código (o backend e o
// banco continuam sendo a barreira), rótulos e leitura de mensagens de erro da API. Testável com `node --test`.

import { hexValido } from "./branding-tokens.ts";
import type { MotivoConviteNaoEnviado, PlataformaConvite, PlataformaEmpresaStatus, PlataformaOnboardingCreate } from "../types/plataforma.ts";

export const SLUG_RESERVADOS = ["plataforma", "gestao", "api", "e", "aprovacao", "login", "logout", "admin", "suporte"] as const;
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

/**
 * Separa os usuários da empresa em Gestores (`perfilBase === "gestor"`) e demais. Gestor NÃO é um cadastro à parte: é o
 * próprio usuário com esse perfil, e a empresa pode ter vários. Admin legado e Usuário ficam em "demais" (nunca contam como
 * Gestor). A conta de sistema nunca chega aqui (a API a omite). Ordem estável por nome.
 */
export function separarGestores<T extends { perfilBase: string; nome: string }>(usuarios: readonly T[]): { gestores: T[]; demais: T[] } {
  const porNome = (a: T, b: T) => a.nome.localeCompare(b.nome, "pt-BR");
  return {
    gestores: usuarios.filter((u) => u.perfilBase === "gestor").sort(porNome),
    demais: usuarios.filter((u) => u.perfilBase !== "gestor").sort(porNome),
  };
}

// ── Onboarding de nova empresa (Fase 10B) ─────────────────────────────────────────────────────────────────

export const EMAIL_SIMPLES = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;

export type RascunhoOnboarding = {
  nome: string;
  nomeFantasia: string;
  documento: string;
  codigoInterno: string;
  slug: string;
  corPrimaria: string;
  corSecundaria: string;
  tema: "" | "claro" | "escuro";
  gestorNome: string;
  gestorEmail: string;
};

export const ONBOARDING_VAZIO: RascunhoOnboarding = {
  nome: "",
  nomeFantasia: "",
  documento: "",
  codigoInterno: "",
  slug: "",
  corPrimaria: "",
  corSecundaria: "",
  tema: "",
  gestorNome: "",
  gestorEmail: "",
};

export type ErrosOnboarding = Partial<Record<keyof RascunhoOnboarding, string>>;

export function erroDoNomeDoGestor(valor: string): string | null {
  const nome = valor.trim().replace(/\s+/g, " ");
  if (!nome) return "Informe o nome do Gestor.";
  if (nome.length > 255) return "O nome pode ter no máximo 255 caracteres.";
  if (/[<>]/.test(nome)) return "O nome não pode conter marcação HTML.";
  return null;
}

export function erroDoEmailDoGestor(valor: string): string | null {
  const email = valor.trim();
  if (!email) return "Informe o e-mail do Gestor.";
  if (email.length > 255 || !EMAIL_SIMPLES.test(email)) return "Informe um e-mail válido.";
  return null;
}

/** Cor opcional da identidade visual: vazia vale (fica o padrão); preenchida precisa ser #RRGGBB. O servidor revalida (contraste, normalização). */
export function erroDaCorOpcional(valor: string): string | null {
  const cor = valor.trim();
  if (!cor) return null;
  return hexValido(cor) ? null : "Use uma cor no formato #RRGGBB.";
}

/** Validação AMIGÁVEL do formulário (o backend continua sendo a barreira: formato, reservados e unicidade do slug, e-mail, duplicidades). */
export function validarOnboarding(r: RascunhoOnboarding): ErrosOnboarding {
  const erros: ErrosOnboarding = {};
  if (!r.nome.trim()) erros.nome = "Informe o nome da empresa.";
  const codigo = erroDoCodigoInterno(r.codigoInterno);
  if (codigo) erros.codigoInterno = codigo;
  // slug vazio → o servidor deriva do código; preenchido, é validado como no backend (formato e reservados)
  if (r.slug.trim()) {
    const slug = erroDoSlug(r.slug);
    if (slug) erros.slug = slug;
  }
  const primaria = erroDaCorOpcional(r.corPrimaria);
  if (primaria) erros.corPrimaria = primaria;
  const secundaria = erroDaCorOpcional(r.corSecundaria);
  if (secundaria) erros.corSecundaria = secundaria;
  const nomeGestor = erroDoNomeDoGestor(r.gestorNome);
  if (nomeGestor) erros.gestorNome = nomeGestor;
  const emailGestor = erroDoEmailDoGestor(r.gestorEmail);
  if (emailGestor) erros.gestorEmail = emailGestor;
  return erros;
}

/** Corpo do onboarding: só campos REAIS do modelo; o status (ativa) e o perfil (gestor) são decididos pelo servidor, nunca enviados. */
export function payloadDoOnboarding(r: RascunhoOnboarding): PlataformaOnboardingCreate {
  return {
    empresa: {
      nome: r.nome.trim(),
      nomeFantasia: r.nomeFantasia.trim() || null,
      documento: r.documento.trim() || null,
      codigoInterno: r.codigoInterno.trim(),
      slug: r.slug.trim().toLowerCase() || null,
    },
    gestor: { nome: r.gestorNome.trim().replace(/\s+/g, " "), email: r.gestorEmail.trim() },
  };
}

/** Há identidade visual a aplicar DEPOIS de criar (cores/tema)? O logo é tratado à parte (arquivo). */
export function brandingDoRascunho(r: RascunhoOnboarding): { corPrimaria?: string; corSecundaria?: string; tema?: "claro" | "escuro" } | null {
  const payload: { corPrimaria?: string; corSecundaria?: string; tema?: "claro" | "escuro" } = {};
  if (r.corPrimaria.trim()) payload.corPrimaria = r.corPrimaria.trim();
  if (r.corSecundaria.trim()) payload.corSecundaria = r.corSecundaria.trim();
  if (r.tema) payload.tema = r.tema;
  return Object.keys(payload).length > 0 ? payload : null;
}

/** Endereço de login da empresa: `<origem>/e/<slug>/login`. Sem token; o slug é o do SERVIDOR, nunca um valor fixo. */
export function urlDeAcessoDaEmpresa(origem: string, slug: string): string {
  return `${origem.replace(/\/+$/, "")}/e/${slug}/login`;
}

/** O servidor devolve link relativo quando não conhece a URL pública: a Gestão completa com a própria origem (a mesma do produto). */
export function absolutizarLink(origem: string, link: string): string {
  return /^https?:\/\//i.test(link) ? link : `${origem.replace(/\/+$/, "")}${link.startsWith("/") ? "" : "/"}${link}`;
}

const DETALHE_MOTIVO: Record<MotivoConviteNaoEnviado, string> = {
  email_nao_configurado: "A empresa ainda não tem e-mail (SMTP) configurado, então o convite não pôde ser enviado.",
  url_publica_ausente: "O endereço público do TaskFlow não está configurado no servidor, então o convite não pôde ser enviado.",
  falha_envio: "O servidor de e-mail não aceitou o envio do convite agora.",
};

/** Texto do estado do convite: enviado, ou "não enviado" com o motivo (nunca esconde a falha). */
export function descreverConvite(convite: Pick<PlataformaConvite, "enviado" | "motivo">): { titulo: string; detalhe: string; tom: "green" | "amber" } {
  if (convite.enviado) {
    return { titulo: "Convite enviado", detalhe: "O Gestor recebeu um e-mail com o link para definir a própria senha.", tom: "green" };
  }
  return {
    titulo: "Convite não enviado",
    detalhe: `${convite.motivo ? DETALHE_MOTIVO[convite.motivo] : "O convite não pôde ser enviado."} A empresa e o Gestor foram criados normalmente.`,
    tom: "amber",
  };
}
