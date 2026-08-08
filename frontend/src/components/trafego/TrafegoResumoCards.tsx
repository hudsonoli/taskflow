import { Building2, CheckCircle2, CircleDot, Users, Workflow } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { TrafegoResumo } from "@/types/trafego";

export function TrafegoResumoCards({ resumo }: { resumo: TrafegoResumo }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
      <MetricCard index={0} title="Sessões ativas" value={resumo.sessoesAtivas} description="Agora" tone="blue" icon={<CircleDot size={16} />} />
      <MetricCard index={1} title="Sessões encerradas" value={resumo.sessoesEncerradas} description="Período filtrado" tone="green" icon={<CheckCircle2 size={16} />} />
      <MetricCard index={2} title="Demandas distintas" value={resumo.demandasDistintas} description="Com movimentação" tone="blue" icon={<Workflow size={16} />} />
      <MetricCard index={3} title="Usuários ativos" value={resumo.usuariosDistintos} description="Nas sessões filtradas" tone="neutral" icon={<Users size={16} />} />
      <MetricCard index={4} title="Departamentos" value={resumo.departamentosDistintos} description="Setores envolvidos" tone="amber" icon={<Building2 size={16} />} />
    </div>
  );
}
