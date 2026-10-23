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
    <div role="group" aria-label={rotulo} className="inline-flex rounded-xl border border-zinc-200 bg-zinc-50 p-1 dark:border-zinc-700 dark:bg-zinc-800">
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
                ? "inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-semibold text-fg shadow-sm dark:bg-zinc-950"
                : "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-fg-muted hover:text-zinc-800 dark:hover:text-zinc-200"
            }
          >
            <Icon className="h-4 w-4" />
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
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <label className="block flex-1 text-sm lg:max-w-sm">
          <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">Busca</span>
          <span className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fg-subtle" />
            <input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Buscar por tarefa, etapa, cliente ou projeto"
              className="field w-full rounded-xl py-2.5 pl-10 pr-3 text-sm"
            />
          </span>
        </label>

        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Período da pauta">
          <Button type="button" variant="secondary" onClick={onPeriodoAnterior} className="px-2.5 py-1.5" aria-label="Período anterior">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-[8.5rem] text-center text-sm font-medium text-fg">
            {periodoInicio && periodoFim ? `${formatarDiaMes(periodoInicio)} – ${formatarDiaMes(periodoFim)}` : "…"}
          </span>
          <Button type="button" variant="secondary" onClick={onPeriodoSeguinte} className="px-2.5 py-1.5" aria-label="Próximo período">
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button type="button" variant="secondary" onClick={onPeriodoHoje} className="px-3 py-1.5 text-xs">
            Hoje
          </Button>
        </div>
      </div>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0 flex-1">{filtrosAvancados}</div>

        <div className="flex flex-wrap items-center gap-2">
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
    </div>
  );
}
