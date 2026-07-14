import { EmptyState } from "@/components/ui/EmptyState";

export type EntityHistoryEvent = {
  id: string;
  usuario: string;
  dataHora: string;
  acao: string;
  /**
   * Opcionais: nem toda entidade terá esses dados (dependem de captura no
   * backend/autenticação — ver observações de domínio em cada consumidor).
   * origem fica solto como string (não a união específica de um domínio,
   * ex. OrigemHistorico de Clientes) para não acoplar este componente
   * compartilhado a um vocabulário fixo.
   */
  ipOrigem?: string;
  dispositivo?: string;
  origem?: string;
};

export type EntityHistoryProps = {
  events: EntityHistoryEvent[];
  variant: "compact" | "full";
};

/**
 * Apresentação simples de eventos de histórico — consolida as ~7
 * implementações hoje duplicadas de HistoricoSection (uma por entidade).
 * variant="compact" (uso dentro de EntityPeek) mostra só o evento mais
 * recente, sem IP/dispositivo, para não aumentar o painel. variant="full"
 * (uso dentro de uma EntitySection dedicada) mostra a lista completa, cada
 * evento em duas linhas: ação+usuário em destaque, depois
 * data/hora · IP · dispositivo quando disponíveis. Sem paginação, sem
 * busca, sem carregamento assíncrono (ver entity-component-api.md, seção 9).
 */
export function EntityHistory({ events, variant }: EntityHistoryProps) {
  if (variant === "compact") {
    const latest = events[0];

    if (!latest) {
      return <p className="text-sm text-zinc-500">Nenhum histórico registrado.</p>;
    }

    return (
      <div>
        <h3 className="text-[11px] font-medium text-zinc-900">Último histórico</h3>
        <div className="mt-1.5 rounded-2xl bg-[#faf8f4] p-2.5">
          <p className="text-[11px] font-normal text-zinc-700">{latest.acao}</p>
          <p className="mt-1 text-[10px] font-normal text-zinc-400">
            {latest.usuario} · {latest.dataHora}
          </p>
        </div>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <EmptyState
        title="Nenhum evento registrado"
        description="As alterações feitas neste registro aparecerão aqui."
      />
    );
  }

  return (
    <div className="space-y-1.5">
      {events.map((event) => {
        const metaParts = [
          event.dataHora,
          event.ipOrigem ? `IP ${event.ipOrigem}` : null,
          event.dispositivo,
          event.origem,
        ].filter((part): part is string => Boolean(part));

        return (
          <div key={event.id} className="rounded-2xl border border-zinc-200 p-2.5">
            <p className="text-[11px] font-normal text-zinc-900">{event.acao}</p>
            <p className="mt-0.5 text-[10px] font-normal text-zinc-500">{event.usuario}</p>
            {metaParts.length > 0 && (
              <p className="mt-1 text-[10px] font-normal text-zinc-400">{metaParts.join(" · ")}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}
