export type ProjetoStatus =
  | "planejamento"
  | "ativo"
  | "pausado"
  | "concluido"
  | "cancelado";

export type ProjetoPrioridade = "baixa" | "media" | "alta";

export type ProjetoEquipeMembro = {
  id: string;
  usuarioId: string;
  nome: string;
  funcao: string;
  departamentoId: string;
  departamentoNome: string;
};

export type ProjetoArquivo = {
  id: string;
  nome: string;
  tipo: string;
  tamanho: string;
  criadoEm: string;
  usuarioId: string;
  usuarioNome: string;
};

export type ProjetoHistoricoEvento = {
  id: string;
  usuarioId: string;
  usuario: string;
  acao: string;
  dataHora: string;
  ip: string;
  dispositivo: string;
};

export type ProjetoModeloCampanhaItem = {
  id: string;
  nomeDemanda: string;
  tipoTarefaId: string;
  tipoTarefaNome: string;
  briefingBase: string;
  prioridadePadrao: ProjetoPrioridade;
  workflowSugeridoId: string;
  workflowSugeridoNome: string;
  responsavelOuSetorSugeridoId: string;
  responsavelOuSetorSugeridoNome: string;
};

export type Projeto = {
  id: string;
  empresaId: string;
  agenciaId: string;
  clienteId: string;
  codigoInterno: string;
  nome: string;
  campanha: string;
  descricao: string;
  status: ProjetoStatus;
  prioridade: ProjetoPrioridade;
  responsavelId: string;
  responsavelNome: string;
  dataInicio: string;
  dataFimPrevista: string;
  createdAt: string;
  updatedAt: string;
  resumo: string;
  modeloCampanhaId?: string;
  modeloCampanha: ProjetoModeloCampanhaItem[];
  equipe: ProjetoEquipeMembro[];
  arquivos: ProjetoArquivo[];
  historico: ProjetoHistoricoEvento[];
};

export type ProjetoFormDraft = Pick<
  Projeto,
  | "nome"
  | "clienteId"
  | "campanha"
  | "responsavelId"
  | "dataInicio"
  | "dataFimPrevista"
  | "status"
  | "prioridade"
  | "descricao"
>;
