import type { UsuarioEditableValues } from "@/types/usuario-api";

type UsuarioUpdateChanges = Partial<UsuarioEditableValues>;

export function buildUsuarioUpdatePayload(
  original: UsuarioEditableValues,
  current: UsuarioEditableValues,
): UsuarioUpdateChanges {
  const payload: UsuarioUpdateChanges = {};

  if (current.codigoInterno !== original.codigoInterno) {
    payload.codigoInterno = current.codigoInterno;
  }
  if (current.nome !== original.nome) {
    payload.nome = current.nome;
  }
  if (current.email !== original.email) {
    payload.email = current.email;
  }
  if (current.perfilBase !== original.perfilBase) {
    payload.perfilBase = current.perfilBase;
  }
  if (current.acessoSistema !== original.acessoSistema) {
    payload.acessoSistema = current.acessoSistema;
  }

  return payload;
}
