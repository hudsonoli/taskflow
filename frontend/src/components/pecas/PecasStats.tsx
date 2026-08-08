import { CheckCircle2, Clock3, Layers3, Tag } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import { formatHoursMinutes } from "@/lib/pecas-mock";
import type { Peca } from "@/types/peca";

export function PecasStats({ pecas }: { pecas: Peca[] }) {
  const ativas = pecas.filter((peca) => peca.ativa).length;
  const categorias = new Set(pecas.map((peca) => peca.categoria).filter(Boolean)).size;
  const comTempo = pecas.filter((peca) => peca.tempoEstimadoMinutos);
  const tempoMedio = comTempo.length
    ? comTempo.reduce((total, peca) => total + (peca.tempoEstimadoMinutos ?? 0), 0) / comTempo.length
    : 0;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de peças" value={pecas.length} description="No catálogo." icon={<Layers3 size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativas" value={ativas} description="Disponíveis para uso." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Categorias" value={categorias} description="Distintas no catálogo." icon={<Tag size={16} />} tone="amber" />
      <MetricCard
        index={3}
        title="Estimativa média"
        value={tempoMedio ? `${formatHoursMinutes(tempoMedio)}h` : "-"}
        description="Média do tempo estimado entre peças com valor definido."
        icon={<Clock3 size={16} />}
        tone="neutral"
      />
    </div>
  );
}
