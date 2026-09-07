export type SlaRegraStatus = "ativo" | "inativo" | "arquivado";

export type SlaPrioridadeAlvo = "baixa" | "media" | "alta";

// `null` = "todas as prioridades" — nunca uma string "todas" armazenada (contrato real,
// Fase 2G.6B). O rótulo "Todas as prioridades" é decisão só de apresentação.
export const slaPrioridadeAlvoLabels: Record<SlaPrioridadeAlvo, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

export type SlaUnidadePrazo = "minutos" | "horas" | "dias_corridos" | "dias_uteis";

export const slaUnidadePrazoLabels: Record<SlaUnidadePrazo, string> = {
  minutos: "Minutos",
  horas: "Horas",
  dias_corridos: "Dias corridos",
  dias_uteis: "Dias úteis",
};

const slaUnidadePrazoLabelsSingular: Record<SlaUnidadePrazo, string> = {
  minutos: "Minuto",
  horas: "Hora",
  dias_corridos: "Dia corrido",
  dias_uteis: "Dia útil",
};

export const slaStatusLabels: Record<SlaRegraStatus, string> = {
  ativo: "Ativa",
  inativo: "Inativa",
  arquivado: "Arquivada",
};

// Só apresentação — nunca converte entre unidades (dias úteis não é "24h", não tem
// equivalência fixa com horas/minutos). Singular só para quantidade === 1 ("1 Dia útil"),
// plural para o resto ("2 Dias úteis", "30 Minutos").
export function formatarPrazo(quantidade: number, unidade: SlaUnidadePrazo): string {
  const label = quantidade === 1 ? slaUnidadePrazoLabelsSingular[unidade] : slaUnidadePrazoLabels[unidade];
  return `${quantidade} ${label}`;
}

// Shape real de SlaRegraRead (backend, Fase 2G.6B) — camelCase via alias Pydantic, sem
// mapeamento manual no client. `null` onde o backend usa `null` (prioridadeAlvo/
// departamentoId/clienteId = "qualquer valor combina", nunca uma string "todas"/"" gravada).
export type SlaRegra = {
  id: string;
  empresaId: string;
  nome: string;
  descricao: string | null;
  prioridadeAlvo: SlaPrioridadeAlvo | null;
  departamentoId: string | null;
  clienteId: string | null;
  prioridadeRegra: number;
  prazoPrimeiraRespostaQuantidade: number;
  prazoPrimeiraRespostaUnidade: SlaUnidadePrazo;
  prazoResolucaoQuantidade: number;
  prazoResolucaoUnidade: SlaUnidadePrazo;
  considerarApenasExpediente: boolean;
  status: SlaRegraStatus;
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  arquivadoPorUsuarioId: string | null;
  motivoArquivamento: string | null;
  restauradoAt: string | null;
  restauradoPorUsuarioId: string | null;
  statusAnteriorArquivamento: SlaRegraStatus | null;
};

// Draft do formulário — usa "" internamente para Combobox/Select (que exigem string), nunca
// enviado à API como "": a fronteira de escrita mapeia "" -> null em
// `slaRegraDraftParaPayload` (api-backend.ts); a fronteira de leitura mapeia null -> "" em
// `createInitialDraft` (SlaFormModal.tsx). `status` só é relevante no modo edição (Create
// nasce sempre ativo — API nem aceita o campo no payload de criação); nunca "arquivado" aqui
// (arquivar é ação dedicada, não PATCH genérico).
export type SlaRegraFormDraft = {
  nome: string;
  descricao: string;
  prioridadeAlvo: SlaPrioridadeAlvo | "";
  departamentoId: string;
  clienteId: string;
  prioridadeRegra: number;
  prazoPrimeiraRespostaQuantidade: number;
  prazoPrimeiraRespostaUnidade: SlaUnidadePrazo;
  prazoResolucaoQuantidade: number;
  prazoResolucaoUnidade: SlaUnidadePrazo;
  considerarApenasExpediente: boolean;
  status: Extract<SlaRegraStatus, "ativo" | "inativo">;
};
