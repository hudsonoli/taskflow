"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, ClipboardCheck, Clock3 } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import { Select } from "@/components/ui/Select";
import { analisarPerformanceColaborador } from "@/lib/relatorios";
import { responsaveisProjetoDisponiveis } from "@/lib/demandas";
import { useAppData } from "@/lib/AppDataContext";
import { DemandasPorProjetoDonut } from "./DemandasPorProjetoDonut";

export function PerformanceColaboradorReport() {
  const { demandas } = useAppData();
  const [colaboradorId, setColaboradorId] = useState(responsaveisProjetoDisponiveis[0]?.id ?? "");
  const performance = useMemo(() => analisarPerformanceColaborador(colaboradorId, demandas), [colaboradorId, demandas]);

  return (
    <div className="flex flex-col gap-4">
      <div className="max-w-xs">
        <Select
          label="Colaborador"
          value={colaboradorId}
          onChange={(event) => setColaboradorId(event.target.value)}
          options={responsaveisProjetoDisponiveis.map((usuario) => ({ value: usuario.id, label: usuario.nome }))}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricCard index={0} title="Demandas entregues" value={performance.demandasEntregues} description="No período selecionado" tone="blue" icon={<ClipboardCheck size={16} />} />
        <MetricCard index={1} title="Entregues no prazo" value={performance.entreguesNoPrazo} description="Dentro do prazo previsto" tone="green" icon={<CheckCircle2 size={16} />} />
        <MetricCard index={2} title="Entregues em atraso" value={performance.entreguesEmAtraso} description="Após o prazo previsto" tone="red" icon={<Clock3 size={16} />} />
      </div>

      <div className="rounded-xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
        <p className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Participação por etapa do workflow</p>
        <DemandasPorProjetoDonut
          fatias={performance.participacaoPorEtapa}
          emptyTitle="Sem participação registrada"
          emptyDescription="Este colaborador ainda não está vinculado a nenhuma etapa de workflow."
        />
      </div>
    </div>
  );
}
