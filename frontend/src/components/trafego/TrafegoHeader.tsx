import { Activity, RefreshCw, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { StatusPill } from "@/components/ui/StatusPill";

export function TrafegoHeader() {
  return (
    <div className="overflow-hidden rounded-3xl border border-zinc-100 bg-white shadow-sm">
      <div className="relative p-5 lg:p-6">
        <div className="absolute right-0 top-0 h-28 w-28 rounded-bl-full bg-blue-50" />

        <div className="relative flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2">
              <StatusPill tone="green">Atualizado agora</StatusPill>
              <StatusPill tone="blue">Operação em tempo estimado</StatusPill>
            </div>

            <div className="mt-4 flex items-start gap-3">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-3xl bg-zinc-950 text-white shadow-sm">
                <Activity className="h-6 w-6" aria-hidden="true" />
              </div>

              <div>
                <h2 className="text-2xl font-bold tracking-tight text-zinc-950">
                  Central de Tráfego
                </h2>
                <p className="mt-1 text-sm font-medium text-zinc-600">
                  Tempo Operacional Estimado
                </p>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
                  As métricas são estimadas com base nas movimentações das demandas e
                  não representam controle de jornada.
                </p>
              </div>
            </div>
          </div>

          <div className="relative flex flex-wrap items-center gap-2 lg:justify-end">
            <div className="rounded-2xl border border-zinc-100 bg-[#faf8f4] px-4 py-2.5 shadow-sm">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
                <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                Monitoramento
              </div>
              <p className="mt-1 text-sm font-semibold text-zinc-900">
                Somente leitura nesta fase
              </p>
            </div>

            <Button variant="secondary" disabled>
              <span className="inline-flex items-center gap-2">
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                Atualizar
              </span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
