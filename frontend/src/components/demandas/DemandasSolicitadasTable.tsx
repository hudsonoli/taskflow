"use client";

import { CalendarDays } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatPrazo, normalizarUsuarioId, statusDemandaLabels, statusDemandaTone } from "@/lib/demandas";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { resolverClienteNome, resolverDepartamentoNome, resolverProjetoNome, resolverUsuarioPorReferencia, rotuloDemanda } from "@/lib/referencias";
import { useUsuariosComIds } from "@/lib/useUsuariosComIds";
import type { Demanda } from "@/types/demanda";
import { ProgressoDemanda } from "./ProgressoDemanda";

/**
 * "Solicitadas por mim": visão de ACOMPANHAMENTO de quem criou as tarefas — o que foi pedido, em que etapa está, com quem está e quanto falta. Não é a fila operacional:
 * sem ações de edição, sem prioridade/PIT. O servidor devolve só as tarefas criadas pelo usuário autenticado, em qualquer etapa, responsável ou departamento.
 */
export function DemandasSolicitadasTable({ demandas, onOpenDetails }: { demandas: Demanda[]; onOpenDetails: (demandaId: string) => void }) {
  const { usuarios } = useUsuariosComIds(demandas.flatMap((demanda) => responsaveisAtuais(demanda)));
  const { projetos } = useDiretorioProjetos();
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();

  if (demandas.length === 0) {
    return <EmptyState title="Nenhuma solicitação encontrada" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-fg">Solicitadas por mim</h2>
          <p className="text-sm text-fg-muted">Acompanhe o que você pediu, da abertura à conclusão, mesmo depois de passar para outra etapa.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-fg-subtle">{demandas.length} registro(s)</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-fg-subtle dark:bg-zinc-950/40">
            <tr>
              {["Solicitação", "Cliente / Projeto", "Status", "Etapa atual", "Responsável atual", "Prazo", "Progresso"].map((coluna) => (
                <th key={coluna} className="px-3 py-2.5">
                  {coluna}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {demandas.map((demanda) => {
              const etapa = demanda.workflowEtapas.find((candidata) => candidata.id === demanda.etapaAtualId);
              const responsaveis = responsaveisAtuais(demanda)
                .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));
              const departamentoAtual = etapa?.departamentoResponsavelIds[0];

              return (
                <tr key={demanda.id} className="group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                  <td className="px-3 py-3">
                    <button
                      type="button"
                      onClick={() => onOpenDetails(demanda.id)}
                      className="flex max-w-[190px] flex-col text-left transition hover:text-indigo-600 dark:hover:text-indigo-400"
                    >
                      <span className="text-xs font-semibold text-fg-subtle">{rotuloDemanda(demanda)}</span>
                      <span className="truncate font-semibold text-fg">{demanda.nome}</span>
                    </button>
                  </td>
                  <td className="px-3 py-3 text-fg-muted">
                    <span className="block max-w-[120px] truncate">{demanda.clienteId ? resolverClienteNome(demanda.clienteId, clientes) : "Sem cliente"}</span>
                    <span className="block max-w-[120px] truncate text-xs text-fg-subtle">{resolverProjetoNome(demanda.projetoId, projetos)}</span>
                  </td>
                  <td className="px-3 py-3">
                    <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                  </td>
                  <td className="px-3 py-3 text-fg-muted">
                    {etapa ? (
                      <>
                        <span className="block max-w-[120px] truncate font-medium text-fg">{etapa.nome}</span>
                        {departamentoAtual && (
                          <span className="block max-w-[120px] truncate text-xs text-fg-subtle">{resolverDepartamentoNome(departamentoAtual, departamentos)}</span>
                        )}
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-3">
                    {responsaveis.length > 0 ? (
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
                    ) : (
                      <span className="text-fg-subtle">—</span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-fg-muted">
                    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-zinc-100 px-2 py-1 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {formatPrazo(demanda.prazoEtapaAtual)}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <ProgressoDemanda demanda={demanda} />
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

/** Responsáveis da ETAPA ATUAL (quem tem a bola agora); sem etapa atual, os da tarefa. */
function responsaveisAtuais(demanda: Demanda): string[] {
  const etapa = demanda.workflowEtapas.find((candidata) => candidata.id === demanda.etapaAtualId);
  return etapa && etapa.usuarioResponsavelIds.length > 0 ? etapa.usuarioResponsavelIds : demanda.usuarioResponsavelIds;
}
