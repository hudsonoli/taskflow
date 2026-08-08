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
};

export async function login(email: string, senha: string): Promise<{ mustChangePassword: boolean }> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.message ?? "Não foi possível entrar");
  }
  return response.json();
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
