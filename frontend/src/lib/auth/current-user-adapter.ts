import type { AuthCurrentUser, AuthPerfilBase } from "../../types/auth";

export type CurrentUserDisplay = {
  id: string;
  nome: string;
  perfilBase: AuthPerfilBase;
  perfilLabel: string;
  avatarUrl?: string | null;
};

const PERFIL_LABELS: Record<AuthPerfilBase, string> = {
  admin: "Administrador",
  gestor: "Gestor",
  operador: "Operador",
};

export function adaptCurrentUser(user: AuthCurrentUser): CurrentUserDisplay {
  return {
    id: user.usuarioId,
    nome: user.nome,
    perfilBase: user.perfilBase,
    perfilLabel: PERFIL_LABELS[user.perfilBase],
  };
}
