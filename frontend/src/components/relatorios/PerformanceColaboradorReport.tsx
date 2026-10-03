"use client";

import { useCallback, useState } from "react";
import { CheckCircle2, ClipboardCheck, Clock3 } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import { Select } from "@/components/ui/Select";
import { getRelatorioColaboradores, getRelatorioPerformanceColaborador } from "@/lib/api-backend";
import { useConsultaRelatorio } from "@/lib/useConsultaRelatorio";
import type { RelatorioPerformanceColaborador } from "@/types/relatorios";
import { DemandasPorProjetoDonut } from "./DemandasPorProjetoDonut";
import { GraficoEstado } from "./GraficoEstado";

// Sem colaborador resolvido (lista vazia) não há consulta: a tela mostra o estado zerado de sempre.
const PERFORMANCE_ZERADA: RelatorioPerformanceColaborador = {
  colaboradorId: "",
  colaboradorNome: "",
  demandasEntregues: 0,
  entreguesNoPrazo: 0,
  entreguesEmAtraso: 0,
  participacaoPorEtapa: [],
};

export function PerformanceColaboradorReport() {
  // D4B — as opções vêm do servidor (consulta histórica: inclui inativo/bloqueado/arquivado e
  // não tem o `limit=200` do diretório) e a performance é calculada sobre TODAS as Demandas do
  // colaborador (antes: `analisarPerformanceColaborador` sobre `AppDataContext.demandas`, só as
  // 200 mais recentes da empresa).
  const { resultado: opcoes, erro: erroOpcoes } = useConsultaRelatorio(getRelatorioColaboradores);
  const [colaboradorIdSelecionado, setColaboradorIdSelecionado] = useState("");
  // As opções carregam assíncronas: antes de resolver a lista está vazia, e capturar o primeiro
  // id num `useState` inicial ficaria travado em "". Deriva o efetivo a cada render.
  const colaboradorId = colaboradorIdSelecionado || opcoes?.[0]?.id || "";

  const buscarPerformance = useCallback(() => getRelatorioPerformanceColaborador(colaboradorId), [colaboradorId]);
  const { resultado, carregando, erro } = useConsultaRelatorio(colaboradorId ? buscarPerformance : null);
  const performance = colaboradorId ? resultado : PERFORMANCE_ZERADA;

  // `carregando` => "…"; `erro` => "—" (nunca um número parcial).
  const valor = (extrair: (dados: RelatorioPerformanceColaborador) => number): number | string => {
    if (carregando) return "…";
    if (!performance) return "—";
    return extrair(performance);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="max-w-xs">
        <Select
          label="Colaborador"
          value={colaboradorId}
          onChange={(event) => setColaboradorIdSelecionado(event.target.value)}
          options={(opcoes ?? []).map((opcao) => ({ value: opcao.id, label: opcao.nome }))}
        />
      </div>

      {erroOpcoes && (
        <p className="text-xs text-red-600 dark:text-red-400">Não foi possível carregar os colaboradores: {erroOpcoes}</p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricCard index={0} title="Demandas entregues" value={valor((dados) => dados.demandasEntregues)} description="No período selecionado" tone="blue" icon={<ClipboardCheck size={16} />} />
        <MetricCard index={1} title="Entregues no prazo" value={valor((dados) => dados.entreguesNoPrazo)} description="Dentro do prazo previsto" tone="green" icon={<CheckCircle2 size={16} />} />
        <MetricCard index={2} title="Entregues em atraso" value={valor((dados) => dados.entreguesEmAtraso)} description="Após o prazo previsto" tone="red" icon={<Clock3 size={16} />} />
      </div>

      <div className="rounded-xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
        <p className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Participação por etapa do workflow</p>
        <GraficoEstado carregando={carregando} erro={erro}>
          <DemandasPorProjetoDonut
            fatias={performance?.participacaoPorEtapa ?? []}
            emptyTitle="Sem participação registrada"
            emptyDescription="Este colaborador ainda não está vinculado a nenhuma etapa de workflow."
          />
        </GraficoEstado>
      </div>
    </div>
  );
}
