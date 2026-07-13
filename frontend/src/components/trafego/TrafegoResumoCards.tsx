import {
  Building2,
  CheckCircle2,
  CircleDot,
  Users,
  Workflow,
} from "lucide-react";
import { DashboardGrid } from "@/components/ui/DashboardGrid";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusPill } from "@/components/ui/StatusPill";
import type { TrafegoResumo } from "@/types/trafego";

type TrafegoResumoCardsProps = {
  resumo: TrafegoResumo;
};

export function TrafegoResumoCards({ resumo }: TrafegoResumoCardsProps) {
  return (
    <DashboardGrid columns="five">
      <MetricCard
        title="Sessões ativas"
        value={resumo.sessoesAtivas}
        description="Agora"
        tone="blue"
        icon={<CircleDot className="h-5 w-5" aria-hidden="true" />}
        badge={<StatusPill tone="blue">em execução</StatusPill>}
      />
      <MetricCard
        title="Sessões encerradas"
        value={resumo.sessoesEncerradas}
        description="Período filtrado"
        tone="green"
        icon={<CheckCircle2 className="h-5 w-5" aria-hidden="true" />}
      />
      <MetricCard
        title="Demandas distintas"
        value={resumo.demandasDistintas}
        description="Com movimentação"
        tone="blue"
        icon={<Workflow className="h-5 w-5" aria-hidden="true" />}
      />
      <MetricCard
        title="Usuários ativos"
        value={resumo.usuariosDistintos}
        description="Nas sessões filtradas"
        tone="neutral"
        icon={<Users className="h-5 w-5" aria-hidden="true" />}
      />
      <MetricCard
        title="Departamentos"
        value={resumo.departamentosDistintos}
        description="Setores envolvidos"
        tone="amber"
        icon={<Building2 className="h-5 w-5" aria-hidden="true" />}
      />
    </DashboardGrid>
  );
}
