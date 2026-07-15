import type {
  DashboardAgendaItem,
  DashboardAtividade,
  DashboardKpi,
  DashboardStatusIndicator,
  DashboardTaskTrendPoint,
} from "@/types/dashboard";

export const dashboardKpisMock: DashboardKpi[] = [
  { id: "tarefas", label: "Tarefas", value: 128 },
  { id: "projetos", label: "Projetos", value: 24 },
  { id: "sla", label: "SLA", value: "97%" },
];

// Ordem oficial pedida para a segunda linha — não reordenar.
export const dashboardStatusIndicatorsMock: DashboardStatusIndicator[] = [
  { id: "no-prazo", label: "No Prazo", value: 64, tone: "green" },
  { id: "atrasadas", label: "Atrasadas", value: 12, tone: "red" },
  { id: "concluidas", label: "Concluídas", value: 41, tone: "emerald" },
  { id: "refacoes", label: "Refações", value: 5, tone: "violet" },
  { id: "aguardando-cliente", label: "Aguardando Cliente", value: 9, tone: "amber" },
  { id: "aguardando-fornecedor", label: "Aguardando Fornecedor", value: 4, tone: "orange" },
  { id: "bloqueadas", label: "Bloqueadas", value: 3, tone: "slate" },
];

export const dashboardAgendaMock: DashboardAgendaItem[] = [
  { id: "agenda-1", horario: "09:30", titulo: "Reunião com Cliente Alfa", tag: "Prioridade alta" },
  { id: "agenda-2", horario: "11:00", titulo: "Ajuste de briefing", tag: "Operação" },
  { id: "agenda-3", horario: "14:00", titulo: "Status do Projeto Aurora", tag: "Projeto" },
  { id: "agenda-4", horario: "16:30", titulo: "Revisão de SLA", tag: "Gestão" },
];

export const dashboardAtividadesMock: DashboardAtividade[] = [
  {
    id: "atividade-1",
    descricao: "Novo cliente cadastrado — Casa Brasil",
    usuario: "Maria Souza",
    horario: "há 12 min",
    tone: "green",
  },
  {
    id: "atividade-2",
    descricao: "Projeto movido para revisão — Projeto Aurora",
    usuario: "João Silva",
    horario: "há 34 min",
    tone: "blue",
  },
  {
    id: "atividade-3",
    descricao: "Tarefa concluída — Revisão de briefing",
    usuario: "Ana Costa",
    horario: "há 51 min",
    tone: "green",
  },
  {
    id: "atividade-4",
    descricao: "Usuário adicionado à equipe — Equipe Criação",
    usuario: "Pedro Santos",
    horario: "há 2h",
    tone: "blue",
  },
  {
    id: "atividade-5",
    descricao: "SLA ajustado — Prioridade alta",
    usuario: "Carlos Lima",
    horario: "há 3h",
    tone: "amber",
  },
];

// Série determinística (sem Math.random/Date.now) — evita mismatch de
// hidratação entre servidor e cliente. Ponto final fixo em 14/07/2026,
// os outros 29 dias contam para trás a partir dele.
function buildDashboardTaskTrendMock(): DashboardTaskTrendPoint[] {
  const endDate = new Date(2026, 6, 14);
  const points: DashboardTaskTrendPoint[] = [];

  for (let dayOffset = 29; dayOffset >= 0; dayOffset -= 1) {
    const date = new Date(endDate);
    date.setDate(date.getDate() - dayOffset);
    const dayIndex = 29 - dayOffset;

    const criadas = 8 + Math.round(4 * Math.sin(dayIndex / 3.2)) + (dayIndex % 5 === 0 ? 3 : 0);
    const concluidas = 6 + Math.round(4 * Math.sin(dayIndex / 3.2 - 0.6));
    const atrasadas = 2 + Math.round(2 * Math.sin(dayIndex / 6 + 1)) + (dayIndex > 20 ? 1 : 0);

    points.push({
      data: date.toISOString().slice(0, 10),
      criadas: Math.max(2, criadas),
      concluidas: Math.max(1, concluidas),
      atrasadas: Math.max(0, atrasadas),
    });
  }

  return points;
}

export const dashboardTaskTrendMock: DashboardTaskTrendPoint[] = buildDashboardTaskTrendMock();
