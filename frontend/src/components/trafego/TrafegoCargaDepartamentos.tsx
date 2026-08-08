import { Badge } from "@/components/ui/Badge";
import { RankingCard } from "@/components/ui/RankingCard";
import { classifyCarga, formatTempoOperacional, resolveTrafegoDepartamentoNome } from "@/lib/trafego";
import type { TrafegoCargaItem } from "@/types/trafego";

export function TrafegoCargaDepartamentos({ cargas }: { cargas: TrafegoCargaItem[] }) {
  const maxValue = Math.max(1, ...cargas.map((carga) => carga.tempoAtivoTotalSegundos));

  return (
    <RankingCard
      title="Carga por departamento"
      description="Setores com execução em andamento."
      emptyTitle="Nenhum departamento em execução"
      emptyDescription="Os filtros atuais não retornaram sessões ativas por departamento."
      items={cargas.map((carga) => {
        const classification = classifyCarga(carga.tempoAtivoTotalSegundos);
        return {
          id: carga.agrupamentoId,
          label: resolveTrafegoDepartamentoNome(carga.agrupamentoId),
          value: carga.tempoAtivoTotalSegundos,
          maxValue,
          displayValue: formatTempoOperacional(carga.tempoAtivoTotalSegundos),
          description: `${carga.sessoesAtivas} sessão(ões) · ${carga.demandasDistintas} demanda(s)`,
          color: "bg-emerald-500",
          badge: <Badge tone="green">{classification.label}</Badge>,
        };
      })}
    />
  );
}
