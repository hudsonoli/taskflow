import type {
  AuthCurrentUser,
  AuthPerfilBase,
  AuthUsuarioStatus,
} from "../../types/auth";

const MAX_RETURN_TO_DECODINGS = 2;
const ASCII_CONTROL_CHARACTER = /[\u0000-\u001f\u007f]/;
const PERCENT_ENCODED_BYTE = /%[0-9a-f]{2}/i;
const JSON_CONTENT_TYPE = "application/json";

const PERFIS_BASE: ReadonlySet<AuthPerfilBase> = new Set([
  "admin",
  "gestor",
  "operador",
]);
const USUARIO_STATUSES: ReadonlySet<AuthUsuarioStatus> = new Set([
  "ativo",
  "inativo",
  "bloqueado",
  "arquivado",
]);
const AUTH_CURRENT_USER_FIELDS = new Set([
  "usuarioId",
  "empresaId",
  "nome",
  "perfilBase",
  "acessoSistema",
  "status",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isAuthCurrentUser(value: unknown): value is AuthCurrentUser {
  if (!isRecord(value)) {
    return false;
  }

  const fields = Object.keys(value);
  return (
    fields.length === AUTH_CURRENT_USER_FIELDS.size &&
    fields.every((field) => AUTH_CURRENT_USER_FIELDS.has(field)) &&
    typeof value.usuarioId === "string" &&
    typeof value.empresaId === "string" &&
    typeof value.nome === "string" &&
    typeof value.perfilBase === "string" &&
    PERFIS_BASE.has(value.perfilBase as AuthPerfilBase) &&
    typeof value.acessoSistema === "boolean" &&
    typeof value.status === "string" &&
    USUARIO_STATUSES.has(value.status as AuthUsuarioStatus)
  );
}

export function getSafeReturnTo(value: string | null): string {
  if (!value || value !== value.trim() || !value.startsWith("/")) {
    return "/";
  }

  let canonicalValue = value;
  try {
    for (let decoding = 0; decoding < MAX_RETURN_TO_DECODINGS; decoding += 1) {
      const decodedValue = decodeURIComponent(canonicalValue);
      if (decodedValue === canonicalValue) {
        break;
      }
      canonicalValue = decodedValue;
    }
  } catch (error) {
    if (error instanceof URIError) {
      return "/";
    }
    throw error;
  }

  if (
    !canonicalValue.startsWith("/") ||
    canonicalValue.startsWith("//") ||
    canonicalValue.includes("\\") ||
    ASCII_CONTROL_CHARACTER.test(canonicalValue) ||
    PERCENT_ENCODED_BYTE.test(canonicalValue)
  ) {
    return "/";
  }

  return value;
}

export function createLoginRequestBody(email: string, senha: string) {
  return { email: email.trim(), senha };
}

type CompleteLoginActions = {
  refresh: () => Promise<void>;
  redirect: (path: string) => void;
};

export async function completeLogin(
  response: Response,
  returnTo: string | null,
  actions: CompleteLoginActions,
): Promise<boolean> {
  const contentType = response.headers
    .get("content-type")
    ?.split(";", 1)[0]
    .trim()
    .toLowerCase();

  if (response.status !== 200 || contentType !== JSON_CONTENT_TYPE) {
    return false;
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return false;
  }

  if (!isAuthCurrentUser(body)) {
    return false;
  }

  await actions.refresh();
  actions.redirect(getSafeReturnTo(returnTo));
  return true;
}
