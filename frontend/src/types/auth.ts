export type AuthPerfilBase = "admin" | "gestor" | "operador";

export type AuthUsuarioStatus =
  | "ativo"
  | "inativo"
  | "bloqueado"
  | "arquivado";

export type AuthLoginRequest = {
  empresaCodigo: string;
  email: string;
  senha: string;
};

export type AuthLoginBackendResponse = {
  accessToken: string;
  tokenType: "bearer";
};

export type AuthCurrentUser = {
  usuarioId: string;
  empresaId: string;
  nome: string;
  perfilBase: AuthPerfilBase;
  acessoSistema: boolean;
  status: AuthUsuarioStatus;
};

export type AuthChangePasswordRequest = {
  senhaAtual: string;
  novaSenha: string;
  confirmacaoSenha: string;
};

export type AuthErrorCode =
  | "INVALID_REQUEST"
  | "UNSUPPORTED_MEDIA_TYPE"
  | "INVALID_ORIGIN"
  | "INVALID_CREDENTIALS"
  | "UNAUTHENTICATED"
  | "FORBIDDEN"
  | "VALIDATION_ERROR"
  | "RATE_LIMITED"
  | "CONFIGURATION_ERROR"
  | "INTERNAL_ERROR"
  | "BACKEND_UNAVAILABLE"
  | "BACKEND_TIMEOUT"
  | "INVALID_BACKEND_RESPONSE";

export type AuthErrorResponse = {
  error: {
    code: AuthErrorCode;
    message: string;
  };
};
