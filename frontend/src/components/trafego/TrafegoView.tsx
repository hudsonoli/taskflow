"use client";

import { useMemo, useState } from "react";
import { DashboardGrid } from "@/components/ui/DashboardGrid";
import { WorkspacePage } from "@/components/workspace/WorkspacePage";
import {
  EMPRESA_TRAFEGO_PADRAO_ID,
  getTrafegoAgora,
  getTrafegoCargaDepartamentos,
  getTrafegoCargaUsuarios,
  getTrafegoResumo,
} from "@/lib/trafego-mock";
import type { TrafegoFiltersState } from "@/types/trafego";
import { TempoOperacionalCard } from "./TempoOperacionalCard";
import { TrafegoAgoraTable } from "./TrafegoAgoraTable";
import { TrafegoCargaDepartamentos } from "./TrafegoCargaDepartamentos";
import { TrafegoCargaUsuarios } from "./TrafegoCargaUsuarios";
import { TrafegoFilters } from "./TrafegoFilters";
import { TrafegoHeader } from "./TrafegoHeader";
import { TrafegoResumoCards } from "./TrafegoResumoCards";

const initialFilters: TrafegoFiltersState = {
  empresaId: EMPRESA_TRAFEGO_PADRAO_ID,
  usuarioIds: [],
  departamentoIds: [],
  demandaQuery: "",
  status: "todos",
  periodo: "24h",
};

export function TrafegoView() {
  const [filters, setFilters] = useState<TrafegoFiltersState>(initialFilters);
  const [loading] = useState(false);

  const sessions = useMemo(() => getTrafegoAgora(filters), [filters]);
  const resumo = useMemo(() => getTrafegoResumo(filters), [filters]);
  const cargaUsuarios = useMemo(
    () => getTrafegoCargaUsuarios(filters),
    [filters]
  );
  const cargaDepartamentos = useMemo(
    () => getTrafegoCargaDepartamentos(filters),
    [filters]
  );

  return (
    <WorkspacePage>
      <TrafegoHeader />
      <TrafegoFilters filters={filters} onChange={setFilters} />

      {loading ? (
        <DashboardGrid columns="three">
          {[1, 2, 3].map((item) => (
            <div key={item} className="h-32 animate-pulse rounded-3xl border border-zinc-100 bg-white shadow-sm" />
          ))}
        </DashboardGrid>
      ) : (
        <>
          <TrafegoResumoCards resumo={resumo} />
          <TempoOperacionalCard resumo={resumo} />
          <TrafegoAgoraTable sessions={sessions} />

          <DashboardGrid columns="two">
            <TrafegoCargaUsuarios cargas={cargaUsuarios} />
            <TrafegoCargaDepartamentos cargas={cargaDepartamentos} />
          </DashboardGrid>
        </>
      )}
    </WorkspacePage>
  );
}
