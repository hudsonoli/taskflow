import { Badge } from "@/components/ui/Badge";
import { RankingCard } from "@/components/ui/RankingCard";
import { classifyCarga, formatTempoOperacional } from "@/lib/trafego";
import type { EquipeDiretorioItem } from "@/lib/api-backend";
import type { TrafegoCargaItem } from "@/types/trafego";

export function TrafegoCargaEquipes({ cargas, equipes }: { cargas: TrafegoCargaItem[]; equipes: EquipeDiretorioItem[] }) {
  const maxValue = Math.max(1, ...cargas.map((carga) => carga.tempoAtivoTotalSegundos));

  return (
    <RankingCard
      title="Carga por equipe"
      description="Squads com execução em andamento."
      emptyTitle="Nenhuma equipe em execução"
      emptyDescription="Os filtros atuais não retornaram sessões ativas por equipe."
      items={cargas.map((carga) => {
        const classification = classifyCarga(carga.tempoAtivoTotalSegundos);
        const equipe = equipes.find((item) => item.id === carga.agrupamentoId);
        return {
          id: carga.agrupamentoId,
          label: equipe?.nome ?? carga.agrupamentoId,
          value: carga.tempoAtivoTotalSegundos,
          maxValue,
          displayValue: formatTempoOperacional(carga.tempoAtivoTotalSegundos),
          description: `${carga.sessoesAtivas} sessão(ões) · ${carga.demandasDistintas} demanda(s)`,
          color: "bg-purple-500",
          badge: <Badge tone="blue">{classification.label}</Badge>,
        };
      })}
    />
  );
}
