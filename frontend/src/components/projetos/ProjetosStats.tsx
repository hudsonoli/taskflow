import { BarChart3, CheckCircle2, FolderKanban, PlayCircle } from "lucide-react";
import { DashboardGrid } from "@/components/ui/DashboardGrid";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Projeto } from "@/types/projeto";

type ProjetosStatsProps = {
  projetos: Projeto[];
};

export function ProjetosStats({ projetos }: ProjetosStatsProps) {
  const ativos = projetos.filter((projeto) => projeto.status === "ativo").length;
  const emPlanejamento = projetos.filter(
    (projeto) => projeto.status === "planejamento"
  ).length;
  const concluidos = projetos.filter(
    (projeto) => projeto.status === "concluido"
  ).length;

  return (
    <DashboardGrid columns="four">
      <MetricCard
        title="Total de projetos"
        value={projetos.length}
        description="Projetos cadastrados no mock local."
        icon={<FolderKanban className="h-5 w-5" />}
        tone="blue"
      />
      <MetricCard
        title="Ativos"
        value={ativos}
        description="Projetos em execução."
        icon={<PlayCircle className="h-5 w-5" />}
        tone="green"
      />
      <MetricCard
        title="Em planejamento"
        value={emPlanejamento}
        description="Campanhas em preparação."
        icon={<BarChart3 className="h-5 w-5" />}
        tone="amber"
      />
      <MetricCard
        title="Concluídos"
        value={concluidos}
        description="Projetos finalizados."
        icon={<CheckCircle2 className="h-5 w-5" />}
        tone="neutral"
      />
    </DashboardGrid>
  );
}
