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

/**
 * Etapa de workflow materializada na Demanda (Fase 2E.2) — snapshot aplicado a partir de um
 * `WorkflowModelo` no momento da criação, não uma referência viva a ele. Editar ou arquivar
 * o template depois não altera etapas já materializadas.
 *
 * Sem endpoint de transição nesta fase: `status` só é lido, nunca escrito diretamente pela
 * interface (ver `WorkflowDemandaSection`, só leitura).
 */
export type DemandaWorkflowEtapa = {
  id: string;
  nome: string;
  ordem: number;
  tipo: "execucao" | "aprovacao";
  quantidadeAntesDeadline: number;
  unidadePrazo: "dias_corridos" | "dias_uteis" | "horas";
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
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
 * ## Workflow (Fase 2E.2)
 *
 * `workflowEtapas` são materializadas a partir de um `WorkflowModelo` no momento da criação
 * (ver `workflowModeloId`) — snapshot, não referência viva: editar/arquivar o template depois
 * não muda nada aqui. `etapaAtualId` é derivado no servidor (menor `ordem` com
 * `status != "concluida"`), nunca uma escrita direta.
 *
 * ## Campos ainda sem persistência (Fase 2E.3/2E.4)
 *
 * `checklist`, `arquivos`, `comentarios` e `historico`. A API os devolve **vazios** para os
 * componentes não quebrarem, e recusa (**422**) qualquer tentativa de enviá-los. A interface
 * não exibe controle de escrita para nenhum deles — affordance ausente com explicação, não
 * campo desabilitado com valor fantasma.
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
  /** Qual WorkflowModelo originou `workflowEtapas` — só informativo (ver docstring acima). */
  workflowModeloId: string | null;
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

  // --- workflow materializado (2E.2) e coleções ainda sem persistência (2E.3/2E.4) ---
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
 * O que o formulário envia. `workflowEtapas` e `etapaAtualId` continuam fora: não há
 * endpoint de transição de etapa nesta fase, só `workflowModeloId` na criação (materializa
 * as etapas do template — ver docstring de `Demanda`). Mandar `workflowEtapas`/`etapaAtualId`
 * direto devolveria 422.
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
  /** Só tem efeito na criação (materializa as etapas do template). Editar depois não
   * reaplica nem troca o workflow já materializado nesta fase. */
  workflowModeloId?: string | null;
};
