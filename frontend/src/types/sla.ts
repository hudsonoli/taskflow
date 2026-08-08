import type { DemandaPrioridade } from "@/types/demanda";

export type SlaPrioridadeAlvo = DemandaPrioridade | "todas";

export const slaPrioridadeAlvoLabels: Record<SlaPrioridadeAlvo, string> = {
  todas: "Todas as prioridades",
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

export type SlaRegra = {
  id: string;
  empresaId: string;
  nome: string;
  descricao: string;
  prioridade: SlaPrioridadeAlvo;
  // "" = aplica a todos os departamentos/clientes.
  departamentoId: string;
  clienteId: string;
  prazoPrimeiraRespostaHoras: number;
  prazoResolucaoHoras: number;
  // Quando true, o prazo só corre dentro do horário de expediente configurado (RegraExpediente).
  considerarApenasExpediente: boolean;
  ativo: boolean;
  createdAt: string;
  updatedAt: string;
};

export type SlaRegraFormDraft = Omit<SlaRegra, "id" | "empresaId" | "createdAt" | "updatedAt">;
