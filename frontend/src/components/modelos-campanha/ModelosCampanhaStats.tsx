import { Archive, CheckCircle2, Layers3, PauseCircle } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { ModeloCampanha } from "@/types/modelo-campanha";

export function ModelosCampanhaStats({ modelos }: { modelos: ModeloCampanha[] }) {
  const ativos = modelos.filter((modelo) => modelo.status === "ativo").length;
  const inativos = modelos.filter((modelo) => modelo.status === "inativo").length;
  const arquivados = modelos.filter((modelo) => modelo.status === "arquivado").length;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de modelos" value={modelos.length} description="Cadastrados na base." icon={<Layers3 size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativos" value={ativos} description="Em uso corrente." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Inativos" value={inativos} description="Preservados, fora de uso." icon={<PauseCircle size={16} />} tone="amber" />
      <MetricCard index={3} title="Arquivados" value={arquivados} description="Soft-delete, restauráveis." icon={<Archive size={16} />} tone="neutral" />
    </div>
  );
}
