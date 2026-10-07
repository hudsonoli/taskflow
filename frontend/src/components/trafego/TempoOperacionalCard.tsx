import { Clock, TimerReset } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { MetricCard } from "@/components/ui/MetricCard";
import { formatTempoOperacional } from "@/lib/trafego";
import type { TrafegoResumo } from "@/types/trafego";

/**
 * D2-D3C1 — agregados do servidor (ver `TrafegoResumoCards`): `resumo === null` é "carregando"
 * ("…"), `erro` é falha ("—"); zero confirmado aparece como "0min".
 */
export function TempoOperacionalCard({ resumo, erro }: { resumo: TrafegoResumo | null; erro?: string | null }) {
  const tempo = (segundos: number | undefined): string => {
    if (erro) return "—";
    if (resumo === null) return "…";
    return formatTempoOperacional(segundos ?? 0);
  };

  return (
    <section className="relative overflow-hidden rounded-2xl border border-line bg-surface-2 p-5 pl-6 text-fg shadow-sm">
      <span aria-hidden className="bg-brand-gradient absolute inset-y-0 left-0 w-1.5" />
      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr] xl:items-center">
        <div>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fg-subtle">Tempo operacional</p>
              <h3 className="mt-1 text-base font-semibold text-fg">Estimativa acumulada do período</h3>
            </div>
            <Badge tone="blue">não é folha de ponto</Badge>
          </div>

          <div className="mt-4 flex items-end gap-3">
            <p className="font-mono text-4xl font-bold tracking-tight text-fg">
              {tempo(resumo?.tempoOperacionalEstimadoSegundos)}
            </p>
            <Clock className="mb-2 h-5 w-5 text-fg-subtle" />
          </div>
          <p className="mt-2 text-sm text-fg-muted">Calculado a partir das sessões de trabalho reais do backend.</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <MetricCard
            title="Média por sessão"
            value={tempo(resumo?.tempoMedioSessaoSegundos)}
            description="Tempo estimado médio"
            tone="blue"
            icon={<TimerReset size={16} />}
          />
          <MetricCard
            title="Maior sessão"
            value={tempo(resumo?.maiorSessaoSegundos)}
            description="Pico do período"
            tone="amber"
            icon={<Clock size={16} />}
          />
        </div>
      </div>
    </section>
  );
}
