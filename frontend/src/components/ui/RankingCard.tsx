import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { EmptyState } from "@/components/ui/EmptyState";
import { Users } from "lucide-react";

export interface RankingItem {
  id: string;
  label: string;
  value: number;
  maxValue: number;
  displayValue: string;
  description: string;
  color: string;
  badge?: ReactNode;
}

export function RankingCard({
  title,
  description,
  items,
  emptyTitle,
  emptyDescription,
}: {
  title: string;
  description: string;
  items: RankingItem[];
  emptyTitle: string;
  emptyDescription: string;
}) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">{title}</h2>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{description}</p>

      <div className="mt-4">
        {items.length === 0 ? (
          <EmptyState title={emptyTitle} description={emptyDescription} icon={<Users size={16} />} />
        ) : (
          <ul className="flex flex-col gap-3">
            {items.map((item, index) => {
              const percent = item.maxValue > 0 ? Math.min(100, Math.round((item.value / item.maxValue) * 100)) : 0;
              return (
                <li key={item.id}>
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-zinc-800 dark:text-zinc-200">{item.label}</span>
                    <div className="flex shrink-0 items-center gap-2">
                      {item.badge}
                      <span className="font-mono text-sm font-semibold text-zinc-900 dark:text-zinc-100">{item.displayValue}</span>
                    </div>
                  </div>
                  <p className="mb-1.5 text-xs text-zinc-400">{item.description}</p>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${percent}%` }}
                      transition={{ duration: 0.4, delay: index * 0.04, ease: "easeOut" }}
                      className={`h-full rounded-full ${item.color}`}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
