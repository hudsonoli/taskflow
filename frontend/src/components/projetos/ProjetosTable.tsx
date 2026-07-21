import { CalendarDays, Eye, Pencil } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { CompactList, splitResolvedNames } from "@/components/ui/CompactList";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  prioridadeProjetoLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  statusProjetoLabels,
} from "@/lib/projetos-mock";
import type { Projeto, ProjetoPrioridade, ProjetoStatus } from "@/types/projeto";

type ProjetosTableProps = {
  projetos: Projeto[];
  onOpenDetails: (projetoId: string) => void;
  onEdit: (projetoId: string) => void;
};

const statusTone: Record<ProjetoStatus, "neutral" | "blue" | "green" | "amber" | "red"> = {
  planejamento: "blue",
  ativo: "green",
  pausado: "amber",
  concluido: "green",
  cancelado: "neutral",
};

const prioridadeClassName: Record<ProjetoPrioridade, string> = {
  alta: "border-slate-300 bg-slate-50 text-slate-800",
  media: "border-sky-200 bg-sky-50 text-sky-700",
  baixa: "border-blue-100 bg-blue-50 text-blue-500",
};

export function ProjetosTable({
  projetos,
  onOpenDetails,
  onEdit,
}: ProjetosTableProps) {
  if (projetos.length === 0) {
    return (
      <EmptyStateIllustration
        title="Nenhum projeto encontrado"
        description="Ajuste a busca ou os filtros para visualizar os projetos cadastrados."
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-zinc-100 bg-white shadow-sm">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950">Carteira de projetos</h2>
          <p className="text-sm text-zinc-500">Projetos, campanhas, responsáveis e prazos em visão operacional.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
          {projetos.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1180px] w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-[11px] font-semibold uppercase tracking-[0.04em] text-zinc-500">
            <tr>
              {[
                "Código",
                "Projeto",
                "Cliente",
                "Campanha",
                "Responsáveis",
                "Departamentos",
                "Status",
                "Prioridade",
                "Prazo",
                "Ações",
              ].map((column) => (
                <th key={column} className="px-4 py-2.5">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {projetos.map((projeto) => {
              const responsaveis = splitResolvedNames(
                resolveResponsaveisProjetoNomes(projeto.responsavelIds)
              );
              const departamentos = splitResolvedNames(
                resolveDepartamentosProjetoNomes(
                  projeto.departamentoResponsavelIds
                )
              );

              return (
                <tr
                  key={projeto.id}
                  className="group transition hover:bg-zinc-50"
                >
                  <td className="px-4 py-3 font-semibold text-zinc-900">
                    {projeto.codigoInterno}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => onOpenDetails(projeto.id)}
                      className="max-w-[240px] text-left font-semibold text-zinc-950 transition hover:text-blue-700"
                    >
                      <span className="block truncate">{projeto.nome}</span>
                      <span className="mt-0.5 block truncate text-xs font-medium text-zinc-400">
                        {projeto.id}
                      </span>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">
                    {resolveClienteProjetoNome(projeto.clienteId)}
                  </td>
                  <td className="px-4 py-3 text-zinc-600">{projeto.campanha}</td>
                  <td className="px-4 py-3">
                    <CompactList items={responsaveis} />
                  </td>
                  <td className="px-4 py-3">
                    <CompactList items={departamentos} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusPill tone={statusTone[projeto.status]}>
                      {statusProjetoLabels[projeto.status]}
                    </StatusPill>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${prioridadeClassName[projeto.prioridade]}`}
                    >
                      {prioridadeProjetoLabels[projeto.prioridade]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {projeto.dataFimPrevista}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => onOpenDetails(projeto.id)}
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Abrir detalhes
                      </Button>
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => onEdit(projeto.id)}
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Editar mock
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
