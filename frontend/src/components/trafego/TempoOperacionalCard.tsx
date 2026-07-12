import { Clock, TimerReset } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { formatTempoOperacional } from "@/lib/trafego-mock";
import type { TrafegoResumo } from "@/types/trafego";

type TempoOperacionalCardProps = {
  resumo: TrafegoResumo;
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TempoOperacionalCard({ resumo }: TempoOperacionalCardProps) {
  return (
    <Card>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium text-zinc-500">
            <TimerReset className="h-4 w-4" aria-hidden="true" />
            Tempo Operacional Estimado
          </div>

          <p className="mt-3 font-mono text-4xl font-bold tabular-nums text-zinc-900">
            {formatTempoOperacional(resumo.tempoOperacionalEstimadoSegundos)}
          </p>

          <p className="mt-2 text-sm text-zinc-500">
            Período de {formatDateTime(resumo.inicioPeriodo)} até{" "}
            {formatDateTime(resumo.fimPeriodo)}.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:min-w-[360px]">
          <div className="rounded-2xl border border-zinc-100 bg-[#faf8f4] p-4">
            <p className="text-xs font-medium uppercase text-zinc-500">
              Média por sessão
            </p>
            <p className="mt-2 font-mono text-xl font-bold tabular-nums text-zinc-900">
              {formatTempoOperacional(resumo.tempoMedioSessaoSegundos)}
            </p>
          </div>

          <div className="rounded-2xl border border-zinc-100 bg-[#faf8f4] p-4">
            <p className="text-xs font-medium uppercase text-zinc-500">
              Maior sessão
            </p>
            <p className="mt-2 font-mono text-xl font-bold tabular-nums text-zinc-900">
              {formatTempoOperacional(resumo.maiorSessaoSegundos)}
            </p>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Clock className="h-4 w-4 text-zinc-500" aria-hidden="true" />
        <Badge>Métrica estimada</Badge>
        <span className="text-xs text-zinc-500">
          Não representa controle de jornada ou folha de ponto.
        </span>
      </div>
    </Card>
  );
}
