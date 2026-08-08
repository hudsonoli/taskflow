import { BarChart3, CheckCircle2, FolderKanban, PlayCircle } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Projeto } from "@/types/projeto";

export function ProjetosStats({ projetos }: { projetos: Projeto[] }) {
  const ativos = projetos.filter((projeto) => projeto.status === "ativo").length;
  const emPlanejamento = projetos.filter((projeto) => projeto.status === "planejamento").length;
  const concluidos = projetos.filter((projeto) => projeto.status === "concluido").length;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de projetos" value={projetos.length} description="Projetos cadastrados." icon={<FolderKanban size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={ativos} description="Em execução." icon={<PlayCircle size={16} />} tone="green" />
      <MetricCard index={2} title="Em planejamento" value={emPlanejamento} description="Campanhas em preparação." icon={<BarChart3 size={16} />} tone="amber" />
      <MetricCard index={3} title="Concluídos" value={concluidos} description="Projetos finalizados." icon={<CheckCircle2 size={16} />} tone="neutral" />
    </div>
  );
}
