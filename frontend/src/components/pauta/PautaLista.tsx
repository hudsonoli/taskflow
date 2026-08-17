"use client";

import { Eye } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverProjetoNome, resolverUsuarioPorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";
import {
  compararPorAgenda,
  normalizarUsuarioId,
  statusDemandaLabels,
  statusDemandaTone,
} from "@/lib/demandas";
import type { Demanda } from "@/types/demanda";

const formatHora = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });
const formatDiaGrupo = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "2-digit", month: "long" });

function chaveDoDia(demanda: Demanda): string {
  const prazo = new Date(demanda.prazoEtapaAtual ?? "");
  if (Number.isNaN(prazo.getTime())) return "sem-prazo";
  return prazo.toISOString().slice(0, 10);
}

function tituloDoGrupo(chave: string): string {
  if (chave === "sem-prazo") return "Sem prazo definido";
  const data = new Date(`${chave}T00:00:00`);
  const titulo = formatDiaGrupo.format(data);
  return titulo.charAt(0).toUpperCase() + titulo.slice(1);
}

export function PautaLista({ demandas, onOpenDetails }: { demandas: Demanda[]; onOpenDetails: (demandaId: string) => void }) {
  const { usuarios } = useDiretorioUsuarios();
  const { projetos } = useDiretorioProjetos();

  if (demandas.length === 0) {
    return <EmptyState title="Nenhuma tarefa na pauta" description="Ajuste a busca ou os filtros para visualizar as tarefas do período." />;
  }

  const ordenadas = [...demandas].sort(compararPorAgenda);
  const grupos = new Map<string, Demanda[]>();
  for (const demanda of ordenadas) {
    const chave = chaveDoDia(demanda);
    const grupo = grupos.get(chave);
    if (grupo) grupo.push(demanda);
    else grupos.set(chave, [demanda]);
  }

  return (
    <div className="flex flex-col gap-5">
      {[...grupos.entries()].map(([chave, demandasDoDia]) => (
        <div key={chave} className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <div className="flex items-center justify-between border-b border-zinc-100 px-4 py-3 dark:border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">{tituloDoGrupo(chave)}</h2>
            <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
              {demandasDoDia.length} tarefa(s)
            </span>
          </div>

          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {demandasDoDia.map((demanda) => {
              const prazo = new Date(demanda.prazoEtapaAtual ?? "");
              const hora = Number.isNaN(prazo.getTime()) ? "—" : formatHora.format(prazo);
              const responsaveis = demanda.usuarioResponsavelIds
                .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));

              return (
                <li key={demanda.id} className="flex flex-wrap items-center gap-4 px-4 py-3 transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                  <span className="w-14 shrink-0 text-sm font-semibold tabular-nums text-zinc-500 dark:text-zinc-400">{hora}</span>

                  <button
                    type="button"
                    onClick={() => onOpenDetails(demanda.id)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <span className="block truncate font-semibold text-zinc-950 transition hover:text-indigo-600 dark:text-zinc-50 dark:hover:text-indigo-400">
                      {demanda.nome}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-zinc-400">
                      {rotuloDemanda(demanda)} · {resolverProjetoNome(demanda.projetoId, projetos)}
                    </span>
                  </button>

                  <AvatarStack
                    pessoas={responsaveis.map((usuario) => ({
                      id: usuario.id,
                      nome: usuario.nome,
                      corIdentificacao: usuario.corIdentificacao,
                      fotoUrl: usuario.fotoUrl,
                    }))}
                    max={3}
                    size="h-7 w-7"
                  />

                  <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>

                  <button
                    type="button"
                    onClick={() => onOpenDetails(demanda.id)}
                    aria-label={`Ver detalhes de ${demanda.nome}`}
                    className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
                  >
                    <Eye className="h-4 w-4" />
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
