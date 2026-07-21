import { Activity, Inbox } from "lucide-react";
import {
  CadastroTable,
  cadastroTableCellClassName,
  cadastroTableHeaderCellClassName,
  cadastroTableHeaderClassName,
  cadastroTableRowClassName,
} from "@/components/cadastros/CadastroTable";
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
    timeZone: "America/Sao_Paulo",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TrafegoAgoraTable({ sessions }: TrafegoAgoraTableProps) {
  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-4 shadow-sm">
      <SectionHeader
        eyebrow="ao vivo"
        title="Quem está trabalhando agora"
        description="Sessões ativas ordenadas por maior tempo em execução."
        action={<StatusPill tone="green">{sessions.length} ativa(s)</StatusPill>}
      />

      <div className="mt-4">
        {sessions.length === 0 ? (
          <EmptyStateIllustration
            icon={<Inbox className="h-6 w-6" aria-hidden="true" />}
            title="Nenhuma sessão em execução no momento."
            description="Ajuste os filtros ou aguarde novas movimentações de demandas."
          />
        ) : (
          <CadastroTable minWidth="760px">
            <thead className={cadastroTableHeaderClassName}>
              <tr>
                <th className={cadastroTableHeaderCellClassName}>Colaborador</th>
                <th className={cadastroTableHeaderCellClassName}>Demanda</th>
                <th className={cadastroTableHeaderCellClassName}>Etapa</th>
                <th className={cadastroTableHeaderCellClassName}>Início</th>
                <th className={`${cadastroTableHeaderCellClassName} text-right`}>Tempo estimado</th>
                <th className={cadastroTableHeaderCellClassName}>Status</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.sessaoId} className={cadastroTableRowClassName}>
                  <td className={cadastroTableCellClassName}>
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-2xl bg-zinc-950 text-white">
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
                  <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                    {resolveTrafegoDemandaNome(session.demandaId)}
                  </td>
                  <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                    {resolveTrafegoEtapaNome(session.workflowEtapaId)}
                  </td>
                  <td className={`${cadastroTableCellClassName} font-mono text-xs text-zinc-500`}>
                    {formatInicio(session.inicioEm)}
                  </td>
                  <td className={`${cadastroTableCellClassName} text-right font-mono font-bold tabular-nums text-zinc-950`}>
                    {formatTempoOperacional(session.tempoDecorridoSegundos)}
                  </td>
                  <td className={cadastroTableCellClassName}>
                    <StatusPill tone={statusTone[session.status]}>
                      {statusTrafegoLabels[session.status]}
                    </StatusPill>
                  </td>
                </tr>
              ))}
            </tbody>
          </CadastroTable>
        )}
      </div>
    </section>
  );
}
