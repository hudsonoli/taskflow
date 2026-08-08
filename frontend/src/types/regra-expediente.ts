export type RegraExpediente = {
  id: string;
  empresaId: string;
  ativo: boolean;
  manhaInicio: string;
  manhaFim: string;
  tardeInicio: string;
  tardeFim: string;
  // Minutos antes de "tardeInicio" em que a retomada manual (arrastar para Em execução) já é permitida.
  toleranciaRetomadaMinutos: number;
  createdAt: string;
  updatedAt: string;
};

export type RegraExpedienteFormDraft = Omit<RegraExpediente, "id" | "empresaId" | "createdAt" | "updatedAt">;
