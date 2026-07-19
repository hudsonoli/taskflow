import type {
  AuthPerfilBase,
  AuthUsuarioStatus,
} from "./auth";

export type PerfilBase = AuthPerfilBase;
export type StatusUsuario = AuthUsuarioStatus;

export type UsuarioApiResponse = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  nome: string;
  email: string;
  perfilBase: PerfilBase;
  acessoSistema: boolean;
  status: StatusUsuario;
  createdAt: string;
  updatedAt: string;
  inativadoAt: string | null;
  inativadoPorUsuarioId: string | null;
  motivoInativacao: string | null;
};

export type UsuarioListFilters = {
  status?: StatusUsuario;
  perfilBase?: PerfilBase;
  search?: string;
  limit?: number;
  offset?: number;
};

export type UsuarioErrorCode =
  | "INVALID_REQUEST"
  | "UNAUTHENTICATED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "VALIDATION_ERROR"
  | "RATE_LIMITED"
  | "CONFIGURATION_ERROR"
  | "INVALID_BACKEND_RESPONSE"
  | "BACKEND_UNAVAILABLE"
  | "BACKEND_TIMEOUT"
  | "INTERNAL_ERROR";

export type UsuarioErrorResponse = {
  error: {
    code: UsuarioErrorCode;
    message: string;
  };
};
