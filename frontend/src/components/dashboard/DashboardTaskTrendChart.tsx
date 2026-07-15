import { DashboardWidget } from "./DashboardWidget";
import type { DashboardTaskTrendPoint } from "@/types/dashboard";

type DashboardTaskTrendChartProps = {
  data: DashboardTaskTrendPoint[];
};

type Serie = {
  key: keyof Pick<DashboardTaskTrendPoint, "criadas" | "concluidas" | "atrasadas">;
  label: string;
  colorClassName: string;
  strokeDasharray?: string;
};

// Três formas de diferenciar cada série além da cor (cor + traço +
// legenda textual) — não depende só de cor para identificar quem é quem.
const series: Serie[] = [
  { key: "criadas", label: "Criadas", colorClassName: "stroke-zinc-900" },
  { key: "concluidas", label: "Concluídas", colorClassName: "stroke-emerald-600", strokeDasharray: "5 3" },
  { key: "atrasadas", label: "Atrasadas", colorClassName: "stroke-red-500", strokeDasharray: "1.5 3" },
];

const VIEW_WIDTH = 300;
const VIEW_HEIGHT = 120;
const PADDING_Y = 10;

function buildPoints(data: DashboardTaskTrendPoint[], key: Serie["key"], maxValue: number) {
  if (data.length === 0) return "";

  const usableHeight = VIEW_HEIGHT - PADDING_Y * 2;
  const stepX = VIEW_WIDTH / Math.max(1, data.length - 1);

  return data
    .map((point, index) => {
      const x = index * stepX;
      const ratio = maxValue === 0 ? 0 : point[key] / maxValue;
      const y = VIEW_HEIGHT - PADDING_Y - ratio * usableHeight;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function formatDateLabel(iso: string) {
  const [, month, day] = iso.split("-");
  return `${day}/${month}`;
}

export function DashboardTaskTrendChart({ data }: DashboardTaskTrendChartProps) {
  const titleId = "dashboard-task-trend-title";
  const descriptionId = "dashboard-task-trend-description";

  const maxValue = data.reduce(
    (max, point) => Math.max(max, point.criadas, point.concluidas, point.atrasadas),
    0
  );

  const firstLabel = data[0] ? formatDateLabel(data[0].data) : "";
  const lastLabel = data[data.length - 1] ? formatDateLabel(data[data.length - 1].data) : "";

  return (
    <DashboardWidget title="Evolução das tarefas — últimos 30 dias">
      <h3 id={titleId} className="sr-only">
        Gráfico de evolução das tarefas nos últimos 30 dias
      </h3>
      <p id={descriptionId} className="sr-only">
        Compara, dia a dia nos últimos 30 dias, a quantidade de tarefas criadas, concluídas e
        atrasadas, para mostrar se o volume de entrada está maior que o de conclusão e se os
        atrasos estão aumentando ou diminuindo.
      </p>

      <svg
        role="img"
        aria-labelledby={`${titleId} ${descriptionId}`}
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        preserveAspectRatio="none"
        className="h-40 w-full"
      >
        <line
          x1={0}
          y1={VIEW_HEIGHT - PADDING_Y}
          x2={VIEW_WIDTH}
          y2={VIEW_HEIGHT - PADDING_Y}
          className="stroke-zinc-100"
          strokeWidth={1}
        />

        {series.map((serie) => (
          <polyline
            key={serie.key}
            points={buildPoints(data, serie.key, maxValue)}
            fill="none"
            className={serie.colorClassName}
            strokeWidth={2}
            strokeDasharray={serie.strokeDasharray}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}
      </svg>

      <div className="mt-1 flex justify-between text-[10px] text-zinc-400">
        <span>{firstLabel}</span>
        <span>{lastLabel}</span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
        {series.map((serie) => (
          <div key={serie.key} className="flex items-center gap-1.5 text-xs text-zinc-600">
            <svg width="14" height="4" aria-hidden="true">
              <line
                x1={0}
                y1={2}
                x2={14}
                y2={2}
                className={serie.colorClassName}
                strokeWidth={2}
                strokeDasharray={serie.strokeDasharray}
              />
            </svg>
            {serie.label}
          </div>
        ))}
      </div>
    </DashboardWidget>
  );
}
