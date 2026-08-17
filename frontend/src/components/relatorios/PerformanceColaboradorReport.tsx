"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, ClipboardCheck, Clock3 } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import { Select } from "@/components/ui/Select";
import { analisarPerformanceColaborador } from "@/lib/relatorios";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { useAppData } from "@/lib/AppDataContext";
import { DemandasPorProjetoDonut } from "./DemandasPorProjetoDonut";

export function PerformanceColaboradorReport() {
  const { demandas } = useAppData();
  // Consulta histórica, não seleção de vínculo novo — inclui inativo/bloqueado (o diretório já
  // exclui só arquivado por padrão, ver `usuario_repository.list_diretorio`), pra não esconder
  // colaborador com Demandas passadas só porque ele não está mais ativo hoje.
  const { usuarios } = useDiretorioUsuarios();
  const [colaboradorIdSelecionado, setColaboradorIdSelecionado] = useState("");
  // O diretório carrega assíncrono (cache remoto): antes de resolver, `usuarios` está vazio, e
  // capturar o primeiro id num `useState` inicial ficaria travado em "". Deriva o efetivo a
  // cada render em vez disso — sem `useEffect`, sem setState em cascata.
  const colaboradorId = colaboradorIdSelecionado || usuarios[0]?.id || "";

  const performance = useMemo(
    () => analisarPerformanceColaborador(colaboradorId, demandas, usuarios),
    [colaboradorId, demandas, usuarios],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="max-w-xs">
        <Select
          label="Colaborador"
          value={colaboradorId}
          onChange={(event) => setColaboradorIdSelecionado(event.target.value)}
          options={usuarios.map((usuario) => ({ value: usuario.id, label: usuario.nome }))}
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
