"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CalendarClock } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { useAppData } from "@/lib/AppDataContext";
import { resolveProjetoDemandaNome } from "@/lib/demandas-mock";
import { DemandaDetailsDrawer } from "@/components/demandas/DemandaDetailsDrawer";
import type { Demanda } from "@/types/demanda";
import { PautaGantt } from "./PautaGantt";
import { PautaLista } from "./PautaLista";
import { type PautaPeriodoFiltro, type PautaViewMode, PautaToolbar } from "./PautaToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function matchesQuery(demanda: Demanda, query: string) {
  if (!query.trim()) return true;
  const haystack = [demanda.nome, demanda.codigoInterno, demanda.pit ?? "", resolveProjetoDemandaNome(demanda.projetoId)].join(" ");
  return normalize(haystack).includes(normalize(query));
}

function periodoParaIntervalo(periodo: PautaPeriodoFiltro): { inicio: Date; fim: Date } {
  const inicio = new Date();
  inicio.setHours(0, 0, 0, 0);

  const dias = periodo === "hoje" ? 0 : periodo === "7d" ? 6 : 29;
  const fim = new Date(inicio);
  fim.setDate(fim.getDate() + dias);
  fim.setHours(23, 59, 59, 999);

  return { inicio, fim };
}

export function PautaView() {
  const router = useRouter();
  const { demandas, setDemandas, usuarioAtual, setDemandaParaAbrir } = useAppData();
  const [query, setQuery] = useState("");
  const [departamentoIds, setDepartamentoIds] = useState<string[]>([]);
  const [periodo, setPeriodo] = useState<PautaPeriodoFiltro>("7d");
  const [viewMode, setViewMode] = useState<PautaViewMode>("lista");
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);

  const { inicio: periodoInicio, fim: periodoFim } = useMemo(() => periodoParaIntervalo(periodo), [periodo]);

  const filteredDemands = useMemo(() => {
    return demandas.filter((demanda) => {
      const prazo = new Date(demanda.prazoEtapaAtual);
      const dentroDoPeriodo = !Number.isNaN(prazo.getTime()) && prazo >= periodoInicio && prazo <= periodoFim;
      const departamentoMatches =
        departamentoIds.length === 0 || demanda.departamentoResponsavelIds.some((id) => departamentoIds.includes(id));
      return dentroDoPeriodo && departamentoMatches && matchesQuery(demanda, query);
    });
  }, [demandas, periodoInicio, periodoFim, departamentoIds, query]);

  const selectedDemand = demandas.find((demanda) => demanda.id === selectedDemandId);

  function handleDemandChange(nextDemand: Demanda) {
    setDemandas((current) => current.map((demanda) => (demanda.id === nextDemand.id ? nextDemand : demanda)));
  }

  // Pauta não duplica o modal de edição — "Editar" leva para Tarefas com a tarefa já aberta.
  function handleEdit(demandaId: string) {
    setSelectedDemandId(null);
    setDemandaParaAbrir({ demandaId });
    router.push("/tarefas");
  }

  if (!usuarioAtual) return null;

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <CalendarClock className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Pauta</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Ordem das tarefas por prazo, para acompanhar o dia e preparar a reunião de pauta da equipe.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <PautaToolbar
        query={query}
        onQueryChange={setQuery}
        departamentoIds={departamentoIds}
        onDepartamentoIdsChange={setDepartamentoIds}
        periodo={periodo}
        onPeriodoChange={setPeriodo}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      {viewMode === "lista" ? (
        <PautaLista demandas={filteredDemands} onOpenDetails={setSelectedDemandId} />
      ) : (
        <PautaGantt demandas={filteredDemands} periodoInicio={periodoInicio} periodoFim={periodoFim} onOpenDetails={setSelectedDemandId} />
      )}

      <DemandaDetailsDrawer
        key={selectedDemand?.id}
        demanda={selectedDemand}
        onClose={() => setSelectedDemandId(null)}
        onEdit={handleEdit}
        onChange={handleDemandChange}
      />
    </div>
  );
}
