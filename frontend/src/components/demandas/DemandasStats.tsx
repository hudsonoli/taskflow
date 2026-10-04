import { CheckCircle2, Clock3, Hourglass, ListChecks, PauseCircle } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import type { DemandaEstatisticas } from "@/types/demanda";

/**
 * Cards da tela Tarefas. Os números vêm do servidor (`GET /demandas/estatisticas`) sobre o
 * universo integral do escopo — não são mais contados sobre `AppDataContext.demandas` (limitado a
 * 200). `carregando` => "…"; `erro`/sem dado => "—".
 */
export function DemandasStats({
  estatisticas,
  carregando,
  erro,
}: {
  estatisticas: DemandaEstatisticas | null;
  carregando: boolean;
  erro: string | null;
}) {
  const valor = (extrair: (dados: DemandaEstatisticas) => number): number | string => {
    if (estatisticas) return extrair(estatisticas);
    return carregando ? "…" : "—";
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
        <MetricCard index={0} title="Total" value={valor((dados) => dados.total)} description="Tarefas cadastradas." icon={<ListChecks size={16} />} tone="blue" />
        <MetricCard index={1} title="Em execução" value={valor((dados) => dados.emExecucao)} description="Em andamento." icon={<Clock3 size={16} />} tone="green" />
        <MetricCard index={2} title="Pausadas/Bloqueadas" value={valor((dados) => dados.pausadasOuBloqueadas)} description="Fluxos suspensos." icon={<PauseCircle size={16} />} tone="amber" />
        <MetricCard index={3} title="Aguardando cliente" value={valor((dados) => dados.aguardandoCliente)} description="Retorno externo pendente." icon={<Hourglass size={16} />} tone="amber" />
        <MetricCard index={4} title="Concluídas" value={valor((dados) => dados.concluidas)} description="Tarefas finalizadas." icon={<CheckCircle2 size={16} />} tone="neutral" />
      </div>
      {erro && <p className="text-xs text-red-600 dark:text-red-400">Não foi possível carregar as estatísticas: {erro}</p>}
    </div>
  );
}
