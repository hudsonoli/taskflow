"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { WorkspacePage } from "@/components/workspace/WorkspacePage";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";
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
      <PageHeader
        title="Central de Tráfego"
        description="Tempo Operacional Estimado"
      />

      <TrafegoHeader />

      <TrafegoFilters filters={filters} onChange={setFilters} />

      {loading ? (
        <div className="grid gap-5 md:grid-cols-3">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-32 animate-pulse rounded-3xl border border-zinc-100 bg-white shadow-sm"
            />
          ))}
        </div>
      ) : (
        <>
          <TrafegoResumoCards resumo={resumo} />

          <TempoOperacionalCard resumo={resumo} />

          <div className="grid gap-5 xl:grid-cols-2">
            <TrafegoCargaUsuarios cargas={cargaUsuarios} />
            <TrafegoCargaDepartamentos cargas={cargaDepartamentos} />
          </div>

          <WorkspaceSection
            title="Quem está trabalhando agora"
            description="Sessões ativas ordenadas por maior tempo em execução."
          >
            <TrafegoAgoraTable sessions={sessions} />
          </WorkspaceSection>
        </>
      )}
    </WorkspacePage>
  );
}
