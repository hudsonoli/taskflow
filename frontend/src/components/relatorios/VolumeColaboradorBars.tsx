"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import type { SerieBarraEmpilhada } from "@/lib/relatorios";
import { seriesColor } from "@/lib/vizPalette";

const CHART_HEIGHT = 220;
const BAR_WIDTH = 24;
const GAP_BETWEEN_BARS = 56;
const GAP_SEGMENT = 2;
const PADDING_LEFT = 32;
const PADDING_BOTTOM = 28;

export function VolumeColaboradorBars({ series }: { series: SerieBarraEmpilhada[] }) {
  const allColaboradores = Array.from(
    new Map(series.flatMap((serie) => serie.segmentos).map((segmento) => [segmento.seriesId, segmento.label])).entries(),
  );

  const maxTotal = Math.max(1, ...series.map((serie) => serie.segmentos.reduce((sum, segmento) => sum + segmento.value, 0)));
  const plotHeight = CHART_HEIGHT - PADDING_BOTTOM;
  const width = PADDING_LEFT + series.length * (BAR_WIDTH + GAP_BETWEEN_BARS);

  const hasData = series.some((serie) => serie.segmentos.length > 0);
  if (!hasData) {
    return <EmptyState title="Sem demandas cadastradas" description="Nenhum projeto tem demandas vinculadas a colaboradores ainda." />;
  }

  const yTicks = [0, Math.ceil(maxTotal / 2), maxTotal];

  return (
    <div className="viz-root">
      <svg width="100%" height={CHART_HEIGHT} viewBox={`0 0 ${width} ${CHART_HEIGHT}`} role="img" aria-label="Volume de demandas por projeto e colaborador">
        {yTicks.map((tick) => {
          const y = plotHeight - (tick / maxTotal) * plotHeight;
          return (
            <g key={tick}>
              <line x1={PADDING_LEFT} x2={width} y1={y} y2={y} stroke="var(--viz-grid)" strokeWidth={1} />
              <text x={PADDING_LEFT - 8} y={y + 3} textAnchor="end" fontSize="10" fill="var(--viz-text-muted)">
                {tick}
              </text>
            </g>
          );
        })}
        <line x1={PADDING_LEFT} x2={width} y1={plotHeight} y2={plotHeight} stroke="var(--viz-baseline)" strokeWidth={1} />

        {series.map((serie, serieIndex) => {
          const x = PADDING_LEFT + serieIndex * (BAR_WIDTH + GAP_BETWEEN_BARS) + GAP_BETWEEN_BARS / 2;
          const posicoes = serie.segmentos.reduce<{ y: number; segHeight: number }[]>((acc, segmento) => {
            const previous = acc[acc.length - 1];
            const cursor = previous ? previous.y - GAP_SEGMENT : plotHeight;
            const segHeight = Math.max(0, (segmento.value / maxTotal) * plotHeight - GAP_SEGMENT);
            acc.push({ y: cursor - segHeight, segHeight });
            return acc;
          }, []);

          return (
            <g key={serie.categoriaId}>
              {serie.segmentos.map((segmento, segmentoIndex) => {
                const colaboradorIndex = allColaboradores.findIndex(([id]) => id === segmento.seriesId);
                const { y, segHeight } = posicoes[segmentoIndex];

                return (
                  <rect key={segmento.seriesId} x={x} y={y} width={BAR_WIDTH} height={segHeight} rx={4} fill={seriesColor(colaboradorIndex)}>
                    <title>
                      {serie.categoria} · {segmento.label}: {segmento.value}
                    </title>
                  </rect>
                );
              })}
              <text
                x={x + BAR_WIDTH / 2}
                y={CHART_HEIGHT - 8}
                textAnchor="middle"
                fontSize="10"
                fill="var(--viz-text-secondary)"
              >
                {serie.categoria.length > 14 ? `${serie.categoria.slice(0, 13)}…` : serie.categoria}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
        {allColaboradores.map(([id, label], index) => (
          <span key={id} className="inline-flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-300">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: seriesColor(index) }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function VolumeColaboradorTable({ series }: { series: SerieBarraEmpilhada[] }) {
  const allColaboradores = Array.from(
    new Map(series.flatMap((serie) => serie.segmentos).map((segmento) => [segmento.seriesId, segmento.label])).entries(),
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">
          <tr>
            <th className="py-2">Projeto</th>
            {allColaboradores.map(([id, label]) => (
              <th key={id} className="py-2 text-right">
                {label}
              </th>
            ))}
            <th className="py-2 text-right">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {series.map((serie) => {
            const total = serie.segmentos.reduce((sum, segmento) => sum + segmento.value, 0);
            return (
              <tr key={serie.categoriaId}>
                <td className="py-2 text-zinc-700 dark:text-zinc-300">{serie.categoria}</td>
                {allColaboradores.map(([id]) => (
                  <td key={id} className="py-2 text-right text-zinc-600 dark:text-zinc-400">
                    {serie.segmentos.find((segmento) => segmento.seriesId === id)?.value ?? 0}
                  </td>
                ))}
                <td className="py-2 text-right font-semibold text-zinc-900 dark:text-zinc-100">{total}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
