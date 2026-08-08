import { Pencil, Workflow as WorkflowIcon } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { contarEtapasPorTipo } from "@/lib/workflow-modelos-mock";
import type { WorkflowModelo } from "@/types/workflow-modelo";

export function WorkflowsGrid({
  workflowModelos,
  onEdit,
}: {
  workflowModelos: WorkflowModelo[];
  onEdit: (modeloId: string) => void;
}) {
  if (workflowModelos.length === 0) {
    return <EmptyState title="Nenhum modelo de workflow encontrado" description="Ajuste a busca ou cadastre um novo modelo." />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {workflowModelos.map((modelo) => {
        const { execucao, aprovacao } = contarEtapasPorTipo(modelo);

        return (
          <div
            key={modelo.id}
            className={`flex flex-col gap-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 ${modelo.ativo ? "" : "opacity-60"}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                  <WorkflowIcon className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <p className="font-semibold text-zinc-950 dark:text-zinc-50">{modelo.nome}</p>
                  <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{modelo.etapas.length} etapa(s)</p>
                </div>
              </div>
              {modelo.ativo ? <Badge tone="green">Ativo</Badge> : <Badge tone="neutral">Inativo</Badge>}
            </div>

            <div className="flex flex-wrap gap-1.5">
              {modelo.etapas.map((etapa) => (
                <span
                  key={etapa.id}
                  className={
                    etapa.tipo === "aprovacao"
                      ? "rounded-full bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                      : "rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400"
                  }
                >
                  {etapa.nome}
                </span>
              ))}
            </div>

            <div className="flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-indigo-500" /> {execucao} execução
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-amber-500" /> {aprovacao} aprovação
              </span>
            </div>

            <Button variant="secondary" onClick={() => onEdit(modelo.id)} className="mt-1 self-start px-3 py-1.5 text-xs">
              <Pencil className="h-3.5 w-3.5" />
              Editar
            </Button>
          </div>
        );
      })}
    </div>
  );
}
