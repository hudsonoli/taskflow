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

export type ProjetoWorkflowEtapaConceitual = {
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
};

// Alinhado a docs/arquitetura-taskfloww/02-modelo-dados-futuro.md, seção 5
// (Checklist/ChecklistItem) — campos equivalentes ao desenho real futuro
// (descricao, concluido, concluidoEm, concluidoPor), sem entidade Checklist
// própria: aqui um projeto tem uma única lista, não múltiplos checklists.
export type ProjetoChecklistItem = {
  id: string;
  descricao: string;
  concluido: boolean;
  concluidoEm?: string;
  concluidoPor?: string;
};

// Alinhado a 02-modelo-dados-futuro.md, seção 9.2 (Comentario) — sem
// entidadeTipo/entidadeId (aqui o comentário já vive embutido no próprio
// Projeto, como historico/arquivos).
export type ProjetoComentario = {
  id: string;
  autorId: string;
  autorNome: string;
  texto: string;
  createdAt: string;
};

// "Aprovação" não tem entidade própria em 02-modelo-dados-futuro.md — lá é
// modelada como evento de transição de etapa de Workflow
// (WorkflowEtapaTemplate.exigeAprovacao + /aprovar//rejeitar). Este tipo é
// um placeholder de estrutura visual para o nível de Projeto, sem
// correspondência arquitetural ainda definida — ver relatório da Fase 8.
export type ProjetoAprovacaoStatus = "pendente" | "aprovado" | "rejeitado";

export type ProjetoAprovacao = {
  id: string;
  titulo: string;
  descricao?: string;
  status: ProjetoAprovacaoStatus;
  solicitadoPor: string;
  solicitadoEm: string;
  respondidoPor?: string;
  respondidoEm?: string;
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
  responsavelIds: string[];
  departamentoResponsavelIds: string[];
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
  checklist: ProjetoChecklistItem[];
  comentarios: ProjetoComentario[];
  aprovacoes: ProjetoAprovacao[];
};

export type ProjetoFormDraft = Pick<
  Projeto,
  | "nome"
  | "clienteId"
  | "campanha"
  | "responsavelIds"
  | "departamentoResponsavelIds"
  | "dataInicio"
  | "dataFimPrevista"
  | "status"
  | "prioridade"
  | "descricao"
>;
