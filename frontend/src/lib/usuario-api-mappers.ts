import type {
  PerfilBase,
  StatusUsuario,
  UsuarioApiResponse,
} from "../types/usuario-api";
import type {
  Usuario,
  UsuarioDetailResult,
  UsuarioListResult,
} from "../types/usuario-domain";
import { PERFIL_LABELS } from "./domain/perfil-labels";
import { STATUS_LABELS } from "./domain/status-labels";

export function isPerfilBase(value: unknown): value is PerfilBase {
  return value === "admin" || value === "gestor" || value === "operador";
}

export function isStatusUsuario(value: unknown): value is StatusUsuario {
  return (
    value === "ativo" ||
    value === "inativo" ||
    value === "bloqueado" ||
    value === "arquivado"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isRequiredString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function parseUsuarioApiResponse(value: unknown): UsuarioApiResponse {
  if (
    !isRecord(value) ||
    !isRequiredString(value.id) ||
    !isRequiredString(value.empresaId) ||
    !isRequiredString(value.codigoInterno) ||
    !isRequiredString(value.nome) ||
    !isRequiredString(value.email) ||
    !isPerfilBase(value.perfilBase) ||
    typeof value.acessoSistema !== "boolean" ||
    !isStatusUsuario(value.status) ||
    !isRequiredString(value.createdAt) ||
    !isRequiredString(value.updatedAt) ||
    !isNullableString(value.inativadoAt) ||
    !isNullableString(value.inativadoPorUsuarioId) ||
    !isNullableString(value.motivoInativacao)
  ) {
    throw new TypeError("Contrato de usuário inválido");
  }

  return {
    id: value.id,
    empresaId: value.empresaId,
    codigoInterno: value.codigoInterno,
    nome: value.nome,
    email: value.email,
    perfilBase: value.perfilBase,
    acessoSistema: value.acessoSistema,
    status: value.status,
    createdAt: value.createdAt,
    updatedAt: value.updatedAt,
    inativadoAt: value.inativadoAt,
    inativadoPorUsuarioId: value.inativadoPorUsuarioId,
    motivoInativacao: value.motivoInativacao,
  };
}

export function mapUsuarioApiResponseToDomain(
  value: unknown,
  expectedEmpresaId: string,
): Usuario {
  const response = parseUsuarioApiResponse(value);
  if (response.empresaId !== expectedEmpresaId) {
    throw new TypeError("Empresa divergente na resposta de usuário");
  }

  return {
    id: response.id,
    codigoInterno: response.codigoInterno,
    nome: response.nome,
    email: response.email,
    perfilBase: response.perfilBase,
    perfilLabel: PERFIL_LABELS[response.perfilBase],
    acessoSistema: response.acessoSistema,
    status: response.status,
    statusLabel: STATUS_LABELS[response.status],
    createdAt: response.createdAt,
    updatedAt: response.updatedAt,
    inativadoAt: response.inativadoAt,
    inativadoPorUsuarioId: response.inativadoPorUsuarioId,
    motivoInativacao: response.motivoInativacao,
  };
}

export function mapUsuarioApiListToResult(
  value: unknown,
  expectedEmpresaId: string,
): UsuarioListResult {
  if (!Array.isArray(value)) {
    throw new TypeError("Contrato de lista de usuários inválido");
  }
  return {
    items: value.map((item) =>
      mapUsuarioApiResponseToDomain(item, expectedEmpresaId),
    ),
  };
}

function isUsuarioDomain(value: unknown): value is Usuario {
  return (
    isRecord(value) &&
    isRequiredString(value.id) &&
    isRequiredString(value.codigoInterno) &&
    isRequiredString(value.nome) &&
    isRequiredString(value.email) &&
    isPerfilBase(value.perfilBase) &&
    value.perfilLabel === PERFIL_LABELS[value.perfilBase] &&
    typeof value.acessoSistema === "boolean" &&
    isStatusUsuario(value.status) &&
    value.statusLabel === STATUS_LABELS[value.status] &&
    isRequiredString(value.createdAt) &&
    isRequiredString(value.updatedAt) &&
    isNullableString(value.inativadoAt) &&
    isNullableString(value.inativadoPorUsuarioId) &&
    isNullableString(value.motivoInativacao) &&
    !("empresaId" in value)
  );
}

export function parseUsuarioListResult(value: unknown): UsuarioListResult {
  if (
    !isRecord(value) ||
    !Array.isArray(value.items) ||
    !value.items.every(isUsuarioDomain)
  ) {
    throw new TypeError("Contrato BFF de lista de usuários inválido");
  }
  return { items: value.items };
}

export function parseUsuarioDetailResult(value: unknown): UsuarioDetailResult {
  if (!isRecord(value) || !isUsuarioDomain(value.data)) {
    throw new TypeError("Contrato BFF de detalhe de usuário inválido");
  }
  return { data: value.data };
}
