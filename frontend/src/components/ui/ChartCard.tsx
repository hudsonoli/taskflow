"use client";

import { useState, type ReactNode } from "react";
import { BarChart3, Table2 } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function ChartCard({
  title,
  description,
  chart,
  table,
}: {
  title: string;
  description: string;
  chart: ReactNode;
  table: ReactNode;
}) {
  const [view, setView] = useState<"chart" | "table">("chart");

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">{title}</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
        </div>
        <Button
          variant="secondary"
          onClick={() => setView((current) => (current === "chart" ? "table" : "chart"))}
          className="shrink-0 px-3 py-1.5 text-xs"
        >
          {view === "chart" ? (
            <>
              <Table2 className="h-3.5 w-3.5" />
              Ver tabela
            </>
          ) : (
            <>
              <BarChart3 className="h-3.5 w-3.5" />
              Ver gráfico
            </>
          )}
        </Button>
      </div>
      {view === "chart" ? chart : table}
    </section>
  );
}
