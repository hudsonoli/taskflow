// Cliente da Administração da Plataforma — só conversa com o BFF (`/api/plataforma/*`), nunca com o FastAPI, e nunca
// vê um token: a sessão de plataforma fica no cookie HttpOnly `tf_platform` (escopo de caminho do BFF).

import { normalizarBranding } from "@/lib/branding";
import { mensagemDeErroDaApi } from "@/lib/plataforma";
import type { Branding, PersonalizacaoUpdatePayload } from "@/types/personalizacao";
import type {
  PlataformaEmpresa,
  PlataformaEmpresaCreate,
  PlataformaEmpresaUpdate,
  PlataformaGestorCreate,
  PlataformaGestorCriado,
  PlataformaDashboard,
  PlataformaMe,
  PlataformaUsuario,
} from "@/types/plataforma";

const BASE = "/api/plataforma";

/** O usuário não é (mais) Administrador da Plataforma ou a sessão de plataforma não pôde ser aberta. */
export class PlataformaAcessoNegadoError extends Error {
  constructor(message = "Acesso restrito à Administração da Plataforma.") {
    super(message);
    this.name = "PlataformaAcessoNegadoError";
  }
}

/** Pergunta ao backend (com a sessão tenant) se o usuário atual é Administrador da Plataforma. Falha → `false`. */
export async function consultarAcessoPlataforma(): Promise<boolean> {
  try {
    const resposta = await fetch(`${BASE}/acesso`, { cache: "no-store" });
    if (!resposta.ok) return false;
    const dados = await resposta.json().catch(() => null);
    return dados?.administradorPlataforma === true;
  } catch {
    return false;
  }
}

/** Troca a sessão tenant por uma sessão de plataforma curta (cookie HttpOnly). 403 → não é administrador. */
export async function abrirSessaoPlataforma(): Promise<void> {
  const resposta = await fetch(`${BASE}/sessao`, { method: "POST", cache: "no-store" });
  if (resposta.ok) return;
  throw new PlataformaAcessoNegadoError();
}

export async function encerrarSessaoPlataforma(): Promise<void> {
  await fetch(`${BASE}/sessao`, { method: "DELETE", cache: "no-store" }).catch(() => undefined);
}

async function enviar(caminho: string, init: RequestInit): Promise<Response> {
  const executar = () => fetch(`${BASE}${caminho}`, { ...init, cache: "no-store" });
  let resposta = await executar();
  // Sessão de plataforma ausente/expirada (cookie curto): reabre UMA vez a partir da sessão tenant e repete.
  // Se o usuário deixou de ser administrador, a reabertura falha (403) e nada mais é tentado.
  if (resposta.status === 401 || resposta.status === 403) {
    await abrirSessaoPlataforma();
    resposta = await executar();
    if (resposta.status === 401 || resposta.status === 403) throw new PlataformaAcessoNegadoError();
  }
  return resposta;
}

async function pedir<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const comCorpoJson = typeof init.body === "string";
  const resposta = await enviar(caminho, {
    ...init,
    headers: { ...(comCorpoJson ? { "Content-Type": "application/json" } : {}), ...(init.headers ?? {}) },
  });
  if (!resposta.ok) {
    const dados = await resposta.json().catch(() => null);
    throw new Error(mensagemDeErroDaApi(dados, `Erro ${resposta.status}`));
  }
  return (await resposta.json()) as T;
}

export const obterMePlataforma = () => pedir<PlataformaMe>("/me");

/** Métricas agregadas de adoção/uso por empresa (sem dados individuais nem conteúdo operacional). */
export const obterDashboardPlataforma = () => pedir<PlataformaDashboard>("/dashboard");

// ── Empresas ──────────────────────────────────────────────────────────────────────────────────────
export function listarEmpresasPlataforma(filtros: { status?: string; search?: string } = {}): Promise<PlataformaEmpresa[]> {
  const params = new URLSearchParams({ limit: "200" });
  if (filtros.status) params.set("status", filtros.status);
  if (filtros.search?.trim()) params.set("search", filtros.search.trim());
  return pedir<PlataformaEmpresa[]>(`/empresas?${params.toString()}`);
}

export const obterEmpresaPlataforma = (id: string) => pedir<PlataformaEmpresa>(`/empresas/${encodeURIComponent(id)}`);

