"use client";

import { Search } from "lucide-react";
import { FiltrosAvancados } from "@/components/filtros/FiltrosAvancados";
import type { DefinicaoFiltro, FiltroAtivo } from "@/types/filtros";

/**
 * Barra de busca + filtros avançados de Arquivos. A busca por nome/demanda/cliente/projeto é um parâmetro à parte
 * (`search`); os filtros estruturados (cliente, projeto, demanda, tipo, status, remetente, data de envio) são chips editáveis.
 * Tudo roda no servidor, antes da paginação — nunca sobre o que já foi carregado.
 */
export function ArquivosFiltros({
  busca,
  onBuscaChange,
  definicoes,
  filtros,
  onFiltrosChange,
}: {
  busca: string;
  onBuscaChange: (busca: string) => void;
  definicoes: readonly DefinicaoFiltro[];
  filtros: readonly FiltroAtivo[];
  onFiltrosChange: (filtros: FiltroAtivo[]) => void;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" aria-hidden />
        <input
          type="search"
          value={busca}
          onChange={(event) => onBuscaChange(event.target.value)}
          placeholder="Buscar por nome, demanda, cliente ou projeto…"
          aria-label="Buscar arquivos"
          className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
        />
      </div>
      <FiltrosAvancados definicoes={definicoes} filtros={filtros} onChange={onFiltrosChange} />
    </div>
  );
}
