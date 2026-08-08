import { Archive, Pencil } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { resolveCorIdentificacaoHex } from "@/lib/cores";
import { resolverUsuarioPorReferencia } from "@/lib/referencias";
import type { DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import type { Equipe } from "@/types/equipe";

export function EquipesGrid({
  equipes,
  usuarios,
  onEdit,
  departamentos,
  onArquivar,
  onRestaurar,
}: {
  equipes: Equipe[];
  usuarios: UsuarioDiretorioItem[];
  onEdit: (equipeId: string) => void;
  departamentos: DepartamentoDiretorioItem[];
  onArquivar: (equipeId: string) => void;
  onRestaurar: (equipeId: string) => void;
}) {
  if (equipes.length === 0) {
    return <EmptyState title="Nenhuma equipe encontrada" description="Ajuste a busca ou cadastre uma nova equipe." />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {equipes.map((equipe) => {
        const lider = resolverUsuarioPorReferencia(equipe.liderId, usuarios);
        const membros = equipe.membroIds
          .map((id) => resolverUsuarioPorReferencia(id, usuarios))
          .filter((usuario): usuario is UsuarioDiretorioItem => Boolean(usuario));

        return (
          <div
            key={equipe.id}
            className={`flex flex-col gap-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 ${equipe.status === "ativo" ? "" : "opacity-60"}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl text-sm font-bold text-white"
                  style={{ backgroundColor: resolveCorIdentificacaoHex(equipe.corIdentificacao) }}
                >
                  {equipe.nome.trim().slice(0, 2).toUpperCase()}
                </span>
                <div className="min-w-0">
                  <p className="font-semibold text-zinc-950 dark:text-zinc-50">{equipe.nome}</p>
                  <p className="mt-0.5 line-clamp-2 text-xs text-zinc-500 dark:text-zinc-400">{equipe.descricao || "Sem descrição"}</p>
                  <p className="mt-1 text-[11px] font-medium text-zinc-400">
                    {/* Sem departamento = squad transversal. Deixar explícito evita ler
                        como cadastro incompleto. */}
                    {equipe.departamentoId
                      ? (departamentos.find((d) => d.id === equipe.departamentoId)?.nome ?? "Departamento removido")
                      : "Transversal"}
                  </p>
                </div>
              </div>
              {equipe.status === "ativo" ? (
                <Badge tone="green">Ativa</Badge>
              ) : equipe.status === "arquivado" ? (
                <Badge tone="neutral">Arquivada</Badge>
              ) : (
                <Badge tone="amber">Inativa</Badge>
              )}
            </div>

            <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-3 dark:border-zinc-800 dark:bg-zinc-950/30">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400">Líder</p>
              {lider ? (
                <div className="mt-1.5 flex items-center gap-2">
                  <Avatar nome={lider.nome} corIdentificacao={lider.corIdentificacao ?? "zinc"} fotoUrl={lider.fotoUrl} className="h-6 w-6 rounded-full text-[10px]" />
                  <span className="text-sm font-medium text-zinc-700 dark:text-zinc-200">{lider.nome}</span>
                </div>
              ) : (
                <p className="mt-1.5 text-sm text-zinc-400">Sem líder definido</p>
              )}
            </div>

            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-400">
                Membros ({membros.length})
              </p>
              <AvatarStack
                pessoas={membros.map((membro) => ({
                  id: membro.id,
                  nome: membro.nome,
                  corIdentificacao: membro.corIdentificacao,
                  fotoUrl: membro.fotoUrl,
                }))}
                max={4}
                size="h-8 w-8"
                emptyLabel="Nenhum membro adicionado"
              />
            </div>

            <div className="mt-1 flex items-center gap-2">
              {equipe.status === "arquivado" ? (
                <Button
                  variant="secondary"
                  onClick={() => onRestaurar(equipe.id)}
                  className="px-3 py-1.5 text-xs"
                >
                  Restaurar
                </Button>
              ) : (
                <>
                  <Button variant="secondary" onClick={() => onEdit(equipe.id)} className="px-3 py-1.5 text-xs">
                    <Pencil className="h-3.5 w-3.5" />
                    Editar
                  </Button>
                  <button
                    type="button"
                    onClick={() => onArquivar(equipe.id)}
                    aria-label={`Arquivar ${equipe.nome}`}
                    className="rounded-full p-1.5 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                  >
                    <Archive className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
