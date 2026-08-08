export const VIZ_SERIES_VARS = [
  "var(--viz-series-1)",
  "var(--viz-series-2)",
  "var(--viz-series-3)",
  "var(--viz-series-4)",
  "var(--viz-series-5)",
  "var(--viz-series-6)",
  "var(--viz-series-7)",
  "var(--viz-series-8)",
];

export function seriesColor(index: number): string {
  return VIZ_SERIES_VARS[index % VIZ_SERIES_VARS.length];
}
