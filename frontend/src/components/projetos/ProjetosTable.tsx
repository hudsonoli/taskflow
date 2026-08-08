import { CalendarDays, Eye, Pencil } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  prioridadeProjetoLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  statusProjetoLabels,
} from "@/lib/projetos-mock";
import type { Projeto, ProjetoPrioridade, ProjetoStatus } from "@/types/projeto";

const statusTone: Record<ProjetoStatus, BadgeTone> = {
  planejamento: "blue",
  ativo: "green",
  pausado: "amber",
  concluido: "green",
  cancelado: "neutral",
};

const prioridadeClassName: Record<ProjetoPrioridade, string> = {
  alta: "border-zinc-300 bg-zinc-50 text-zinc-800 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200",
  media: "border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-400",
  baixa: "border-indigo-100 bg-indigo-50 text-indigo-600 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-400",
};

function splitResolvedNames(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function CompactList({ items }: { items: string[] }) {
  const visibleItems = items.slice(0, 2);
  const extraItems = items.length - visibleItems.length;

  return (
    <div className="flex max-w-[220px] flex-wrap gap-1.5">
      {visibleItems.map((item) => (
        <span
          key={item}
          className="inline-flex max-w-[140px] items-center rounded-full bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
          title={item}
        >
          <span className="truncate">{item}</span>
        </span>
      ))}
      {extraItems > 0 && (
        <span className="inline-flex items-center rounded-full bg-zinc-900 px-2 py-1 text-xs font-semibold text-white dark:bg-zinc-100 dark:text-zinc-900">
          +{extraItems}
        </span>
      )}
    </div>
  );
}

export function ProjetosTable({
  projetos,
  onOpenDetails,
  onEdit,
}: {
  projetos: Projeto[];
  onOpenDetails: (projetoId: string) => void;
  onEdit: (projetoId: string) => void;
}) {
  if (projetos.length === 0) {
    return <EmptyState title="Nenhum projeto encontrado" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Carteira de projetos</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Projetos, campanhas, responsáveis e prazos.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
          {projetos.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1180px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              {["Código", "Projeto", "Cliente", "Campanha", "Responsáveis", "Departamentos", "Status", "Prioridade", "Prazo", "Ações"].map(
                (column) => (
                  <th key={column} className="px-4 py-2.5">
                    {column}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {projetos.map((projeto) => {
              const responsaveis = splitResolvedNames(resolveResponsaveisProjetoNomes(projeto.responsavelIds));
              const departamentos = splitResolvedNames(resolveDepartamentosProjetoNomes(projeto.departamentoResponsavelIds));

              return (
                <tr key={projeto.id} className="group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                  <td className="px-4 py-3 font-semibold text-zinc-900 dark:text-zinc-100">{projeto.codigoInterno}</td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => onOpenDetails(projeto.id)}
                      className="max-w-[240px] text-left font-semibold text-zinc-950 transition hover:text-indigo-600 dark:text-zinc-50 dark:hover:text-indigo-400"
                    >
                      <span className="block truncate">{projeto.nome}</span>
                      <span className="mt-0.5 block truncate text-xs font-medium text-zinc-400">{projeto.id}</span>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{resolveClienteProjetoNome(projeto.clienteId)}</td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{projeto.campanha}</td>
                  <td className="px-4 py-3">
                    <CompactList items={responsaveis} />
                  </td>
                  <td className="px-4 py-3">
                    <CompactList items={departamentos} />
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={statusTone[projeto.status]}>{statusProjetoLabels[projeto.status]}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${prioridadeClassName[projeto.prioridade]}`}>
                      {prioridadeProjetoLabels[projeto.prioridade]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-400">
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {projeto.dataFimPrevista}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Button variant="secondary" onClick={() => onOpenDetails(projeto.id)} className="px-3 py-1.5 text-xs">
                        <Eye className="h-3.5 w-3.5" />
                        Detalhes
                      </Button>
                      <Button variant="secondary" onClick={() => onEdit(projeto.id)} className="px-3 py-1.5 text-xs">
                        <Pencil className="h-3.5 w-3.5" />
                        Editar
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
