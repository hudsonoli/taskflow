export type TipoTarefaStatus = "ativo" | "inativo" | "arquivado";

/**
 * Cadastro real (Fase 2G.9) — backend já existia desde a Fase 2G.2 (model/schema/service/
 * rotas/testes), só a tela administrativa estava pendente. Sem `codigoInterno`/
 * `codigoReferencia`: diferente de Workflow/Departamento/Cliente, Tipo de Tarefa não é
 * documento pesquisável nem tem importação legada prevista — é só um rótulo com identidade
 * por nome dentro da Empresa, igual a Categoria de Peça (ver model `TipoTarefa`).
 *
 * Sem os campos de auditoria de arquivamento (`arquivadoAt`/`motivoArquivamento`/
 * `restauradoAt`/...) — mesmo padrão de `Departamento`/`WorkflowModelo`: o schema da API os
 * expõe, mas nenhuma tela de cadastro os exibe ainda.
 */
export type TipoTarefa = {
  /** UUID técnico — usado em relações e rotas. Nunca exibido na interface. */
  id: string;
  empresaId: string;
  nome: string;
  descricao: string;
  ordem: number;
  status: TipoTarefaStatus;
  createdAt: string;
  updatedAt: string;
};

/** Campos que o formulário edita — a empresa é responsabilidade do backend. */
export type TipoTarefaFormDraft = {
  nome: string;
  descricao: string;
  ordem: number;
  status: Exclude<TipoTarefaStatus, "arquivado">;
};

/**
 * Projeção mínima pra seleção operacional (Modelo de Campanha de Projeto) — só ativo, sem
 * descrição/ordem/status. Mesmo padrão de WorkflowModeloDiretorioItem (Fase 2G.1).
 */
export type TipoTarefaDiretorioItem = {
  id: string;
  nome: string;
};
