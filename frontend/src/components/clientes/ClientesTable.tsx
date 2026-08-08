import { ArchiveRestore, Pencil, Trash2 } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { resolveCorIdentificacaoHex } from "@/lib/cores";
import { resolverGrupoClienteNomes, resolverUsuarioPorReferencia } from "@/lib/referencias";
import { statusClienteLabels, type Cliente, type ClienteStatus } from "@/types/cliente";
import type { GrupoClienteDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";

const statusTone: Record<ClienteStatus, BadgeTone> = {
  ativo: "green",
  suspenso: "amber",
  inativo: "neutral",
  arquivado: "red",
};

export function ClientesTable({
  clientes,
  grupos,
  usuarios,
  onEdit,
  onArquivar,
  onRestaurar,
}: {
  clientes: Cliente[];
  grupos: GrupoClienteDiretorioItem[];
  usuarios: UsuarioDiretorioItem[];
  onEdit: (clienteId: string) => void;
  onArquivar: (clienteId: string) => void;
  onRestaurar: (clienteId: string) => void;
}) {
  if (clientes.length === 0) {
    return <EmptyState title="Nenhum cliente encontrado" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Carteira de clientes</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Clientes, documentos, grupos e responsáveis.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
          {clientes.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1080px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              {["Código", "Cliente", "Documento", "Cidade/UF", "Grupo", "Responsável", "Status", "Ações"].map((column) => (
                <th key={column} className="px-4 py-2.5">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {clientes.map((cliente) => (
              <tr key={cliente.id} className="group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                <td className="px-4 py-3 font-semibold text-zinc-900 dark:text-zinc-100" title={cliente.codigoReferencia}>
                  #{cliente.sequencialReferencia}
                </td>
                <td className="px-4 py-3">
                  <button type="button" onClick={() => onEdit(cliente.id)} className="flex max-w-[240px] items-center gap-2.5 text-left">
                    <span
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                      style={{ backgroundColor: resolveCorIdentificacaoHex(cliente.corIdentificacao) }}
                    >
                      {cliente.nome.slice(0, 2).toUpperCase()}
                    </span>
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-zinc-950 transition group-hover:text-indigo-600 dark:text-zinc-50 dark:group-hover:text-indigo-400">
                        {cliente.nome}
                      </span>
                      <span className="mt-0.5 block truncate text-xs font-medium text-zinc-400">{cliente.razaoSocial || "—"}</span>
                    </span>
                  </button>
                </td>
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{cliente.documento || "-"}</td>
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                  {cliente.cidade ? `${cliente.cidade}${cliente.uf ? `/${cliente.uf}` : ""}` : "-"}
                </td>
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{resolverGrupoClienteNomes(cliente.grupoClienteIds, grupos)}</td>
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{cliente.responsavelComercialId
                    ? (resolverUsuarioPorReferencia(cliente.responsavelComercialId, usuarios)?.nome ?? "-")
                    : "-"}</td>
                <td className="px-4 py-3">
                  <Badge tone={statusTone[cliente.status]}>{statusClienteLabels[cliente.status]}</Badge>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {cliente.status === "arquivado" ? (
                      <Button variant="secondary" onClick={() => onRestaurar(cliente.id)} className="px-3 py-1.5 text-xs">
                        <ArchiveRestore className="h-3.5 w-3.5" />
                        Restaurar
                      </Button>
                    ) : (
                      <>
                        <Button variant="secondary" onClick={() => onEdit(cliente.id)} className="px-3 py-1.5 text-xs">
                          <Pencil className="h-3.5 w-3.5" />
                          Editar
                        </Button>
                        <Button variant="secondary" onClick={() => onArquivar(cliente.id)} className="px-3 py-1.5 text-xs">
                          <Trash2 className="h-3.5 w-3.5" />
                          Excluir
                        </Button>
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
