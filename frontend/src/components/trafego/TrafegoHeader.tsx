"use client";

import { useId } from "react";
import { Activity, Info, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/Button";
import { TEXTO_INFO_TRAFEGO } from "@/lib/trafego-ui";

/** Ícone "i" com tooltip discreto (hover E foco de teclado). Não ocupa espaço: o balão é `absolute` e sem eventos de ponteiro. */
function InfoTooltip({ texto }: { texto: string }) {
  const id = useId();
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        aria-label="Sobre a Central de Tráfego"
        aria-describedby={id}
        className="inline-flex h-5 w-5 items-center justify-center rounded-full text-fg-subtle transition hover:text-fg focus-visible:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
      >
        <Info className="h-4 w-4" aria-hidden />
      </button>
      <span
        id={id}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 w-64 -translate-x-1/2 rounded-lg border border-line bg-surface px-3 py-2 text-xs font-normal leading-5 text-fg-muted opacity-0 shadow-lg transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
      >
        {texto}
      </span>
    </span>
  );
}

export function TrafegoHeader({ onRefresh, refreshing }: { onRefresh: () => void; refreshing: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
      className="rounded-2xl border border-line bg-surface shadow-sm"
    >
      <div className="relative flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between lg:px-6">
        <div className="flex items-center gap-3">
          <div className="bg-brand-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-xl shadow-sm">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h2 className="text-2xl font-bold tracking-tight text-fg">Central de Tráfego</h2>
              <InfoTooltip texto={TEXTO_INFO_TRAFEGO} />
            </div>
            <p className="text-sm font-medium text-fg-muted">Tempo operacional em tempo real</p>
          </div>
        </div>

        <Button variant="secondary" onClick={onRefresh} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>
    </motion.div>
  );
}
