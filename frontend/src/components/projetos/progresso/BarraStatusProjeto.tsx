import type { ReactNode } from "react";
import clsx from "clsx";
import type { ResumoProjeto, SegmentoId } from "@/lib/projetos-progresso";

const COR: Record<SegmentoId, string> = {
  concluida: "bg-emerald-500",
  em_execucao: "bg-indigo-500",
  aguardando_cliente: "bg-amber-400",
  bloqueada: "bg-red-500",
  pausada: "bg-zinc-500 dark:bg-zinc-400",
  // "ainda não iniciada" = segmento VAZADO com contorno neutro (≥3:1 contra a trilha nos dois temas), distinto de "pausada" (cheio)
  planejada: "bg-surface ring-1 ring-inset ring-zinc-500",
};

/** Composição das tarefas do projeto por situação real. Além da cor: legenda em texto com a contagem e `title` em cada trecho. */
export function BarraStatusProjeto({ resumo, lateral }: { resumo: ResumoProjeto; /** alertas ao lado da barra (mesma linha) */ lateral?: ReactNode }) {
  const presentes = resumo.segmentos.filter((segmento) => segmento.quantidade > 0);
  if (resumo.total === 0) return null;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <div role="img" aria-label={`Tarefas por situação: ${presentes.map((s) => `${s.quantidade} ${s.rotulo.toLowerCase()}`).join(", ")}`} className="flex h-2 min-w-[8rem] flex-1 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
          {presentes.map((segmento) => (
            <span key={segmento.id} title={`${segmento.rotulo}: ${segmento.quantidade}`} className={clsx(COR[segmento.id], "h-full")} style={{ width: `${(segmento.quantidade / resumo.total) * 100}%` }} />
          ))}
        </div>
        {lateral}
      </div>
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-fg-muted">
        {presentes.map((segmento) => (
          <li key={segmento.id} className="flex items-center gap-1">
            <span className={clsx("h-2 w-2 rounded-full", COR[segmento.id])} aria-hidden />
            <span className="font-medium text-fg">{segmento.quantidade}</span> {segmento.rotulo.toLowerCase()}
          </li>
        ))}
      </ul>
    </div>
  );
}
