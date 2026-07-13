import type { ReactNode } from "react";

type MetricCardTone = "neutral" | "blue" | "green" | "amber" | "red";

type MetricCardProps = {
  title: string;
  value: ReactNode;
  description?: string;
  icon?: ReactNode;
  tone?: MetricCardTone;
  badge?: ReactNode;
  footer?: ReactNode;
};

const toneClassNames: Record<MetricCardTone, string> = {
  neutral: "bg-zinc-100 text-zinc-700 ring-zinc-200",
  blue: "bg-blue-50 text-blue-700 ring-blue-100",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  amber: "bg-amber-50 text-amber-700 ring-amber-100",
  red: "bg-red-50 text-red-700 ring-red-100",
};

export function MetricCard({
  title,
  value,
  description,
  icon,
  tone = "neutral",
  badge,
  footer,
}: MetricCardProps) {
  return (
    <div className="group rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-zinc-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
            {title}
          </p>
          <div className="mt-3 text-3xl font-bold tracking-tight text-zinc-950">
            {value}
          </div>
        </div>

        {icon && (
          <div
            className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl ring-1 ${toneClassNames[tone]}`}
          >
            {icon}
          </div>
        )}
      </div>

      {(description || badge) && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {description && <p className="text-sm text-zinc-500">{description}</p>}
          {badge}
        </div>
      )}

      {footer && <div className="mt-4 border-t border-zinc-100 pt-3">{footer}</div>}
    </div>
  );
}
