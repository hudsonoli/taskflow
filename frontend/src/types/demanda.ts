export type DemandaStatus =
  | "rascunho"
  | "planejada"
  | "em_execucao"
  | "pausada"
  | "bloqueada"
  | "aguardando_cliente"
  | "concluida"
  | "cancelada";

export type DemandaPrioridade = "baixa" | "media" | "alta";

export type DemandaWorkflowEtapaStatus = "pendente" | "em_execucao" | "pausada" | "concluida";

export type DemandaWorkflowEtapa = {
  id: string;
  nome: string;
  ordem: number;
  // Execução (azul) ou aprovação/gate (âmbar) — opcional: etapas criadas manualmente não têm tipo definido.
  tipo?: "execucao" | "aprovacao";
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  prazoHoras: number;
  status: DemandaWorkflowEtapaStatus;
};

export type DemandaChecklistItem = {
  id: string;
  texto: string;
  concluido: boolean;
};

export type DemandaArquivo = {
  nome: string;
  url: string;
  tamanhoBytes: number;
  finalDoCliente: boolean;
};

export type DemandaComentario = {
  id: string;
  usuarioId: string;
  usuario: string;
  texto: string;
  dataHora: string;
  // IDs de usuários citados via @Nome no texto — usado para notificar menções.
  mencoes: string[];
};

export type DemandaHistoricoTipo = "ajuste_interno" | "ajuste_cliente" | "refacao" | "outro";

export type DemandaHistoricoEvento = {
  id: string;
  usuarioId: string;
  usuario: string;
  acao: string;
  tipo?: DemandaHistoricoTipo;
  dataHora: string;
  ip: string;
  dispositivo: string;
};

export type Demanda = {
  id: string;
  empresaId: string;
  agenciaId: string;
  projetoId: string;
  clienteId: string;
  codigoInterno: string;
  nome: string;
  pit?: string;
  briefing: string;
  status: DemandaStatus;
  prioridade: DemandaPrioridade;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  workflowEtapas: DemandaWorkflowEtapa[];
  etapaAtualId: string;
  prazoEtapaAtual: string;
  dataCriacao: string;
  dataInicio: string;
  dataFimPrevista: string;
  enviadoClienteEm?: string;
  prazoRetornoCliente?: string;
  retornoRecebidoEm?: string;
  // Aviso de entrega final: se já foi enviado/dispensado ao concluir a demanda.
  emailConclusaoEnviado: boolean;
  emailConclusaoData?: string;
  // Bandeira de prioridade: ativável apenas por Gestão, heads e Atendimento (ver podeCriarDemanda).
  sinalizada: boolean;
  checklist: DemandaChecklistItem[];
  arquivos: DemandaArquivo[];
  comentarios: DemandaComentario[];
  createdAt: string;
  updatedAt: string;
  historico: DemandaHistoricoEvento[];
};

export type DemandaFormDraft = Pick<
  Demanda,
  | "nome"
  | "pit"
  | "projetoId"
  | "clienteId"
  | "briefing"
  | "prioridade"
  | "status"
  | "usuarioResponsavelIds"
  | "departamentoResponsavelIds"
  | "dataFimPrevista"
  | "workflowEtapas"
  | "etapaAtualId"
>;
