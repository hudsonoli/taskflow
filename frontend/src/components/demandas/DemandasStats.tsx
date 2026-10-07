import { CheckCircle2, Clock3, Hourglass, ListChecks, PauseCircle } from "lucide-react";
import { KpiStrip } from "@/components/ui/KpiStrip";
import type { DemandaEstatisticas } from "@/types/demanda";

/**
 * Indicadores da tela Tarefas. Os números vêm do servidor (`GET /demandas/estatisticas`) sobre o
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
      <KpiStrip
        ariaLabel="Indicadores das tarefas"
        itens={[
          { key: "total", label: "Total", value: valor((dados) => dados.total), description: "Tarefas cadastradas.", icon: <ListChecks size={16} />, tone: "blue" },
          { key: "em-execucao", label: "Em execução", value: valor((dados) => dados.emExecucao), description: "Em andamento.", icon: <Clock3 size={16} />, tone: "green" },
          { key: "pausadas-bloqueadas", label: "Pausadas/Bloqueadas", value: valor((dados) => dados.pausadasOuBloqueadas), description: "Fluxos suspensos.", icon: <PauseCircle size={16} />, tone: "amber" },
          { key: "aguardando-cliente", label: "Aguardando cliente", value: valor((dados) => dados.aguardandoCliente), description: "Retorno externo pendente.", icon: <Hourglass size={16} />, tone: "amber" },
          { key: "concluidas", label: "Concluídas", value: valor((dados) => dados.concluidas), description: "Tarefas finalizadas.", icon: <CheckCircle2 size={16} />, tone: "neutral" },
        ]}
      />
      {erro && <p className="text-xs text-red-600 dark:text-red-400">Não foi possível carregar as estatísticas: {erro}</p>}
    </div>
  );
}