export const criarEmpresaPlataforma = (dados: PlataformaEmpresaCreate) =>
  pedir<PlataformaEmpresa>("/empresas", { method: "POST", body: JSON.stringify(dados) });

export const atualizarEmpresaPlataforma = (id: string, dados: PlataformaEmpresaUpdate) =>
  pedir<PlataformaEmpresa>(`/empresas/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(dados) });

export const inativarEmpresaPlataforma = (id: string, motivoInativacao?: string) =>
  pedir<PlataformaEmpresa>(`/empresas/${encodeURIComponent(id)}/inativar`, {
    method: "POST",
    body: JSON.stringify(motivoInativacao?.trim() ? { motivoInativacao: motivoInativacao.trim() } : {}),
  });

export const reativarEmpresaPlataforma = (id: string) =>
  pedir<PlataformaEmpresa>(`/empresas/${encodeURIComponent(id)}/reativar`, { method: "POST" });

// ── Branding de uma empresa (mesmo contrato e mesmas validações do tenant) ────────────────────────
export async function obterBrandingEmpresa(id: string): Promise<Branding> {
  return normalizarBranding(await pedir<unknown>(`/empresas/${encodeURIComponent(id)}/personalizacao`));
}

export async function atualizarBrandingEmpresa(id: string, payload: PersonalizacaoUpdatePayload): Promise<Branding> {
  return normalizarBranding(
    await pedir<unknown>(`/empresas/${encodeURIComponent(id)}/personalizacao`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  );
}

export async function restaurarBrandingEmpresa(id: string): Promise<Branding> {
  return normalizarBranding(await pedir<unknown>(`/empresas/${encodeURIComponent(id)}/personalizacao`, { method: "DELETE" }));
}

export async function removerLogoEmpresa(id: string): Promise<Branding> {
  return normalizarBranding(await pedir<unknown>(`/empresas/${encodeURIComponent(id)}/personalizacao/logo`, { method: "DELETE" }));
}

// Upload multipart — o `Content-Type` com o boundary é do próprio navegador (não passa por `pedir`, que assume JSON).
export async function enviarLogoEmpresa(id: string, arquivo: File): Promise<Branding> {
  const formData = new FormData();
  formData.append("arquivo", arquivo);
  const resposta = await enviar(`/empresas/${encodeURIComponent(id)}/personalizacao/logo`, { method: "POST", body: formData });
  if (!resposta.ok) {
    const dados = await resposta.json().catch(() => null);
    throw new Error(mensagemDeErroDaApi(dados, `Erro ${resposta.status}`));
  }
  return normalizarBranding(await resposta.json());
}

/** URL do logo de uma empresa para `<img>` (versionada: cache imutável e troca instantânea). */
export function urlLogoEmpresa(id: string, versao: string | null): string {
  return `${BASE}/empresas/${encodeURIComponent(id)}/personalizacao/logo${versao ? `?v=${encodeURIComponent(versao)}` : ""}`;
}

// ── Usuários e primeiro Gestor ────────────────────────────────────────────────────────────────────
export const listarUsuariosEmpresa = (id: string) =>
  pedir<PlataformaUsuario[]>(`/empresas/${encodeURIComponent(id)}/usuarios?limit=200`);

/** A `senhaTemporaria` existe SÓ nesta resposta: quem chama não deve guardá-la além do modal de entrega. */
export const criarGestorEmpresa = (id: string, dados: PlataformaGestorCreate) =>
  pedir<PlataformaGestorCriado>(`/empresas/${encodeURIComponent(id)}/gestores`, {
    method: "POST",
    body: JSON.stringify(dados),
  });

/** Usuários da PRÓPRIA empresa que podem ser promovidos a Gestor (só elegíveis; o servidor é quem decide). */
export const listarCandidatosGestor = (id: string) => pedir<PlataformaUsuario[]>(`/empresas/${encodeURIComponent(id)}/candidatos-gestor`);

/** Promove um Usuário existente da empresa a Gestor (mesmo cadastro e mesma senha; nada é gerado). */
export const promoverGestorEmpresa = (id: string, usuarioId: string) =>
  pedir<PlataformaUsuario>(`/empresas/${encodeURIComponent(id)}/usuarios/${encodeURIComponent(usuarioId)}/promover-gestor`, {
    method: "POST",
  });
