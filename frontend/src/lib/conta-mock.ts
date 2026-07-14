import type { PerfilAcesso } from "@/lib/access-control";

export type CurrentUser = {
  id: string;
  nome: string;
  email: string;
  telefone: string;
  celular: string;
  cargo: string;
  departamento: string;
  perfil: PerfilAcesso;
  avatarUrl: string | null;
  avatarThumbnail: string | null;
};

export const currentUser: CurrentUser = {
  id: "1",
  nome: "João Silva",
  email: "usuario@taskfloww.local",
  telefone: "(11) 3333-4444",
  celular: "(11) 99999-8888",
  cargo: "Administrador",
  departamento: "Operações",
  perfil: "Owner",
  avatarUrl: null,
  avatarThumbnail: null,
};

export function getCurrentUserInitials(nome: string) {
  const words = nome.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();

  return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
}

export function logout() {
  // TODO: integrar com autenticação.
  console.log("logout");
}
