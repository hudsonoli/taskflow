/**
 * Regra única de apresentação das entidades numeradas do TaskFlowW.
 *
 * Nenhum componente deve montar o rótulo à mão, fazer substring de `codigoReferencia`,
 * usar o `id` técnico como label ou exibir `#sequencial` onde a entidade não usa.
 *
 * Separação (ver docs/padrao-migracao-dominio.md):
 * - `id` (UUID) → relacionamento e rotas, nunca exibido;
 * - `codigoReferencia` (D26000001) → busca precisa, importação/exportação e integrações;
 * - `sequencialReferencia` → o número que aparece no rótulo, quando a entidade o exibe.
 */

/** Entidades que exibem SOMENTE o nome, sem número. */
const ENTIDADES_SEM_NUMERO_VISIVEL = new Set(["departamento", "equipe"]);

export type EntidadeReferenciavel =
  | "departamento"
  | "equipe"
  | "usuario"
  | "cliente"
  | "fornecedor"
  | "projeto"
  | "tarefa";

export function formatarReferenciaVisual({
  entidade,
  sequencialReferencia,
  nome,
}: {
  entidade: EntidadeReferenciavel;
  sequencialReferencia?: number | null;
  nome: string;
}): string {
  if (ENTIDADES_SEM_NUMERO_VISIVEL.has(entidade)) return nome;
  if (sequencialReferencia == null) return nome;
  // Sem zeros à esquerda — o número vem inteiro da API, não de substring do código.
  return `#${sequencialReferencia}-${nome}`;
}
