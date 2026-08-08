import type {
  DepartamentoDiretorioItem,
  EquipeDiretorioItem,
  GrupoClienteDiretorioItem,
  UsuarioDiretorioItem,
} from "@/lib/api-backend";

/**
 * Camada central de compatibilidade entre UUID real e codigoInterno legado.
 *
 * Contexto: Usuário já é 100% real (UUID). Enquanto Demandas/Equipes/Departamentos/
 * Workflows continuarem mock, toda NOVA seleção de responsável feita nesses domínios grava
 * `usuario.codigoInterno` (nunca o UUID) — mas referências já existentes, criadas antes
 * desta migração, podem conter formatos antigos do mock (ids tipo "user-1"/"usuario-3").
 * Nenhum componente deve comparar `usuario.id === referencia` diretamente: sempre passar
 * pelas funções abaixo, que aceitam qualquer um dos dois formatos.
 */
export function correspondeUsuario(referencia: string, usuario: UsuarioDiretorioItem): boolean {
  return referencia === usuario.id || referencia === usuario.codigoInterno;
}

export function resolverUsuarioPorReferencia(
  referencia: string,
  diretorio: UsuarioDiretorioItem[],
): UsuarioDiretorioItem | undefined {
  return diretorio.find((usuario) => correspondeUsuario(referencia, usuario));
}

/**
 * Normaliza uma lista de referências (formato legado, UUID ou já codigoInterno) para
 * codigoInterno — usado antes de passar `values` a um picker genérico (MemberSelector),
 * cujas `options[].id` são sempre codigoInterno (ver política em
 * docs/padrao-arquivamento.md). Não resolvido = mantém o valor original (não descarta
 * silenciosamente uma referência histórica desconhecida).
 */
export function normalizarReferenciasParaCodigoInterno(
  referencias: string[],
  diretorio: UsuarioDiretorioItem[],
): string[] {
  return referencias.map((referencia) => resolverUsuarioPorReferencia(referencia, diretorio)?.codigoInterno ?? referencia);
}

/**
 * Mesmo padrão acima, pra Grupo de Cliente: `Cliente.tagIds` continua mock nesta entrega e
 * guarda o `id` mock antigo (ex. "grupo-grupo-bretas"), que o backend real preservou como
 * `codigoInterno` do grupo (ver backend/app/cli/seed_grupos_cliente.py). Nenhum componente
 * deve comparar `grupo.id === referencia` diretamente — sempre por aqui, que casa por `id`
 * OU `codigoInterno`.
 */
export function correspondeGrupoCliente(referencia: string, grupo: GrupoClienteDiretorioItem): boolean {
  return referencia === grupo.id || referencia === grupo.codigoInterno;
}

export function resolverGrupoClientePorReferencia(
  referencia: string,
  diretorio: GrupoClienteDiretorioItem[],
): GrupoClienteDiretorioItem | undefined {
  return diretorio.find((grupo) => correspondeGrupoCliente(referencia, grupo));
}

/**
 * Substitui `resolveGrupoClienteNomes` (antes em lib/grupos-cliente-mock.ts) — mesma
 * assinatura de uso (junta os nomes resolvidos, "-" se vazio), agora casando por id OU
 * codigoInterno e marcando grupos arquivados com o sufixo "(arquivado)".
 */
/**
 * Departamento: mesmo padrão, com um escopo menor desde o contract da Etapa D.
 *
 * `Usuario.departamentoId` **sempre** vem como UUID — é uma FK real em `usuarios`, o banco
 * não aceita outra coisa. Quem ainda carrega o id legado do mock (`dep-criacao`) são
 * `Demanda.departamentoResponsavelIds`, `Projeto` e `SLA`, que o backend preservou como
 * `codigoInterno` do Departamento. Por isso resolver por `id` OU `codigoInterno` continua
 * obrigatório aqui — some quando Projeto, Demanda e SLA migrarem.
 */
/**
 * Aceita qualquer objeto que carregue os dois identificadores — o item de diretório e o
 * `Departamento` completo têm formatos diferentes, mas a regra de comparação é uma só e
 * mora aqui. Nenhum componente deve reimplementá-la.
 */
type ReferenciavelPorCodigoInterno = { id: string; codigoInterno: string };

export function correspondeDepartamento(
  referencia: string,
  departamento: ReferenciavelPorCodigoInterno,
): boolean {
  return referencia === departamento.id || referencia === departamento.codigoInterno;
}

export function resolverDepartamentoPorReferencia(
  referencia: string,
  diretorio: DepartamentoDiretorioItem[],
): DepartamentoDiretorioItem | undefined {
  return diretorio.find((departamento) => correspondeDepartamento(referencia, departamento));
}

/**
 * Substitui `resolveDepartamentoNome` (antes em lib/departamentos-mock.ts). Departamento é
 * exibido **somente pelo nome** — sem `#sequencial`, sem código (ver lib/formatarReferencia.ts).
 */
export function resolverDepartamentoNome(
  referencia: string,
  diretorio: DepartamentoDiretorioItem[],
): string {
  if (!referencia) return "Sem departamento";
  const departamento = resolverDepartamentoPorReferencia(referencia, diretorio);
  if (!departamento) return referencia;
  return departamento.status === "arquivado" ? `${departamento.nome} (arquivado)` : departamento.nome;
}

/** Equipe: mesmo padrão — resolve por `id` OU `codigoInterno` legado (`equipe-1`). */
export function correspondeEquipe(referencia: string, equipe: EquipeDiretorioItem): boolean {
  return referencia === equipe.id || referencia === equipe.codigoInterno;
}

export function resolverEquipePorReferencia(
  referencia: string,
  diretorio: EquipeDiretorioItem[],
): EquipeDiretorioItem | undefined {
  return diretorio.find((equipe) => correspondeEquipe(referencia, equipe));
}

/** Equipe é exibida **somente pelo nome** (ver lib/formatarReferencia.ts). */
export function resolverEquipeNome(referencia: string, diretorio: EquipeDiretorioItem[]): string {
  if (!referencia) return "Sem equipe";
  const equipe = resolverEquipePorReferencia(referencia, diretorio);
  if (!equipe) return referencia;
  return equipe.status === "arquivado" ? `${equipe.nome} (arquivada)` : equipe.nome;
}

export function resolverGrupoClienteNomes(tagIds: string[], diretorio: GrupoClienteDiretorioItem[]): string {
  if (tagIds.length === 0) return "-";
  return tagIds
    .map((referencia) => {
      const grupo = resolverGrupoClientePorReferencia(referencia, diretorio);
      if (!grupo) return referencia;
      return grupo.status === "arquivado" ? `${grupo.nome} (arquivado)` : grupo.nome;
    })
    .join(", ");
}
