import clsx from "clsx";
import { TEXTO_ESCOPO_AGORA, kpisDoAgora, type TomKpi } from "@/lib/trafego-operacional";
import type { AgoraKpis } from "@/types/trafego-operacional";

// Cor semântica só quando há o que olhar (zero é neutro); tokens/tons do design system existente (Badge/MetricCard), sem paleta nova.
const BORDA: Record<TomKpi, string> = {
  neutral: "border-line",
  blue: "border-line",
  amber: "border-amber-200 dark:border-amber-500/30",
  red: "border-red-200 dark:border-red-500/30",
};
const VALOR: Record<TomKpi, string> = {
  neutral: "text-fg",
  blue: "text-indigo-700 dark:text-indigo-400",
  amber: "text-amber-700 dark:text-amber-400",
  red: "text-red-700 dark:text-red-400",
};
const PONTO: Record<TomKpi, string> = {
  neutral: "bg-zinc-300 dark:bg-zinc-600",
  blue: "bg-indigo-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

/**
 * Cinco indicadores compactos do AGORA — números simples em blocos, sem gráficos. `kpis === null` é carregamento ("…", sem inventar zero); contagens do ESCOPO de triagem (ver tooltip).
 * Os quatro de triagem mostram só a contagem: o endpoint AGORA não traz as listas de atrasadas/vencem hoje/sem responsável/sem prazo, então não há drill-down nesta fase.
 */
export function TrafegoAgoraKpis({ kpis }: { kpis: AgoraKpis | null }) {
  const itens = kpis ? kpisDoAgora(kpis) : null;
  const rotulos = kpisDoAgora({ emExecucao: 0, atrasadas: 0, vencemHoje: 0, semResponsavel: 0, semPrazo: 0, semEtapaAtual: 0 });

  return (
    <ul aria-label="Indicadores do estado atual" title={TEXTO_ESCOPO_AGORA} className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-5">
      {rotulos.map((base, indice) => {
        const item = itens ? itens[indice] : base;
        const tom: TomKpi = itens ? item.tom : "neutral";
        return (
          <li key={base.id} className={clsx("rounded-xl border bg-surface px-3.5 py-3 shadow-sm", BORDA[tom])}>
            <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
              <span aria-hidden className={clsx("h-1.5 w-1.5 rounded-full", PONTO[tom])} />
              {base.label}
            </p>
            <p className={clsx("mt-1 text-2xl font-semibold tabular-nums tracking-tight", VALOR[tom])}>{itens ? item.valor : "…"}</p>
            <p className="mt-0.5 text-xs text-fg-subtle">{base.ajuda}</p>
          </li>
        );
      })}
    </ul>
  );
}
