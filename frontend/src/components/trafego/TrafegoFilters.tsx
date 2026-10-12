"use client";

import { Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import type { TrafegoFiltersState } from "@/types/trafego";

const PERIODOS: Array<{ value: TrafegoFiltersState["periodo"]; label: string }> = [
  { value: "hoje", label: "Hoje" },
  { value: "24h", label: "24h" },
  { value: "7d", label: "7 dias" },
  { value: "30d", label: "30 dias" },
];

/**
 * Filtros da Central de Tráfego na faixa superior: período (botões rápidos) e busca de Demanda, na mesma linha de Usuário/Demanda (a `TrafegoView` os
 * agrupa num só cartão; os filtros avançados em chips ficam logo abaixo). Os filtros estruturados rodam NO SERVIDOR (indicadores, carga e "quem está trabalhando agora" usam a mesma regra), então
 * os totais e a paginação já refletem o recorte — nada é filtrado só sobre a página carregada.
 */
export function TrafegoFilters({
  periodo,
  onPeriodoChange,
  demandaQuery,
  onDemandaQueryChange,
}: {
  periodo: TrafegoFiltersState["periodo"];
  onPeriodoChange: (periodo: TrafegoFiltersState["periodo"]) => void;
  demandaQuery: string;
  onDemandaQueryChange: (texto: string) => void;
}) {
  return (
    <div role="search" aria-label="Filtros operacionais" className="flex flex-[2_1_29rem] flex-wrap items-end gap-3">
      <div role="group" aria-label="Período" className="flex shrink-0 items-center gap-2">
        {PERIODOS.map((item) => (
          <Button
            key={item.value}
            type="button"
            variant={periodo === item.value ? "primary" : "secondary"}
            aria-pressed={periodo === item.value}
            onClick={() => onPeriodoChange(item.value)}
            className="px-3 py-2 text-xs"
          >
            {item.label}
          </Button>
        ))}
      </div>
      <div className="relative min-w-[12rem] max-w-full flex-1">
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
    </div>
  );
}
