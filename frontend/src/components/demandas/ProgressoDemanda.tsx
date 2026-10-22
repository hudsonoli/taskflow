"use client";

import { Check, CircleDot } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { estadoDoProgresso, resumoDoProgresso, segmentosDoProgresso, type EstadoSegmento } from "@/lib/progresso-demanda";
import type { Demanda } from "@/types/demanda";

const CLASSE_SEGMENTO: Record<EstadoSegmento, string> = {
  concluida: "bg-indigo-500 dark:bg-indigo-400",
  atual: "bg-indigo-200 ring-1 ring-inset ring-indigo-500 dark:bg-indigo-500/30 dark:ring-indigo-400",
  futura: "bg-zinc-200 dark:bg-zinc-700",
};

/**
 * Progresso compacto da tarefa (acompanhamento): barra segmentada (um segmento por etapa) + percentual textual + estado. Os números vêm do servidor
 * (`Demanda.progresso`); aqui só se desenha. Acessível: `role="progressbar"` com texto, e a lista de etapas aparece no foco/hover (sem depender de cor).
 */
export function ProgressoDemanda({ demanda }: { demanda: Demanda }) {
  const estado = estadoDoProgresso(demanda);
  const progresso = demanda.progresso;

  if (!estado.mostrarBarra || !progresso || progresso.percentual === null) {
    return (
      <span data-testid="progresso-demanda" className="inline-flex">
        <Badge tone={estado.rotulo === "Cancelada" ? "red" : "neutral"}>{estado.rotulo ?? "Sem fluxo"}</Badge>
      </span>
    );
  }

  const segmentos = segmentosDoProgresso(demanda);
  const resumo = resumoDoProgresso(progresso);
  const descricao = `${progresso.percentual}% — ${resumo}${progresso.etapaAtualNome ? `. Etapa atual: ${progresso.etapaAtualNome}` : ""}`;

  return (
    <div data-testid="progresso-demanda" className="group relative min-w-[120px] max-w-[170px]" tabIndex={0} aria-label={descricao}>
      <div className="flex items-center gap-2">
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progresso.percentual}
          aria-valuetext={descricao}
          className="flex h-2 min-w-0 flex-1 gap-0.5"
        >
          {segmentos.map((segmento) => (
            <span key={segmento.id} className={`h-full min-w-[3px] flex-1 rounded-full ${CLASSE_SEGMENTO[segmento.estado]}`} />
          ))}
        </div>
        <span className="w-9 shrink-0 text-right text-xs font-semibold tabular-nums text-fg">{progresso.percentual}%</span>
      </div>
      {estado.rotulo && (
        <div className="mt-1">
          <Badge tone="amber">{estado.rotulo}</Badge>
        </div>
      )}
      <div
        role="tooltip"
        className="pointer-events-none invisible absolute right-0 top-full z-20 mt-1.5 w-56 rounded-xl border border-line bg-surface p-3 text-xs opacity-0 shadow-lg transition group-hover:visible group-hover:opacity-100 group-focus:visible group-focus:opacity-100"
      >
        <p className="font-semibold text-fg">{resumo}</p>
        {progresso.etapaAtualNome && <p className="mt-0.5 text-fg-muted">Etapa atual: {progresso.etapaAtualNome}</p>}
        <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto">
          {segmentos.map((segmento) => (
            <li key={segmento.id} className="flex items-center gap-1.5 text-fg-muted">
              {segmento.estado === "concluida" ? (
                <Check className="h-3 w-3 shrink-0 text-indigo-600 dark:text-indigo-400" aria-label="concluída" />
              ) : segmento.estado === "atual" ? (
                <CircleDot className="h-3 w-3 shrink-0 text-indigo-600 dark:text-indigo-400" aria-label="etapa atual" />
              ) : (
                <span className="h-3 w-3 shrink-0" aria-hidden />
              )}
              <span className={`truncate ${segmento.estado === "atual" ? "font-semibold text-fg" : ""}`}>
                {segmento.nome}
                {segmento.estado === "atual" ? " · atual" : ""}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
