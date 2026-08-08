"use client";

import type { PontoLinha } from "@/lib/relatorios";

const CHART_HEIGHT = 200;
const PADDING_LEFT = 32;
const PADDING_BOTTOM = 24;
const PADDING_TOP = 16;
const PADDING_RIGHT = 12;

export function VolumeSemanalLine({ pontos }: { pontos: PontoLinha[] }) {
  const maxValue = Math.max(1, ...pontos.map((ponto) => ponto.value));
  const plotHeight = CHART_HEIGHT - PADDING_BOTTOM - PADDING_TOP;
  const width = 640;
  const plotWidth = width - PADDING_LEFT - PADDING_RIGHT;
  const stepX = pontos.length > 1 ? plotWidth / (pontos.length - 1) : 0;

  function xFor(index: number) {
    return PADDING_LEFT + index * stepX;
  }
  function yFor(value: number) {
    return PADDING_TOP + plotHeight - (value / maxValue) * plotHeight;
  }

  const linePath = pontos.map((ponto, index) => `${index === 0 ? "M" : "L"} ${xFor(index)} ${yFor(ponto.value)}`).join(" ");
  const areaPath = `${linePath} L ${xFor(pontos.length - 1)} ${PADDING_TOP + plotHeight} L ${xFor(0)} ${PADDING_TOP + plotHeight} Z`;

  const yTicks = [0, Math.ceil(maxValue / 2), maxValue];
  const lastIndex = pontos.length - 1;

  return (
    <div className="viz-root">
      <svg width="100%" height={CHART_HEIGHT} viewBox={`0 0 ${width} ${CHART_HEIGHT}`} role="img" aria-label="Volume de demandas em fluxo por semana">
        {yTicks.map((tick) => {
          const y = yFor(tick);
          return (
            <g key={tick}>
              <line x1={PADDING_LEFT} x2={width - PADDING_RIGHT} y1={y} y2={y} stroke="var(--viz-grid)" strokeWidth={1} />
              <text x={PADDING_LEFT - 8} y={y + 3} textAnchor="end" fontSize="10" fill="var(--viz-text-muted)">
                {tick}
              </text>
            </g>
          );
        })}

        <path d={areaPath} fill="var(--viz-series-1)" opacity={0.1} stroke="none" />
        <path d={linePath} fill="none" stroke="var(--viz-series-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

        {pontos.map((ponto, index) => {
          const isEdge = index === 0 || index === lastIndex;
          return (
            <g key={ponto.inicioSemana}>
              <circle cx={xFor(index)} cy={yFor(ponto.value)} r={4} fill="var(--viz-series-1)" stroke="var(--viz-surface)" strokeWidth={2}>
                <title>
                  Semana de {ponto.semanaLabel}: {ponto.value} demanda(s)
                </title>
              </circle>
              {isEdge && (
                <text x={xFor(index)} y={yFor(ponto.value) - 10} textAnchor="middle" fontSize="10" fill="var(--viz-text-secondary)">
                  {ponto.value}
                </text>
              )}
              {(index % 2 === 0 || isEdge) && (
                <text x={xFor(index)} y={CHART_HEIGHT - 6} textAnchor="middle" fontSize="9" fill="var(--viz-text-muted)">
                  {ponto.semanaLabel}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function VolumeSemanalTable({ pontos }: { pontos: PontoLinha[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400">
          <tr>
            <th className="py-2">Semana</th>
            <th className="py-2 text-right">Demandas criadas</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {pontos.map((ponto) => (
            <tr key={ponto.inicioSemana}>
              <td className="py-2 text-zinc-700 dark:text-zinc-300">{ponto.semanaLabel}</td>
              <td className="py-2 text-right font-semibold text-zinc-900 dark:text-zinc-100">{ponto.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
