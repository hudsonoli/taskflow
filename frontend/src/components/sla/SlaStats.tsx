import { Archive, CheckCircle2, CircleSlash, Timer } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { SlaRegra } from "@/types/sla";

// Sem média de prazos: unidades diferentes (minutos/horas/dias_corridos/dias_uteis) não são
// diretamente comparáveis — dias úteis em particular não tem equivalência fixa em horas. Só
// métricas estruturais (contagem por status), que são sempre semanticamente corretas.
export function SlaStats({ slaRegras }: { slaRegras: SlaRegra[] }) {
  const ativas = slaRegras.filter((regra) => regra.status === "ativo").length;
  const inativas = slaRegras.filter((regra) => regra.status === "inativo").length;
  const arquivadas = slaRegras.filter((regra) => regra.status === "arquivado").length;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de regras" value={slaRegras.length} description="Nesta listagem." icon={<Timer size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativas" value={ativas} description="Em vigor." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Inativas" value={inativas} description="Fora de vigor." icon={<CircleSlash size={16} />} tone="amber" />
      <MetricCard index={3} title="Arquivadas" value={arquivadas} description="Fora da listagem padrão." icon={<Archive size={16} />} tone="neutral" />
    </div>
  );
}
