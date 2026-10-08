"use client";

import { Search, SlidersHorizontal } from "lucide-react";
import { FiltrosAvancados } from "@/components/filtros/FiltrosAvancados";
import { Button } from "@/components/ui/Button";
import type { DefinicaoFiltro, FiltroAtivo } from "@/types/filtros";
import type { TrafegoFiltersState } from "@/types/trafego";

const PERIODOS: Array<{ value: TrafegoFiltersState["periodo"]; label: string }> = [
  { value: "hoje", label: "Hoje" },
  { value: "24h", label: "24h" },
  { value: "7d", label: "7 dias" },
  { value: "30d", label: "30 dias" },
];

/**
 * Filtros da Central de Tráfego: período (botões rápidos), busca de Demanda e os filtros avançados em chips.
 * Os filtros estruturados rodam NO SERVIDOR (indicadores, carga e "quem está trabalhando agora" usam a mesma regra), então
 * os totais e a paginação já refletem o recorte — nada é filtrado só sobre a página carregada.
 */
export function TrafegoFilters({
  periodo,
  onPeriodoChange,
  demandaQuery,
  onDemandaQueryChange,
  definicoes,
  filtros,
  onFiltrosChange,
}: {
  periodo: TrafegoFiltersState["periodo"];
  onPeriodoChange: (periodo: TrafegoFiltersState["periodo"]) => void;
  demandaQuery: string;
  onDemandaQueryChange: (texto: string) => void;
  definicoes: readonly DefinicaoFiltro[];
  filtros: readonly FiltroAtivo[];
  onFiltrosChange: (filtros: FiltroAtivo[]) => void;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <span className="bg-brand-gradient flex h-9 w-9 items-center justify-center rounded-xl">
            <SlidersHorizontal className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-fg">Filtros operacionais</p>
            <p className="text-xs text-fg-muted">Ajuste a visão sem alterar dados.</p>
          </div>
        </div>

        <div role="group" aria-label="Período" className="flex flex-wrap items-center gap-2">
          {PERIODOS.map((item) => (
            <Button
              key={item.value}
              type="button"
              variant={periodo === item.value ? "primary" : "secondary"}
              aria-pressed={periodo === item.value}
              onClick={() => onPeriodoChange(item.value)}
              className="px-3 py-1.5 text-xs"
            >
              {item.label}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" aria-hidden />
          <input
            type="search"
            value={demandaQuery}
            onChange={(event) => onDemandaQueryChange(event.target.value)}
            placeholder="Buscar demanda"
            aria-label="Buscar demanda"
            className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
          />
        </div>
        <FiltrosAvancados definicoes={definicoes} filtros={filtros} onChange={onFiltrosChange} />
      </div>
    </div>
  );
}
