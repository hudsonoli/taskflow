"use client";

import type { ReactNode } from "react";
import { CalendarRange, ChevronLeft, ChevronRight, FolderKanban, List, Search, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { formatarDiaMes, type ModoPauta, type VisaoPauta } from "@/lib/pauta-operacional";

function Alternador<T extends string>({
  rotulo,
  valor,
  opcoes,
  onChange,
}: {
  rotulo: string;
  valor: T;
  opcoes: Array<{ value: T; label: string; icon: typeof List }>;
  onChange: (valor: T) => void;
}) {
  return (
    <div role="group" aria-label={rotulo} data-pauta="alternador" className="inline-flex rounded-lg border border-line bg-surface-2 p-0.5">
      {opcoes.map((opcao) => {
        const Icon = opcao.icon;
        const ativo = valor === opcao.value;
        return (
          <button
            key={opcao.value}
            type="button"
            aria-pressed={ativo}
            onClick={() => onChange(opcao.value)}
            className={
              ativo
                ? "inline-flex items-center gap-1.5 rounded-md bg-white px-2.5 py-1 text-xs font-semibold text-fg shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:bg-zinc-950"
                : "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium text-fg-muted hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            }
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
            {opcao.label}
          </button>
        );
      })}
    </div>
  );
}

export function PautaToolbar({
  query,
  onQueryChange,
  visao,
  onVisaoChange,
  modo,
  onModoChange,
  periodoInicio,
  periodoFim,
  onPeriodoAnterior,
  onPeriodoSeguinte,
  onPeriodoHoje,
  filtrosAvancados,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  visao: VisaoPauta;
  onVisaoChange: (value: VisaoPauta) => void;
  modo: ModoPauta;
  onModoChange: (value: ModoPauta) => void;
  periodoInicio: string | null;
  periodoFim: string | null;
  onPeriodoAnterior: () => void;
  onPeriodoSeguinte: () => void;
  onPeriodoHoje: () => void;
  /** Filtros avançados da Pauta (Colaborador, Departamento, Cliente, Projeto, Prioridade). */
  filtrosAvancados: ReactNode;
}) {
  return (
    <div data-pauta="toolbar" className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-line bg-surface p-2.5 shadow-sm">
      <label className="relative block w-full sm:w-64">
        <span className="sr-only">Busca</span>
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" aria-hidden />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Buscar por tarefa, etapa, cliente ou projeto"
          className="field w-full rounded-lg py-1.5 pl-9 pr-3 text-sm"
        />
      </label>

      <div className="min-w-0 flex-1 basis-56">{filtrosAvancados}</div>

      <div className="flex flex-wrap items-center gap-2 lg:ml-auto">
        <div className="flex items-center gap-1" role="group" aria-label="Período da pauta">
          <Button type="button" variant="secondary" onClick={onPeriodoAnterior} className="px-2 py-1.5" aria-label="Período anterior">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-[7.5rem] text-center text-xs font-medium tabular-nums text-fg">
            {periodoInicio && periodoFim ? `${formatarDiaMes(periodoInicio)} – ${formatarDiaMes(periodoFim)}` : "…"}
          </span>
          <Button type="button" variant="secondary" onClick={onPeriodoSeguinte} className="px-2 py-1.5" aria-label="Próximo período">
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button type="button" variant="secondary" onClick={onPeriodoHoje} className="px-3 py-1.5 text-xs">
            Hoje
          </Button>
        </div>
        <Alternador
          rotulo="Agrupar por"
          valor={visao}
          onChange={onVisaoChange}
          opcoes={[
            { value: "colaborador", label: "Colaborador", icon: Users },
            { value: "projeto", label: "Projeto", icon: FolderKanban },
          ]}
        />
        <Alternador
          rotulo="Apresentação"
          valor={modo}
          onChange={onModoChange}
          opcoes={[
            { value: "gantt", label: "Gantt", icon: CalendarRange },
            { value: "lista", label: "Lista", icon: List },
          ]}
        />
      </div>
    </div>
  );
}
