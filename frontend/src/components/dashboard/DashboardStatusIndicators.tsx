import { CadastroIndicators } from "@/components/cadastros";
import type { DashboardStatusIndicator } from "@/types/dashboard";

type DashboardStatusIndicatorsProps = {
  statusIndicators: DashboardStatusIndicator[];
};

// Sete indicadores operacionais, na ordem oficial definida pelo mock
// (dashboard-mock.ts) — não reordenar aqui. mobile=1 col, sm=2, lg
// (notebook, ~1366px)=4 (quebra 4+3), 2xl (desktop grande)=7. Não uso
// "xl" para o layout de 7 colunas porque, com a Sidebar aberta, a área
// útil de conteúdo em notebooks de ~1366px de viewport já cai na faixa
// "xl" do Tailwind mas não tem largura real para 7 cards sem espremer.
export function DashboardStatusIndicators({
  statusIndicators,
}: DashboardStatusIndicatorsProps) {
  return (
    <CadastroIndicators
      density="compact"
      columnsClassName="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-7"
      items={statusIndicators.map((indicator) => ({
        label: indicator.label,
        value: indicator.value,
        tone: indicator.tone,
      }))}
    />
  );
}
