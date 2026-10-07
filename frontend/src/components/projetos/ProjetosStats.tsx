import { BarChart3, CheckCircle2, FolderKanban, PlayCircle } from "lucide-react";
import { KpiStrip } from "@/components/ui/KpiStrip";
import type { Projeto } from "@/types/projeto";

export function ProjetosStats({ projetos }: { projetos: Projeto[] }) {
  const ativos = projetos.filter((projeto) => projeto.status === "ativo").length;
  const emPlanejamento = projetos.filter((projeto) => projeto.status === "planejamento").length;
  const concluidos = projetos.filter((projeto) => projeto.status === "concluido").length;

  return (
    <KpiStrip
      ariaLabel="Indicadores dos projetos"
      itens={[
        { key: "total", label: "Total de projetos", value: projetos.length, description: "Projetos cadastrados.", icon: <FolderKanban size={16} />, tone: "blue" },
        { key: "ativos", label: "Ativos", value: ativos, description: "Em execução.", icon: <PlayCircle size={16} />, tone: "green" },
        { key: "planejamento", label: "Em planejamento", value: emPlanejamento, description: "Campanhas em preparação.", icon: <BarChart3 size={16} />, tone: "amber" },
        { key: "concluidos", label: "Concluídos", value: concluidos, description: "Projetos finalizados.", icon: <CheckCircle2 size={16} />, tone: "neutral" },
      ]}
    />
  );
}
