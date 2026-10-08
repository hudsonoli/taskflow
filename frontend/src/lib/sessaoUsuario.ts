// Contexto do usuário logado — lógica PURA (sem React/fetch), testável com `node --test`.
//
// AUTORIDADE (perfil + permissões) e CONTEXTO OPERACIONAL (departamento atual, Head) são decididos pelo BACKEND a cada
// requisição, mas o `usuarioAtual` da interface é carregado uma vez. Se outra pessoa promove o usuário ou troca o departamento
// dele (Configurações → Usuários ou Administração da Plataforma) com a sessão aberta, a tela fica com o estado antigo —
// menus, "Meu Departamento", rótulos de departamento. `usuarioMudou` + a revalidação do AppDataProvider corrigem isso na fonte.

/** Campos de `Usuario` relevantes para decidir se o estado da interface ficou velho. */
export type UsuarioComparavel = {
  id: string;
  perfil: string;
  departamentoId: string;
  liderDepartamento?: boolean;
  ativo: boolean;
  updatedAt: string;
  permissoes?: string[];
};

/** `true` se algo que a interface usa para decidir acesso/contexto mudou. Pessoa diferente = mudou. Sem estado anterior = mudou. */
export function usuarioMudou(anterior: UsuarioComparavel | undefined, atual: UsuarioComparavel): boolean {
  if (!anterior || anterior.id !== atual.id) return true;
  if (
    anterior.perfil !== atual.perfil ||
    anterior.departamentoId !== atual.departamentoId ||
    Boolean(anterior.liderDepartamento) !== Boolean(atual.liderDepartamento) ||
    anterior.ativo !== atual.ativo ||
    anterior.updatedAt !== atual.updatedAt
  ) {
    return true;
  }
  // exceções individuais de permissão não passam por `updatedAt` do usuário
  const chave = (p?: string[]) => [...(p ?? [])].sort().join("|");
  return chave(anterior.permissoes) !== chave(atual.permissoes);
}

/** O contexto de DEPARTAMENTO/AUTORIDADE mudou (e não só um dado cadastral)? Decide se os diretórios em cache são descartados. */
export function contextoOperacionalMudou(anterior: UsuarioComparavel | undefined, atual: UsuarioComparavel): boolean {
  if (!anterior || anterior.id !== atual.id) return true;
  return (
    anterior.perfil !== atual.perfil ||
    anterior.departamentoId !== atual.departamentoId ||
    Boolean(anterior.liderDepartamento) !== Boolean(atual.liderDepartamento) ||
    anterior.ativo !== atual.ativo
  );
}

/** Intervalo mínimo entre duas revalidações (foco/visibilidade disparam em rajada) e período da revalidação periódica. */
export const REVALIDACAO_MIN_MS = 10_000;
export const REVALIDACAO_PERIODO_MS = 120_000;

/** Pode revalidar agora? (respeita o intervalo mínimo; `ultimo` = instante da última tentativa). */
export function podeRevalidar(ultimo: number, agora: number, minimo: number = REVALIDACAO_MIN_MS): boolean {
  return agora - ultimo >= minimo;
}

/**
 * "Meu Departamento": entre os departamentos dos quais a pessoa é Head, escolhe o do contexto ATUAL (o departamento em que
 * ela está hoje); sem ele, o primeiro. Evita que o dono formal de um departamento antigo "puxe" a tela para lá só por causa
 * da ordem da lista. Não move nem altera nenhum dado: é só a escolha do recorte exibido.
 */
export function escolherDepartamentoHead<T>(candidatos: readonly T[], ehDepartamentoAtual: (departamento: T) => boolean): T | undefined {
  return candidatos.find(ehDepartamentoAtual) ?? candidatos[0];
}
