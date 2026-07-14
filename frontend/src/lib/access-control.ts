/**
 * Camada de autorização do TaskFloww V2 — nome definitivo (não "auth-mock")
 * para evitar renomeações quando autenticação/RBAC real forem implementados.
 * Nesta fase, PerfilAcesso vem de dado simulado (lib/conta-mock.ts,
 * currentUser.perfil) — não há sessão, token ou verificação de servidor.
 * O backend deverá aplicar a mesma checagem ao servir/gravar estes campos:
 * ocultar no frontend não substitui autorização real (ver
 * docs/design-system/entity-component-api.md, seção "Guia Administrativa").
 *
 * Hierarquia oficial (não é RBAC completo — apenas os perfis nomeados,
 * usados hoje só para a guia Administrativa de Clientes):
 */
export type PerfilAcesso =
  | "Owner"
  | "Diretoria"
  | "Gestor"
  | "Financeiro"
  | "Operador"
  | "Cliente";

const ADMINISTRATIVE_ROLES: readonly PerfilAcesso[] = [
  "Owner",
  "Diretoria",
  "Gestor",
  "Financeiro",
];

/**
 * Acesso à guia Administrativa (Fee Mensal, dados bancários e, no futuro,
 * Salário de Usuários). Only-frontend: apenas decide o que renderizar.
 */
export function hasAdministrativeAccess(perfil: PerfilAcesso): boolean {
  return ADMINISTRATIVE_ROLES.includes(perfil);
}
