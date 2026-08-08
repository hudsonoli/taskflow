import { Clock, TimerReset } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { MetricCard } from "@/components/ui/MetricCard";
import { formatTempoOperacional } from "@/lib/trafego";
import type { TrafegoResumo } from "@/types/trafego";

export function TempoOperacionalCard({ resumo }: { resumo: TrafegoResumo }) {
  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5 text-white shadow-sm">
      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr] xl:items-center">
        <div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">Tempo operacional</p>
              <h3 className="mt-1 text-base font-semibold text-white">Estimativa acumulada do período</h3>
            </div>
            <Badge tone="blue">não é folha de ponto</Badge>
          </div>

          <div className="mt-4 flex items-end gap-3">
            <p className="font-mono text-4xl font-bold tracking-tight text-white">
              {formatTempoOperacional(resumo.tempoOperacionalEstimadoSegundos)}
            </p>
            <Clock className="mb-2 h-5 w-5 text-zinc-400" />
          </div>
          <p className="mt-2 text-sm text-zinc-400">Calculado a partir das sessões de trabalho reais do backend.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <MetricCard
            title="Média por sessão"
            value={formatTempoOperacional(resumo.tempoMedioSessaoSegundos)}
            description="Tempo estimado médio"
            tone="blue"
            icon={<TimerReset size={16} />}
          />
          <MetricCard
            title="Maior sessão"
            value={formatTempoOperacional(resumo.maiorSessaoSegundos)}
            description="Pico do período"
            tone="amber"
            icon={<Clock size={16} />}
          />
        </div>
      </div>
    </section>
  );
}
