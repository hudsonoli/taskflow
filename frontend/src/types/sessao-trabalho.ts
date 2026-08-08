export type SessaoTrabalhoStatus = "ativa" | "encerrada" | "cancelada";

export interface SessaoTrabalho {
  id: string;
  empresaId: string;
  agenciaId: string | null;
  demandaId: string;
  workflowEtapaId: string | null;
  usuarioId: string | null;
  departamentoId: string | null;
  status: SessaoTrabalhoStatus;
  inicioEm: string;
  fimEm: string | null;
  duracaoSegundos: number | null;
  motivoEncerramento: string | null;
  createdAt: string;
  updatedAt: string;
}
