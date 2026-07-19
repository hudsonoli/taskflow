import type {
  PerfilBase,
  StatusUsuario,
  UsuarioErrorResponse,
} from "./usuario-api";

export type UsuarioPerfilLabel = "Administrador" | "Gestor" | "Operador";
export type UsuarioStatusLabel =
  | "Ativo"
  | "Inativo"
  | "Bloqueado"
  | "Arquivado";

export type Usuario = {
  id: string;
  codigoInterno: string;
  nome: string;
  email: string;
  perfilBase: PerfilBase;
  perfilLabel: UsuarioPerfilLabel;
  acessoSistema: boolean;
  status: StatusUsuario;
  statusLabel: UsuarioStatusLabel;
  createdAt: string;
  updatedAt: string;
  inativadoAt: string | null;
  inativadoPorUsuarioId: string | null;
  motivoInativacao: string | null;
};

export type UsuarioListResult = {
  items: Usuario[];
};

export type UsuarioDetailResult = {
  data: Usuario;
};

export type UsuarioClientResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: UsuarioErrorResponse };
