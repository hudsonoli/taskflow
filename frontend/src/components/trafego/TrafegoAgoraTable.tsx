import { Activity, Inbox } from "lucide-react";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  formatTempoOperacional,
  resolveTrafegoDemandaNome,
  resolveTrafegoDepartamentoNome,
  resolveTrafegoEtapaNome,
  resolveTrafegoUsuarioNome,
  statusTrafegoLabels,
} from "@/lib/trafego-mock";
import type { TrafegoAgoraItem, TrafegoSessaoStatus } from "@/types/trafego";

type TrafegoAgoraTableProps = {
  sessions: TrafegoAgoraItem[];
};

const statusTone: Record<TrafegoSessaoStatus, "blue" | "amber" | "red" | "green"> = {
  ativa: "green",
  pausada: "amber",
  bloqueada: "red",
  aguardando_cliente: "blue",
};

function formatInicio(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TrafegoAgoraTable({ sessions }: TrafegoAgoraTableProps) {
  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm">
      <SectionHeader
        eyebrow="ao vivo"
        title="Quem está trabalhando agora"
        description="Sessões ativas ordenadas por maior tempo em execução."
        action={<StatusPill tone="green">{sessions.length} ativa(s)</StatusPill>}
      />

      <div className="mt-5">
        {sessions.length === 0 ? (
          <EmptyStateIllustration
            icon={<Inbox className="h-6 w-6" aria-hidden="true" />}
            title="Nenhuma sessão em execução no momento."
            description="Ajuste os filtros ou aguarde novas movimentações de demandas."
          />
        ) : (
          <div className="overflow-hidden rounded-3xl border border-zinc-100">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-100 bg-[#faf8f4] text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-400">
                  <tr>
                    <th className="px-4 py-3">Colaborador</th>
                    <th className="px-4 py-3">Demanda</th>
                    <th className="px-4 py-3">Etapa</th>
                    <th className="px-4 py-3">Início</th>
                    <th className="px-4 py-3 text-right">Tempo estimado</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((session) => (
                    <tr
                      key={session.sessaoId}
                      className="border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-zinc-950 text-white">
                            <Activity className="h-4 w-4" aria-hidden="true" />
                          </span>
                          <div>
                            <p className="font-semibold text-zinc-950">
                              {resolveTrafegoUsuarioNome(session.usuarioId)}
                            </p>
                            <p className="text-xs text-zinc-500">
                              {resolveTrafegoDepartamentoNome(session.departamentoId)}
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-medium text-zinc-900">
                        {resolveTrafegoDemandaNome(session.demandaId)}
                      </td>
                      <td className="px-4 py-3 text-zinc-500">
                        {resolveTrafegoEtapaNome(session.workflowEtapaId)}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-zinc-500">
                        {formatInicio(session.inicioEm)}
                      </td>
                      <td className="px-4 py-3 text-right font-mono font-bold tabular-nums text-zinc-950">
                        {formatTempoOperacional(session.tempoDecorridoSegundos)}
                      </td>
                      <td className="px-4 py-3">
                        <StatusPill tone={statusTone[session.status]}>
                          {statusTrafegoLabels[session.status]}
                        </StatusPill>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
