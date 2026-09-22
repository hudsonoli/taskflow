// Espelha PermissaoAdminItem do backend (app/schemas/usuario_permissao.py, Fase 2G.10C-C1) —
// módulo, label e o próprio agrupamento vêm sempre da API, nunca recalculados aqui.
export type PermissaoOverride = "conceder" | "negar";

export interface PermissaoAdminItem {
  permissao: string;
  modulo: string;
  label: string;
  herdado: boolean;
  override: PermissaoOverride | null;
  efetivo: boolean;
}

// Estado do Select por linha — "herdar" é só a ausência de override (nunca um valor
// persistido, ver docstring de UsuarioPermissaoService.remover_override no backend).
export type PermissaoEstadoUI = "herdar" | "conceder" | "negar";
