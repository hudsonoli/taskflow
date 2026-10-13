"use client";

import { Plus, Trash2 } from "lucide-react";
import clsx from "clsx";
import { DIAS_NOME, horasDoDia, MAX_PERIODOS_POR_DIA, ordenarPeriodos, sugerirNovoPeriodo } from "@/lib/expediente-periodos";
import type { DiaSemana, PeriodoExpediente } from "@/types/regra-expediente";

/**
 * Editor dos períodos de UM dia da semana: 0 períodos = Fechado; 1 ou mais = dia útil. Início/fim em campos de hora; a lista se reordena pelo início ao sair do
 * campo (enquanto se digita a ordem não muda, para a linha não "pular"). A validação (início < fim, sem sobreposição) é feita por quem usa — aqui só se mostra o erro.
 */
export function PeriodosDoDia({
  dia,
  periodos,
  erro,
  onChange,
}: {
  dia: DiaSemana;
  periodos: PeriodoExpediente[];
  erro?: string;
  onChange: (periodos: PeriodoExpediente[]) => void;
}) {
  const nome = DIAS_NOME[dia];
  const sugestao = sugerirNovoPeriodo(periodos);
  const horas = horasDoDia(periodos);

  function atualizar(indice: number, campo: keyof PeriodoExpediente, valor: string) {
    onChange(periodos.map((periodo, i) => (i === indice ? { ...periodo, [campo]: valor } : periodo)));
  }

  return (
    <div className="grid gap-2 border-b border-line py-3 last:border-b-0 sm:grid-cols-[7rem_minmax(0,1fr)] sm:items-start sm:gap-4">
      <div>
        <p className="text-sm font-semibold text-fg">{nome}</p>
        <p className="text-xs text-fg-muted">{periodos.length === 0 ? "Fechado" : `${horas} h de trabalho`}</p>
      </div>

      <div className="flex min-w-0 flex-col gap-2">
        {periodos.length === 0 && <p className="text-sm text-fg-subtle">Sem períodos — o dia fica fechado.</p>}
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        {periodos.map((periodo, indice) => (
          <div key={indice} className="flex items-center gap-2">
            <input
              type="time"
              value={periodo.inicio}
              aria-label={`${nome}: início do período ${indice + 1}`}
              onChange={(event) => atualizar(indice, "inicio", event.target.value)}
              onBlur={() => onChange(ordenarPeriodos(periodos))}
              className="field w-28 rounded-xl px-3 py-2 text-sm"
            />
            <span className="text-fg-subtle" aria-hidden>
              —
            </span>
            <input
              type="time"
              value={periodo.fim}
              aria-label={`${nome}: fim do período ${indice + 1}`}
              onChange={(event) => atualizar(indice, "fim", event.target.value)}
              onBlur={() => onChange(ordenarPeriodos(periodos))}
              className="field w-28 rounded-xl px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={() => onChange(periodos.filter((_, i) => i !== indice))}
              aria-label={`${nome}: remover período ${indice + 1}`}
              title="Remover período"
              className="rounded-lg p-2 text-fg-subtle transition hover:bg-surface-hover hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
            </button>
          </div>
        ))}

        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={!sugestao}
            onClick={() => sugestao && onChange([...periodos, sugestao])}
            title={sugestao ? "Adicionar período" : `Limite de ${MAX_PERIODOS_POR_DIA} períodos ou sem espaço no dia`}
            className={clsx(
              "inline-flex items-center gap-1 self-start rounded-full border border-dashed border-fg-subtle px-3 py-1 text-xs font-semibold text-fg-muted transition",
              "hover:border-fg hover:text-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:opacity-40",
            )}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden />
            período
          </button>
          {periodos.length > 0 && (
            <button
              type="button"
              onClick={() => onChange([])}
              className="text-xs font-medium text-fg-subtle underline-offset-2 hover:text-fg hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
            >
              Fechar o dia
            </button>
          )}
        </div>
        </div>

        {erro && (
          <p role="alert" className="text-xs font-medium text-red-600 dark:text-red-400">
            {erro}
          </p>
        )}
      </div>
    </div>
  );
}
