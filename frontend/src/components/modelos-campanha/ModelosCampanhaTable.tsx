import { Archive, Layers3, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import type { ModeloCampanha } from "@/types/modelo-campanha";

function formatarData(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function ModelosCampanhaTable({
  modelos,
  onEdit,
  onArquivar,
  onRestaurar,
}: {
  modelos: ModeloCampanha[];
  onEdit: (modeloId: string) => void;
  onArquivar: (modeloId: string) => void;
  onRestaurar: (modeloId: string) => void;
}) {
  if (modelos.length === 0) {
    return (
      <EmptyState
        title="Nenhum modelo de campanha encontrado"
        description="Ajuste a busca ou os filtros, ou crie um novo modelo."
        icon={<Layers3 size={16} />}
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Modelos de campanha</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Biblioteca reutilizável de estruturas de campanha.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">{modelos.length} registro(s)</span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[840px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              <th className="px-4 py-2.5">Nome</th>
              <th className="px-4 py-2.5">Descrição</th>
              <th className="px-4 py-2.5">Itens</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Atualizado em</th>
              <th className="px-4 py-2.5">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {modelos.map((modelo) => (
              <tr
                key={modelo.id}
                className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${
                  modelo.status === "ativo" ? "" : "opacity-60"
                }`}
              >
                <td className="px-4 py-3">
                  <button type="button" onClick={() => onEdit(modelo.id)} className="text-left">
                    <span className="font-semibold text-zinc-950 transition group-hover:text-indigo-600 dark:text-zinc-50 dark:group-hover:text-indigo-400">
                      {modelo.nome}
                    </span>
                  </button>
                </td>
                <td className="max-w-[280px] truncate px-4 py-3 text-zinc-500 dark:text-zinc-400" title={modelo.descricao ?? ""}>
                  {modelo.descricao || "-"}
                </td>
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{modelo.itens.length}</td>
                <td className="px-4 py-3">
                  {modelo.status === "ativo" ? (
                    <Badge tone="green">Ativo</Badge>
                  ) : modelo.status === "arquivado" ? (
                    <Badge tone="neutral">Arquivado</Badge>
                  ) : (
                    <Badge tone="amber">Inativo</Badge>
                  )}
                </td>
                <td className="px-4 py-3 text-zinc-500 dark:text-zinc-400">{formatarData(modelo.updatedAt)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {modelo.status === "arquivado" ? (
                      <Button variant="secondary" onClick={() => onRestaurar(modelo.id)} className="px-3 py-1.5 text-xs">
                        Restaurar
                      </Button>
                    ) : (
                      <>
                        <Button variant="secondary" onClick={() => onEdit(modelo.id)} className="px-3 py-1.5 text-xs">
                          <Pencil className="h-3.5 w-3.5" />
                          Editar
                        </Button>
                        <button
                          type="button"
                          onClick={() => onArquivar(modelo.id)}
                          aria-label={`Arquivar ${modelo.nome}`}
                          className="rounded-full p-1.5 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                        >
                          <Archive className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
