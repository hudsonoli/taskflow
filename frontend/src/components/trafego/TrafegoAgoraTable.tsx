import { Badge } from "@/components/ui/Badge";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspaceTable } from "@/components/workspace/WorkspaceTable";
import {
  formatTempoOperacional,
  resolveTrafegoDemandaNome,
  resolveTrafegoDepartamentoNome,
  resolveTrafegoEtapaNome,
  resolveTrafegoUsuarioNome,
  statusTrafegoLabels,
} from "@/lib/trafego-mock";
import type { TrafegoAgoraItem } from "@/types/trafego";

type TrafegoAgoraTableProps = {
  sessions: TrafegoAgoraItem[];
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
  if (sessions.length === 0) {
    return (
      <WorkspaceEmptyState
        title="Nenhuma sessão em execução no momento."
        description="Ajuste os filtros ou aguarde novas movimentações de demandas."
      />
    );
  }

  return (
    <WorkspaceTable
      columns={[
        "Colaborador",
        "Departamento",
        "Demanda",
        "Etapa",
        "Início",
        "Tempo estimado",
        "Status",
      ]}
    >
      {sessions.map((session) => (
        <tr
          key={session.sessaoId}
          className="border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50"
        >
          <td className="px-6 py-4 font-medium text-zinc-900">
            {resolveTrafegoUsuarioNome(session.usuarioId)}
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {resolveTrafegoDepartamentoNome(session.departamentoId)}
          </td>
          <td className="px-6 py-4 text-zinc-900">
            {resolveTrafegoDemandaNome(session.demandaId)}
          </td>
          <td className="px-6 py-4 text-zinc-500">
            {resolveTrafegoEtapaNome(session.workflowEtapaId)}
          </td>
          <td className="px-6 py-4 font-mono text-zinc-500">
            {formatInicio(session.inicioEm)}
          </td>
          <td className="px-6 py-4 font-mono font-semibold tabular-nums text-zinc-900">
            {formatTempoOperacional(session.tempoDecorridoSegundos)}
          </td>
          <td className="px-6 py-4">
            <Badge>{statusTrafegoLabels[session.status]}</Badge>
          </td>
        </tr>
      ))}
    </WorkspaceTable>
  );
}
