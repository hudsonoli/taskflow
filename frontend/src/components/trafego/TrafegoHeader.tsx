"use client";

import { Activity, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export function TrafegoHeader({ onRefresh, refreshing }: { onRefresh: () => void; refreshing: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
      className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="relative p-5 lg:p-6">
        <div className="pointer-events-none absolute right-0 top-0 h-28 w-28 rounded-bl-full bg-indigo-50 dark:bg-indigo-500/10" />

        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="green">Dados reais</Badge>
              <Badge tone="blue">Motor de horas</Badge>
            </div>

            <div className="mt-4 flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm">
                <Activity className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-zinc-950 dark:text-zinc-50">Central de Tráfego</h2>
                <p className="mt-1 text-sm font-medium text-zinc-600 dark:text-zinc-300">Tempo operacional em tempo real</p>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
                  Sessões de trabalho abertas e encerradas via API, calculadas pelo motor de horas do backend.
                </p>
              </div>
            </div>
          </div>

          <Button variant="secondary" onClick={onRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
