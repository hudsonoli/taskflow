/**
 * Projeção mínima pra seleção operacional (Modelo de Campanha de Projeto) — só ativo, sem
 * descrição/ordem/status. Mesmo padrão de WorkflowModeloDiretorioItem (Fase 2G.1).
 *
 * Sem tipo `TipoTarefa`/`TipoTarefaFormDraft` completos ainda: nenhuma tela de cadastro
 * dedicada existe nesta fase (2G.2 cobre backend + diretório + integração no Projeto) — CRUD
 * completo fica para quando essa tela existir, evitando tipo morto sem consumidor.
 */
export type TipoTarefaDiretorioItem = {
  id: string;
  nome: string;
};
