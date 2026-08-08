import { CheckCircle2, ShieldAlert, UsersRound } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { Equipe } from "@/types/equipe";

export function EquipesStats({ equipes }: { equipes: Equipe[] }) {
  const ativas = equipes.filter((equipe) => equipe.status === "ativo").length;
  const semLider = equipes.filter((equipe) => !equipe.liderId).length;
  const membrosAlocados = new Set(equipes.flatMap((equipe) => equipe.membroIds)).size;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de equipes" value={equipes.length} description="Cadastradas na base." icon={<UsersRound size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativas" value={ativas} description="Em operação." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Sem líder" value={semLider} description="Precisam de um responsável." icon={<ShieldAlert size={16} />} tone="amber" />
      <MetricCard index={3} title="Pessoas alocadas" value={membrosAlocados} description="Distintas em alguma equipe." icon={<UsersRound size={16} />} tone="neutral" />
    </div>
  );
}
