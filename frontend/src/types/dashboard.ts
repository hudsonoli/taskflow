export type DashboardKpi = {
  id: string;
  label: string;
  value: string | number;
};

// Tons semânticos dos 7 indicadores operacionais — green e emerald são
// intencionalmente tons distintos (não variações do mesmo "verde"): green
// (mais claro/suave) para "No Prazo", emerald (mais forte) para
// "Concluídas", para os dois nunca ficarem visualmente iguais.
export type DashboardStatusTone =
  | "green"
  | "emerald"
  | "red"
  | "violet"
  | "amber"
  | "orange"
  | "slate";

export type DashboardStatusIndicator = {
  id: string;
  label: string;
  value: string | number;
  tone: DashboardStatusTone;
};

export type DashboardAgendaItem = {
  id: string;
  horario: string;
  titulo: string;
  tag: string;
};

export type DashboardAtividadeTone = "neutral" | "blue" | "green" | "amber" | "red";

export type DashboardAtividade = {
  id: string;
  descricao: string;
  usuario: string;
  horario: string;
  tone: DashboardAtividadeTone;
};

export type DashboardTaskTrendPoint = {
  data: string;
  criadas: number;
  concluidas: number;
  atrasadas: number;
};

export type DashboardData = {
  kpis: DashboardKpi[];
  statusIndicators: DashboardStatusIndicator[];
  taskTrend: DashboardTaskTrendPoint[];
  agenda: DashboardAgendaItem[];
  atividades: DashboardAtividade[];
  currentUserNome: string;
};
