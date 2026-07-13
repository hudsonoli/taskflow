import { Clock, TimerReset } from "lucide-react";
import { MetricCard } from "@/components/ui/MetricCard";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusPill } from "@/components/ui/StatusPill";
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
    <section className="rounded-3xl border border-zinc-100 bg-zinc-950 p-5 text-white shadow-sm">
      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr] xl:items-center">
        <div>
          <SectionHeader
            eyebrow="tempo operacional"
            title="Estimativa acumulada do período"
            description="Métrica operacional baseada nas movimentações de demandas."
            action={<StatusPill tone="blue">não é folha de ponto</StatusPill>}
          />

          <div className="mt-4 flex items-end gap-3">
            <p className="font-mono text-4xl font-bold tracking-tight text-white">
              {formatTempoOperacional(resumo.tempoOperacionalEstimadoSegundos)}
            </p>
            <Clock className="mb-2 h-5 w-5 text-zinc-400" aria-hidden="true" />
          </div>

          <p className="mt-2 text-sm text-zinc-400">
            De {formatDateTime(resumo.inicioPeriodo)} até{" "}
            {formatDateTime(resumo.fimPeriodo)}.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <MetricCard
            title="Média por sessão"
            value={formatTempoOperacional(resumo.tempoMedioSessaoSegundos)}
            description="Tempo estimado médio"
            tone="blue"
            icon={<TimerReset className="h-5 w-5" aria-hidden="true" />}
          />
          <MetricCard
            title="Maior sessão"
            value={formatTempoOperacional(resumo.maiorSessaoSegundos)}
            description="Pico do período"
            tone="amber"
            icon={<Clock className="h-5 w-5" aria-hidden="true" />}
          />
        </div>
      </div>
    </section>
  );
}
