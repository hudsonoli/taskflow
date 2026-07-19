import type { PerfilBase } from "../../types/usuario-api";
import type { UsuarioPerfilLabel } from "../../types/usuario-domain";

export const PERFIL_LABELS: Record<PerfilBase, UsuarioPerfilLabel> = {
  admin: "Administrador",
  gestor: "Gestor",
  operador: "Operador",
};
