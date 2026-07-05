export type EquipeMembro = {
  membroId: string;
  usuarioId: string;
  nome: string;
  papel: string;
};

export type HistoricoEquipe = {
  id: string;
  usuarioId: string;
  usuario: string;
  dataHora: string;
  dispositivo: string;
  ipOrigem: string;
  acao: string;
};

export type EquipeAcesso = {
  visualizarTodosProjetos: boolean;
  aprovarSla: boolean;
  gerenciarMembros: boolean;
  visivelParaClientes: boolean;
};

export type EquipeDraft = {
  equipeId: string;
  codigoInterno: string;
  empresaId: string;
  clienteId?: string;
  nome: string;
  sigla: string;
  descricao: string;
  departamentoId: string;
  responsavelId: string;
  ativa: boolean;
  membros: EquipeMembro[];
  acesso: EquipeAcesso;
  historico: HistoricoEquipe[];
};
