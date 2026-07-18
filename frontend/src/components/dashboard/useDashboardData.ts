"use client";

import { useAuth } from "@/components/auth/useAuth";
import { currentUser } from "@/lib/conta-mock";
import {
  dashboardAgendaMock,
  dashboardAtividadesMock,
  dashboardKpisMock,
  dashboardStatusIndicatorsMock,
  dashboardTaskTrendMock,
} from "@/lib/dashboard-mock";
import type { DashboardData } from "@/types/dashboard";

// Único ponto de acesso aos dados da Dashboard. A identidade autenticada
// substitui somente o nome da saudação; os dados operacionais seguem mockados.
export function useDashboardData(): DashboardData {
  const { user } = useAuth();

  return {
    kpis: dashboardKpisMock,
    statusIndicators: dashboardStatusIndicatorsMock,
    taskTrend: dashboardTaskTrendMock,
    agenda: dashboardAgendaMock,
    atividades: dashboardAtividadesMock,
    currentUserNome: user?.nome ?? currentUser.nome,
  };
}
