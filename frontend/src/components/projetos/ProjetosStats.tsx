import { WorkspaceStats } from "@/components/workspace/WorkspaceStats";
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
    <WorkspaceStats
      stats={[
        {
          label: "Total de projetos",
          value: projetos.length,
          description: "Projetos cadastrados no mock local.",
        },
        {
          label: "Ativos",
          value: ativos,
          description: "Projetos em execução.",
        },
        {
          label: "Em planejamento",
          value: emPlanejamento,
          description: "Campanhas em preparação.",
        },
        {
          label: "Concluídos",
          value: concluidos,
          description: "Projetos finalizados.",
        },
      ]}
    />
  );
}
