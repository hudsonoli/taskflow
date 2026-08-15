export type DemandaStatus =
  | "rascunho"
  | "planejada"
  | "em_execucao"
  | "pausada"
  | "bloqueada"
  | "aguardando_cliente"
  | "concluida"
  | "cancelada"
  // Entra pela rota de arquivamento, com motivo obrigatório — nunca por edição de status.
  | "arquivada";

// Status oferecidos em formulário/Kanban. `arquivada` fica de fora: enviá-la num PATCH é 422.
export type DemandaStatusEditavel = Exclude<DemandaStatus, "arquivada">;

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

/**
 * Demanda — a unidade de trabalho da operação. A interface chama de **Tarefa**.
 *
 * ## Os três identificadores
 *
 * | Campo | Papel | Onde aparece |
 * |---|---|---|
 * | `id` (UUID) | técnico — chave de rota | **nunca exibido** |
 * | `numeroOperacional` (`2063`) | rótulo operacional | `#2063`, em toda listagem e card |
 * | `codigoReferencia` (`T26000001`) | identidade oficial, reinicia por ano | detalhe, busca, auditoria |
 *
 * Não derivam um do outro: a primeira demanda é `T26000001` **e** `#2063` ao mesmo tempo.
 *
 * ## Campos ainda sem persistência (Fase 2E.1)
 *
 * `workflowEtapas`, `etapaAtualId`, `checklist`, `arquivos`, `comentarios` e `historico`
 * entram em 2E.2–2E.4. A API os devolve **vazios** para os componentes não quebrarem, e
 * recusa (**422**) qualquer tentativa de enviá-los. A interface não exibe controle de escrita
 * para nenhum deles — affordance ausente com explicação, não campo desabilitado com valor
 * fantasma.
 */
export type Demanda = {
  id: string;
  empresaId: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  numeroOperacional: number;
  projetoId: string | null;
  clienteId: string | null;
  criadoPorUsuarioId: string | null;
  nome: string;
  pit?: string | null;
  briefing: string | null;
  status: DemandaStatus;
  prioridade: DemandaPrioridade;
  // Obrigatório quando `status === "bloqueada"`; limpo automaticamente ao sair do bloqueio
  // (o motivo anterior fica preservado no evento de domínio).
  motivoBloqueio: string | null;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  // Campo MANUAL e independente — não deriva de `prazoHoras` das etapas. A Pauta ordena por ele.
  prazoEtapaAtual: string | null;
  dataInicio: string | null;
  dataFimPrevista: string | null;
  enviadoClienteEm?: string | null;
  prazoRetornoCliente?: string | null;
  retornoRecebidoEm?: string | null;
  // Aviso de entrega final: se já foi enviado/dispensado ao concluir a demanda.
  emailConclusaoEnviado: boolean;
  emailConclusaoData?: string | null;
  // Bandeira de prioridade: ativável apenas por Gestão, heads e Atendimento (ver podeCriarDemanda).
  sinalizada: boolean;
  createdAt: string;
  updatedAt: string;
  arquivadoAt?: string | null;
  arquivadoPorUsuarioId?: string | null;
  motivoArquivamento?: string | null;
  restauradoAt?: string | null;
  restauradoPorUsuarioId?: string | null;
  statusAnteriorArquivamento?: DemandaStatus | null;

  // --- sem persistência nesta fase: sempre vazios, nunca editáveis ---
  workflowEtapas: DemandaWorkflowEtapa[];
  etapaAtualId: string | null;
  checklist: DemandaChecklistItem[];
  arquivos: DemandaArquivo[];
  comentarios: DemandaComentario[];
  historico: DemandaHistoricoEvento[];
};

/** Forma enxuta para seletores (`TrafegoIniciarSessao`) — também escopada no servidor. */
export type DemandaDiretorio = {
  id: string;
  numeroOperacional: number;
  codigoReferencia: string;
  nome: string;
  status: DemandaStatus;
  clienteId: string | null;
  projetoId: string | null;
};

/**
 * O que o formulário envia. `workflowEtapas` e `etapaAtualId` saíram: não há tabela para
 * gravá-las, e mandá-las devolveria 422.
 */
export type DemandaFormDraft = {
  nome: string;
  pit?: string | null;
  projetoId: string | null;
  clienteId: string | null;
  briefing: string | null;
  prioridade: DemandaPrioridade;
  status: DemandaStatusEditavel;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  dataFimPrevista: string | null;
};
