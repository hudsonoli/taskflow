import type { StatusUsuario } from "../../types/usuario-api";
import type { UsuarioStatusLabel } from "../../types/usuario-domain";

export const STATUS_LABELS: Record<StatusUsuario, UsuarioStatusLabel> = {
  ativo: "Ativo",
  inativo: "Inativo",
  bloqueado: "Bloqueado",
  arquivado: "Arquivado",
};
