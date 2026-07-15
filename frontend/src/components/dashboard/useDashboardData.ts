import { currentUser } from "@/lib/conta-mock";
import {
  dashboardAgendaMock,
  dashboardAtividadesMock,
  dashboardKpisMock,
  dashboardStatusIndicatorsMock,
  dashboardTaskTrendMock,
} from "@/lib/dashboard-mock";
import type { DashboardData } from "@/types/dashboard";

// Único ponto de acesso a dado da Dashboard. Hoje só repassa mocks
// estáticos (nenhum useState/useEffect/useMemo — não há nada assíncrono
// nem derivado a memoizar ainda); quando existir API, só este arquivo
// muda, nenhum componente visual precisa saber da diferença.
export function useDashboardData(): DashboardData {
  return {
    kpis: dashboardKpisMock,
    statusIndicators: dashboardStatusIndicatorsMock,
    taskTrend: dashboardTaskTrendMock,
    agenda: dashboardAgendaMock,
    atividades: dashboardAtividadesMock,
    currentUserNome: currentUser.nome,
  };
}
