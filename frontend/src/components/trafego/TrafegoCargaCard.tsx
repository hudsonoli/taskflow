import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { RankingCard } from "@/components/ui/RankingCard";
import { classifyCarga, formatTempoOperacional } from "@/lib/trafego";
import type { TrafegoCargaAgregada } from "@/types/trafego";

/**
 * D2-D3C2 — ranking de carga (usuário/departamento/equipe) sobre os agregados do servidor
 * (`GET /sessoes-trabalho/trafego/carga`), já com nome e já ordenados — nunca mais agrupados no
 * cliente a partir de uma lista de 100 sessões. `cargas === null` é "carregando"; `erro` é falha
 * da requisição (nenhum dos dois fabrica ranking); lista vazia é "zero confirmado".
 */
export function TrafegoCargaCard({
  title,
  description,
  emptyTitle,
  emptyDescription,
  cargas,
  erro,
  color,
  badgeTone,
}: {
  title: string;
  description: string;
  emptyTitle: string;
  emptyDescription: string;
  cargas: TrafegoCargaAgregada[] | null;
  erro?: string | null;
  color: string;
  badgeTone: BadgeTone;
}) {
  const itens = erro ? [] : (cargas ?? []);
  const maxValue = Math.max(1, ...itens.map((carga) => carga.tempoAtivoTotalSegundos));
  const vazio = erro
    ? { title: "Não foi possível carregar a carga", description: erro }
    : cargas === null
      ? { title: "Carregando…", description: "Buscando a carga no servidor." }
      : { title: emptyTitle, description: emptyDescription };

  return (
    <RankingCard
      title={title}
      description={description}
      emptyTitle={vazio.title}
      emptyDescription={vazio.description}
      items={itens.map((carga) => ({
        id: carga.id,
        label: carga.nome,
        value: carga.tempoAtivoTotalSegundos,
        maxValue,
        displayValue: formatTempoOperacional(carga.tempoAtivoTotalSegundos),
        description: `${carga.sessoesAtivas} sessão(ões) · ${carga.demandasDistintas} demanda(s)`,
        color,
        badge: <Badge tone={badgeTone}>{classifyCarga(carga.tempoAtivoTotalSegundos).label}</Badge>,
      }))}
    />
  );
}
