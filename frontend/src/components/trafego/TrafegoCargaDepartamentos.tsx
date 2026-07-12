import { RankingCard } from "@/components/ui/RankingCard";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  classifyCarga,
  formatTempoOperacional,
  resolveTrafegoDepartamentoNome,
} from "@/lib/trafego-mock";
import type { TrafegoCargaItem } from "@/types/trafego";

type TrafegoCargaDepartamentosProps = {
  cargas: TrafegoCargaItem[];
};

function toneForCarga(seconds: number) {
  if (seconds < 1800) return "green";
  if (seconds < 4200) return "blue";
  return "amber";
}

export function TrafegoCargaDepartamentos({
  cargas,
}: TrafegoCargaDepartamentosProps) {
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
          displayValue: formatTempoOperacional(carga.tempoAtivoTotalSegundos),
          description: `${carga.sessoesAtivas} sessão(ões) · ${carga.demandasDistintas} demanda(s)`,
          color: "#10b981",
          badge: (
            <StatusPill tone={toneForCarga(carga.tempoAtivoTotalSegundos)}>
              {classification.label}
            </StatusPill>
          ),
        };
      })}
    />
  );
}
