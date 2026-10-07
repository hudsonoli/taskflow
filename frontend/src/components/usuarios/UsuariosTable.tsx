import { Pencil, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { estiloCorIdentificacao } from "@/lib/cores";
import { resolverDepartamentoNome } from "@/lib/referencias";
import { perfilUsuarioLabels } from "@/types/usuario";
import type { Usuario } from "@/types/usuario";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";

export function UsuariosTable({
  usuarios,
  departamentos,
  temMais = false,
  podeEditar,
  podeExcluir,
  onEdit,
  onExcluir,
}: {
  usuarios: Usuario[];
  departamentos: DepartamentoDiretorioItem[];
  /** Há mais páginas no servidor: o contador mostra o que está carregado, com "+". */
  temMais?: boolean;
  /** Autoridade do usuário logado SOBRE aquela linha (perfil + permissões da sessão): sem ela, a ação não aparece. */
  podeEditar: (usuario: Usuario) => boolean;
  podeExcluir: (usuario: Usuario) => boolean;
  onEdit: (usuarioId: string) => void;
  onExcluir: (usuarioId: string) => void;
}) {
  if (usuarios.length === 0) {
    return <EmptyState title="Nenhuma pessoa encontrada" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-fg">Equipe</h2>
          <p className="text-sm text-fg-muted">Pessoas com acesso ao workspace.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-fg-subtle">
          {usuarios.length}
          {temMais ? "+" : ""} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[960px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-fg-subtle dark:bg-zinc-950/40">
            <tr>
              <th className="px-4 py-2.5">Pessoa</th>
              <th className="px-4 py-2.5">Departamento</th>
              <th className="px-4 py-2.5">E-mail</th>
              <th className="px-4 py-2.5">Perfil</th>
              <th className="px-4 py-2.5">Situação</th>
              <th className="px-4 py-2.5">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {usuarios.map((usuario) => (
              <tr key={usuario.id} className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${usuario.ativo ? "" : "opacity-60"}`}>
                <td className="px-4 py-3">
                  {podeEditar(usuario) ? (
                    <button type="button" onClick={() => onEdit(usuario.id)} className="flex max-w-[240px] items-center gap-2.5 text-left">
                      <span
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                        style={estiloCorIdentificacao(usuario.corIdentificacao)}
                      >
                        {usuario.nome.slice(0, 2).toUpperCase()}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate font-semibold text-fg transition group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                          {usuario.nome}
                        </span>
                      </span>
                    </button>
                  ) : (
                    <div className="flex max-w-[240px] items-center gap-2.5">
                      <span
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white"
                        style={estiloCorIdentificacao(usuario.corIdentificacao)}
                      >
                        {usuario.nome.slice(0, 2).toUpperCase()}
                      </span>
                      <span className="block min-w-0 truncate font-semibold text-fg">{usuario.nome}</span>
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-fg-muted">
                  <span className="flex items-center gap-1.5">
                    {resolverDepartamentoNome(usuario.departamentoId, departamentos)}
                    {usuario.liderDepartamento && <Badge tone="blue">Head</Badge>}
                  </span>
                </td>
                <td className="px-4 py-3 max-w-[220px] truncate text-fg-muted" title={usuario.email}>
                  {usuario.email || "-"}
                </td>
                <td className="px-4 py-3">
                  <Badge tone="blue">{perfilUsuarioLabels[usuario.perfil]}</Badge>
                </td>
                <td className="px-4 py-3">
                  {usuario.ativo ? <Badge tone="green">Ativo</Badge> : <Badge tone="red">Inativo</Badge>}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    {podeEditar(usuario) && (
                      <Button variant="secondary" onClick={() => onEdit(usuario.id)} className="px-3 py-1.5 text-xs">
                        <Pencil className="h-3.5 w-3.5" />
                        Editar
                      </Button>
                    )}
                    {podeExcluir(usuario) && (
                      <Button variant="secondary" onClick={() => onExcluir(usuario.id)} className="px-3 py-1.5 text-xs">
                        <Trash2 className="h-3.5 w-3.5" />
                        Excluir
                      </Button>
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
