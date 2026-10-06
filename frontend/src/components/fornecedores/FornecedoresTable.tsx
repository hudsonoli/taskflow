import { ArchiveRestore, Archive, Pencil } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { statusFornecedorLabels } from "@/lib/fornecedores";
import { estiloCorIdentificacao } from "@/lib/cores";
import type { Fornecedor, FornecedorStatus } from "@/types/fornecedor";

const statusTone: Record<FornecedorStatus, BadgeTone> = {
  ativo: "green",
  inativo: "neutral",
  arquivado: "red",
};

export function FornecedoresTable({
  fornecedores,
  onEdit,
  onArquivar,
  onRestaurar,
}: {
  fornecedores: Fornecedor[];
  onEdit: (fornecedorId: string) => void;
  onArquivar: (fornecedorId: string) => void;
  onRestaurar: (fornecedorId: string) => void;
}) {
  if (fornecedores.length === 0) {
    return <EmptyState title="Nenhum fornecedor encontrado" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-fg">Fornecedores</h2>
          <p className="text-sm text-fg-muted">Gráficas, produtoras, freelancers, mídia.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-fg-subtle">
          {fornecedores.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1060px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-fg-subtle dark:bg-zinc-950/40">
            <tr>
              <th className="px-4 py-2.5">Código</th>
              <th className="px-4 py-2.5">Fornecedor</th>
              <th className="px-4 py-2.5">Categoria</th>
              <th className="px-4 py-2.5">Documento</th>
              <th className="px-4 py-2.5">Contato</th>
              <th className="px-4 py-2.5">Cidade/UF</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {fornecedores.map((fornecedor) => {
              const arquivado = fornecedor.status === "arquivado";
              return (
                <tr
                  key={fornecedor.id}
                  className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${fornecedor.status !== "ativo" ? "opacity-60" : ""}`}
                >
                  {/* O número é o rótulo; o código completo (F26000001) fica no title. O UUID
                      nunca aparece. Ver lib/formatarReferencia.ts. */}
                  <td
                    className="px-4 py-3 font-semibold text-fg"
                    title={fornecedor.codigoReferencia}
                  >
                    #{fornecedor.sequencialReferencia}
                  </td>
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => onEdit(fornecedor.id)} className="flex max-w-[260px] items-center gap-2.5 text-left">
                      <span
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                        style={estiloCorIdentificacao(fornecedor.corIdentificacao)}
                      >
                        {fornecedor.nome.slice(0, 2).toUpperCase()}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-semibold text-fg transition group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                          {fornecedor.nome}
                        </span>
                      </span>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-fg-muted">{fornecedor.categoria || "-"}</td>
                  <td className="px-4 py-3 font-mono text-xs tabular-nums text-fg-muted">{fornecedor.documento || "-"}</td>
                  <td className="px-4 py-3 text-fg-muted">
                    {fornecedor.contatoNome ? `${fornecedor.contatoNome}${fornecedor.email ? ` · ${fornecedor.email}` : ""}` : fornecedor.email || "-"}
                  </td>
                  <td className="px-4 py-3 text-fg-muted">
                    {fornecedor.cidade ? `${fornecedor.cidade}${fornecedor.uf ? `/${fornecedor.uf}` : ""}` : "-"}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={statusTone[fornecedor.status]}>{statusFornecedorLabels[fornecedor.status]}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {arquivado ? (
                        <Button variant="secondary" onClick={() => onRestaurar(fornecedor.id)} className="px-3 py-1.5 text-xs">
                          <ArchiveRestore className="h-3.5 w-3.5" />
                          Restaurar
                        </Button>
                      ) : (
                        <>
                          <Button variant="secondary" onClick={() => onEdit(fornecedor.id)} className="px-3 py-1.5 text-xs">
                            <Pencil className="h-3.5 w-3.5" />
                            Editar
                          </Button>
                          {/* Arquivar = soft-delete permanente. Nunca há exclusão física. */}
                          <Button variant="secondary" onClick={() => onArquivar(fornecedor.id)} className="px-3 py-1.5 text-xs">
                            <Archive className="h-3.5 w-3.5" />
                            Arquivar
                          </Button>
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
