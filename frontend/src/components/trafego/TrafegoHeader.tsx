import { Clock3, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";

export function TrafegoHeader() {
  return (
    <div className="rounded-3xl border border-zinc-100 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium text-zinc-500">
            <Clock3 className="h-4 w-4" aria-hidden="true" />
            <span>Atualizado agora</span>
          </div>

          <h2 className="mt-3 text-2xl font-bold text-zinc-900">
            Central de Tráfego
          </h2>

          <p className="mt-1 text-sm font-medium text-zinc-600">
            Tempo Operacional Estimado
          </p>

          <p className="mt-3 max-w-3xl text-sm text-zinc-500">
            As métricas são estimadas com base nas movimentações das demandas e
            não representam controle de jornada.
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
  );
}
