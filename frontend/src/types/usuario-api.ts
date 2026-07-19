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

export type UsuarioEditableValues = {
  codigoInterno: string;
  nome: string;
  email: string;
  perfilBase: PerfilBase;
  acessoSistema: boolean;
};

export type UsuarioCreatePayload = Omit<
  UsuarioEditableValues,
  "acessoSistema"
> & {
  acessoSistema?: boolean;
};

export type UsuarioUpdatePayload = Partial<UsuarioEditableValues>;

export type UsuarioErrorCode =
  | "INVALID_REQUEST"
  | "INVALID_ORIGIN"
  | "UNSUPPORTED_MEDIA_TYPE"
  | "UNAUTHENTICATED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
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
