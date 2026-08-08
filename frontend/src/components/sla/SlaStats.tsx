import { CheckCircle2, Clock, Timer } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { SlaRegra } from "@/types/sla";

export function SlaStats({ slaRegras }: { slaRegras: SlaRegra[] }) {
  const ativas = slaRegras.filter((regra) => regra.ativo).length;
  const mediaResposta = slaRegras.length
    ? Math.round(slaRegras.reduce((total, regra) => total + regra.prazoPrimeiraRespostaHoras, 0) / slaRegras.length)
    : 0;
  const mediaResolucao = slaRegras.length
    ? Math.round(slaRegras.reduce((total, regra) => total + regra.prazoResolucaoHoras, 0) / slaRegras.length)
    : 0;

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <MetricCard index={0} title="Total de regras" value={slaRegras.length} description="Cadastradas na base." icon={<Timer size={16} />} tone="blue" />
      <MetricCard index={1} title="Ativas" value={ativas} description="Em vigor." icon={<CheckCircle2 size={16} />} tone="green" />
      <MetricCard index={2} title="Resposta média" value={`${mediaResposta}h`} description="Primeira resposta." icon={<Clock size={16} />} tone="amber" />
      <MetricCard index={3} title="Resolução média" value={`${mediaResolucao}h`} description="Prazo de resolução." icon={<Clock size={16} />} tone="neutral" />
    </div>
  );
}
