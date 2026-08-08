"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import type { FatiaPizza } from "@/lib/relatorios";
import { seriesColor } from "@/lib/vizPalette";

const SIZE = 200;
const STROKE = 30;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const GAP = 2;

export function DemandasPorProjetoDonut({
  fatias,
  emptyTitle = "Sem demandas em aberto",
  emptyDescription = "Nenhuma demanda em aberto encontrada para os projetos deste cliente.",
}: {
  fatias: FatiaPizza[];
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  const total = fatias.reduce((sum, fatia) => sum + fatia.value, 0);

  if (total === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  const segmentos = fatias.reduce<{ fatia: FatiaPizza; dash: number; offset: number }[]>((acc, fatia) => {
    const previous = acc[acc.length - 1];
    const cumulative = previous ? previous.offset + (previous.fatia.value / total) * CIRCUMFERENCE : 0;
    const length = (fatia.value / total) * CIRCUMFERENCE;
    acc.push({ fatia, dash: Math.max(0, length - GAP), offset: cumulative });
    return acc;
  }, []);

  return (
    <div className="viz-root flex flex-col items-center gap-6 sm:flex-row sm:justify-center">
      <div className="relative shrink-0" style={{ width: SIZE, height: SIZE }}>
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Demandas em aberto por projeto">
          <circle cx={SIZE / 2} cy={SIZE / 2} r={RADIUS} fill="none" stroke="var(--viz-grid)" strokeWidth={STROKE} />
          <g style={{ transform: "rotate(-90deg)", transformOrigin: "50% 50%" }}>
            {segmentos.map(({ fatia, dash, offset }, index) => (
              <circle
                key={fatia.id}
                cx={SIZE / 2}
                cy={SIZE / 2}
                r={RADIUS}
                fill="none"
                stroke={seriesColor(index)}
                strokeWidth={STROKE}
                strokeDasharray={`${dash} ${CIRCUMFERENCE - dash}`}
                strokeDashoffset={-offset}
              >
                <title>
                  {fatia.label}: {fatia.value} ({Math.round((fatia.value / total) * 100)}%)
                </title>
              </circle>
            ))}
          </g>
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{total}</span>
          <span className="text-xs text-zinc-500 dark:text-zinc-400">em aberto</span>
        </div>
      </div>

      <ul className="flex flex-col gap-2">
        {fatias.map((fatia, index) => (
          <li key={fatia.id} className="flex items-center gap-2.5 text-sm">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: seriesColor(index) }} />
            <span className="text-zinc-700 dark:text-zinc-300">{fatia.label}</span>
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">{fatia.value}</span>
            <span className="text-xs text-zinc-400">({Math.round((fatia.value / total) * 100)}%)</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DemandasPorProjetoTable({ fatias }: { fatias: FatiaPizza[] }) {
  const total = fatias.reduce((sum, fatia) => sum + fatia.value, 0);

  if (total === 0) {
    return <EmptyState title="Sem demandas em aberto" description="Nenhuma demanda em aberto para este cliente." />;
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">
        <tr>
          <th className="py-2">Projeto</th>
          <th className="py-2 text-right">Demandas abertas</th>
          <th className="py-2 text-right">%</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
        {fatias.map((fatia) => (
          <tr key={fatia.id}>
            <td className="py-2 text-zinc-700 dark:text-zinc-300">{fatia.label}</td>
            <td className="py-2 text-right font-semibold text-zinc-900 dark:text-zinc-100">{fatia.value}</td>
            <td className="py-2 text-right text-zinc-500 dark:text-zinc-400">{Math.round((fatia.value / total) * 100)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
