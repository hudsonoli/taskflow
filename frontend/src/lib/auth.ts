import type { Usuario } from "@/types/usuario";
import { mapUsuarioReadToUsuario, type UsuarioReadApi } from "@/lib/api-backend";

// Helpers de cliente — só conversam com as rotas BFF (/api/auth/* e /api/backend/*), nunca
// leem ou guardam o token. O JWT fica inteiramente do lado do servidor, num cookie HttpOnly.

export type SessaoAtual = {
  usuarioId: string;
  empresaId: string;
  nome: string;
  perfilBase: "admin" | "gestor" | "operador";
  acessoSistema: boolean;
  status: "ativo" | "inativo" | "bloqueado" | "arquivado";
  mustChangePassword: boolean;
  /** preferência pessoal de tema; null = usar o padrão da empresa */
  temaPreferencia?: "claro" | "escuro" | "sistema" | null;
  /** slug PÚBLICO da empresa da sessão (contexto visual); nunca autoriza nada */
  empresaSlug?: string | null;
};

// `slug`: o da URL `/e/<slug>/login`. Sem slug, é o acesso legado `/login` (empresa padrão do servidor).
export async function login(email: string, senha: string, slug?: string): Promise<{ mustChangePassword: boolean }> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha, ...(slug ? { empresaSlug: slug } : {}) }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.message ?? "Não foi possível entrar");
  }
  return response.json();
}

// Login Google Workspace — mesmo contrato de `login()` (BFF trata o idToken, grava o mesmo
// cookie tf_session). `email` é o que o usuário digitou (login_hint), confirmado no backend
// contra o claim do token antes de qualquer vínculo — ver AuthService.login_google.
export async function loginGoogle(email: string, idToken: string, slug?: string): Promise<{ mustChangePassword: boolean }> {
  const response = await fetch("/api/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, idToken, ...(slug ? { empresaSlug: slug } : {}) }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.message ?? "Não foi possível entrar com Google");
  }
  return response.json();
}

// Recuperação de senha. O pedido NUNCA revela se a conta existe: sucesso é sempre a mesma mensagem.
// `empresaCodigo` é do servidor (BFF) — nunca enviado daqui.
export async function solicitarRedefinicaoSenha(email: string, slug?: string): Promise<string> {
  const response = await fetch("/api/auth/password-reset/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, ...(slug ? { empresaSlug: slug } : {}) }),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.message ?? "Não foi possível processar o pedido agora. Tente novamente em instantes.");
  }
  return data?.message as string;
}

/** Token de redefinição inexistente, expirado, já usado ou de outra empresa (o servidor nunca diz qual). */
export class LinkRedefinicaoInvalidoError extends Error {}

export async function confirmarRedefinicaoSenha(
  token: string,
  novaSenha: string,
  confirmacaoSenha: string,
  slug?: string,
): Promise<void> {
  const response = await fetch("/api/auth/password-reset/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, novaSenha, confirmacaoSenha, ...(slug ? { empresaSlug: slug } : {}) }),
  });
  if (response.ok) return;
  const data = await response.json().catch(() => null);
  if (response.status === 400) {
    throw new LinkRedefinicaoInvalidoError(data?.message ?? "Este link é inválido ou expirou.");
  }
  throw new Error(data?.message ?? "Não foi possível redefinir a senha agora. Tente novamente em instantes.");
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" });
}

export async function fetchSessao(): Promise<SessaoAtual | null> {
  const response = await fetch("/api/auth/session", { cache: "no-store" });
  if (!response.ok) return null;
  return response.json();
}

export async function alterarSenhaInicial(senhaAtual: string, novaSenha: string, confirmacaoSenha: string): Promise<void> {
  const response = await fetch("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ senhaAtual, novaSenha, confirmacaoSenha }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.message ?? data?.detail ?? "Não foi possível trocar a senha");
  }
}

export async function fetchUsuarioAtualCompleto(): Promise<Usuario | null> {
  const response = await fetch("/api/backend/usuarios/me", { cache: "no-store" });
  if (!response.ok) return null;
  const data: UsuarioReadApi = await response.json();
  return mapUsuarioReadToUsuario(data);
}
