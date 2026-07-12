import { RankingCard } from "@/components/ui/RankingCard";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  classifyCarga,
  formatTempoOperacional,
  resolveTrafegoUsuarioNome,
} from "@/lib/trafego-mock";
import type { TrafegoCargaItem } from "@/types/trafego";

type TrafegoCargaUsuariosProps = {
  cargas: TrafegoCargaItem[];
};

function toneForCarga(seconds: number) {
  if (seconds < 1800) return "green";
  if (seconds < 4200) return "blue";
  return "amber";
}

export function TrafegoCargaUsuarios({ cargas }: TrafegoCargaUsuariosProps) {
  return (
    <RankingCard
      title="Carga por usuário"
      description="Colaboradores com sessões ativas no momento."
      emptyTitle="Nenhum usuário em execução"
      emptyDescription="Os filtros atuais não retornaram sessões ativas por usuário."
      items={cargas.map((carga) => {
        const classification = classifyCarga(carga.tempoAtivoTotalSegundos);

        return {
          id: carga.agrupamentoId,
          label: resolveTrafegoUsuarioNome(carga.agrupamentoId),
          value: carga.tempoAtivoTotalSegundos,
          displayValue: formatTempoOperacional(carga.tempoAtivoTotalSegundos),
          description: `${carga.sessoesAtivas} sessão(ões) · ${carga.demandasDistintas} demanda(s)`,
          color: "#2563eb",
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
