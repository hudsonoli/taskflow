import type { ReactNode } from "react";
import { EmptyStateIllustration } from "./EmptyStateIllustration";
import { ProgressBar } from "./ProgressBar";
import { SectionHeader } from "./SectionHeader";

type RankingCardItem = {
  id: string;
  label: string;
  value: number;
  displayValue: string;
  description?: string;
  color?: string;
  badge?: ReactNode;
};

type RankingCardProps = {
  title: string;
  description?: string;
  items: RankingCardItem[];
  emptyTitle?: string;
  emptyDescription?: string;
};

export function RankingCard({
  title,
  description,
  items,
  emptyTitle = "Nenhum dado encontrado",
  emptyDescription = "Não há informações suficientes para exibir este ranking.",
}: RankingCardProps) {
  const maxValue = Math.max(...items.map((item) => item.value), 1);

  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm">
      <SectionHeader title={title} description={description} />

      <div className="mt-5 space-y-4">
        {items.length === 0 ? (
          <EmptyStateIllustration title={emptyTitle} description={emptyDescription} />
        ) : (
          items.map((item) => {
            const percent = Math.max(2, Math.round((item.value / maxValue) * 100));

            return (
              <div key={item.id} className="rounded-2xl border border-zinc-100 p-3.5 transition hover:bg-zinc-50">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: item.color ?? "#2563eb" }}
                      />
                      <p className="truncate text-sm font-semibold text-zinc-950">
                        {item.label}
                      </p>
                    </div>
                    {item.description && (
                      <p className="mt-1 text-xs text-zinc-500">{item.description}</p>
                    )}
                  </div>

                  <div className="shrink-0 text-right">
                    <p className="font-mono text-sm font-bold tabular-nums text-zinc-950">
                      {item.displayValue}
                    </p>
                    {item.badge && <div className="mt-1">{item.badge}</div>}
                  </div>
                </div>

                <ProgressBar value={percent} className="mt-3" />
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
