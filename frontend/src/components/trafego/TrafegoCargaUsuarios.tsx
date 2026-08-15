import { Badge } from "@/components/ui/Badge";
import { RankingCard } from "@/components/ui/RankingCard";
import { classifyCarga, formatTempoOperacional, resolveTrafegoUsuarioNome } from "@/lib/trafego";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import type { TrafegoCargaItem } from "@/types/trafego";

export function TrafegoCargaUsuarios({
  cargas,
  diretorio,
}: {
  cargas: TrafegoCargaItem[];
  diretorio: UsuarioDiretorioItem[];
}) {
  const maxValue = Math.max(1, ...cargas.map((carga) => carga.tempoAtivoTotalSegundos));

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
          label: resolveTrafegoUsuarioNome(carga.agrupamentoId, diretorio),
          value: carga.tempoAtivoTotalSegundos,
          maxValue,
          displayValue: formatTempoOperacional(carga.tempoAtivoTotalSegundos),
          description: `${carga.sessoesAtivas} sessão(ões) · ${carga.demandasDistintas} demanda(s)`,
          color: "bg-indigo-500",
          badge: <Badge tone="blue">{classification.label}</Badge>,
        };
      })}
    />
  );
}
