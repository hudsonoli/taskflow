import { Archive, Pencil } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { resolveCorIdentificacaoHex } from "@/lib/clientes-mock";
import { resolverUsuarioPorReferencia } from "@/lib/referencias";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import type { Departamento } from "@/types/departamento";

export function DepartamentosTable({
  departamentos,
  usuarios,
  onEdit,
  onArquivar,
  onRestaurar,
}: {
  departamentos: Departamento[];
  usuarios: UsuarioDiretorioItem[];
  onEdit: (departamentoId: string) => void;
  onArquivar: (departamentoId: string) => void;
  onRestaurar: (departamentoId: string) => void;
}) {
  if (departamentos.length === 0) {
    return <EmptyState title="Nenhum departamento encontrado" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Departamentos</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Setores da operação e seus responsáveis.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
          {departamentos.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[760px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              <th className="px-4 py-2.5">Departamento</th>
              <th className="px-4 py-2.5">Descrição</th>
              <th className="px-4 py-2.5">Responsável</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {departamentos.map((departamento) => {
              const responsavel = resolverUsuarioPorReferencia(departamento.responsavelId, usuarios);
              return (
                <tr key={departamento.id} className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${departamento.status === "ativo" ? "" : "opacity-60"}`}>
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => onEdit(departamento.id)} className="flex items-center gap-2.5 text-left">
                      <span
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                        style={{ backgroundColor: resolveCorIdentificacaoHex(departamento.corIdentificacao) }}
                      >
                        {departamento.nome.slice(0, 2).toUpperCase()}
                      </span>
                      <span className="font-semibold text-zinc-950 transition group-hover:text-indigo-600 dark:text-zinc-50 dark:group-hover:text-indigo-400">
                        {departamento.nome}
                      </span>
                    </button>
                  </td>
                  <td className="max-w-[320px] truncate px-4 py-3 text-zinc-500 dark:text-zinc-400" title={departamento.descricao}>
                    {departamento.descricao || "-"}
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{responsavel?.nome ?? "Sem responsável"}</td>
                  <td className="px-4 py-3">
                    {departamento.status === "ativo" ? (
                      <Badge tone="green">Ativo</Badge>
                    ) : departamento.status === "arquivado" ? (
                      <Badge tone="neutral">Arquivado</Badge>
                    ) : (
                      <Badge tone="amber">Inativo</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {departamento.status === "arquivado" ? (
                        <Button
                          variant="secondary"
                          onClick={() => onRestaurar(departamento.id)}
                          className="px-3 py-1.5 text-xs"
                        >
                          Restaurar
                        </Button>
                      ) : (
                        <>
                          <Button
                            variant="secondary"
                            onClick={() => onEdit(departamento.id)}
                            className="px-3 py-1.5 text-xs"
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            Editar
                          </Button>
                          <button
                            type="button"
                            onClick={() => onArquivar(departamento.id)}
                            aria-label={`Arquivar ${departamento.nome}`}
                            className="rounded-full p-1.5 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                          >
                            <Archive className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
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
