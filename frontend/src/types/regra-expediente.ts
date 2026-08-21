export type DiaSemana = 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0 = segunda .. 6 = domingo (Fase 2G.3)

export type JanelaDia = {
  diaSemana: DiaSemana;
  ativo: boolean;
  manhaInicio: string | null;
  manhaFim: string | null;
  tardeInicio: string | null;
  tardeFim: string | null;
};

export type RegraExpediente = {
  id: string;
  empresaId: string;
  ativo: boolean;
  toleranciaRetomadaMinutos: number;
  dias: JanelaDia[];
  createdAt: string;
  updatedAt: string;
};

// Full-replace: quando `dias` é enviado, precisa cobrir os 7 dias — mesma regra do backend
// (RegraExpedienteUpdate.validar_dias_completos).
export type RegraExpedienteUpdateDraft = {
  ativo?: boolean;
  toleranciaRetomadaMinutos?: number;
  dias?: JanelaDia[];
};

// GET /expediente/estado — leitura operacional enxuta (Kanban, capacidade de Meu
// Departamento). Nunca as janelas por dia, só agregados: ver EstadoExpedienteRead no backend.
export type EstadoExpediente = {
  ativo: boolean;
  dentroExpediente: boolean;
  agora: string;
  toleranciaRetomadaMinutos: number;
  horasUteisHoje: number;
};
