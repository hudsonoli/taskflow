"use client";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PrioridadeTag } from "@/components/demandas/PrioridadeTag";
import { statusDemandaLabels } from "@/lib/demandas";
import { formatarDiaMes, separarPorPlanejamento, type GrupoPauta } from "@/lib/pauta-operacional";
import type { DemandaStatus } from "@/types/demanda";
import type { PautaItem } from "@/types/pauta-operacional";
import { contextoDoItem, rotuloDeOrigem, rotuloDeResponsaveis, type PautaContexto } from "./pautaContexto";

function janelaDoItem(item: PautaItem): string {
  const { estado, inicio, fim } = item.planejamento;
  if (estado === "planejado") return `${formatarDiaMes(inicio)} → ${formatarDiaMes(fim)}`;
  if (estado === "incompleto") return `Início ${formatarDiaMes(inicio)} · fim não definido`;
  return "Sem janela planejada";
}

/** Lista da Pauta: as MESMAS etapas e os mesmos grupos do Gantt (colaborador ou projeto), em linhas — sem outra fonte de dados nem outra ordem. */
export function PautaLista({ grupos, contexto }: { grupos: GrupoPauta[]; contexto: PautaContexto }) {
  if (grupos.length === 0) {
    return <EmptyState title="Nenhuma etapa na pauta" description="Ajuste a busca ou os filtros para visualizar as etapas em aberto." />;
  }
  return (
    <div className="flex flex-col gap-5">
      {grupos.map((grupo) => {
        const { planejadas, incompletas, naoPlanejadas } = separarPorPlanejamento(grupo.itens);
        const usuarioDoGrupo = grupo.tipo === "colaborador" ? grupo.chave : undefined;
        return (
          <section key={grupo.chave} aria-label={grupo.titulo} className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
            <div className="flex items-baseline gap-2 border-b border-zinc-100 bg-zinc-50 px-4 py-2.5 dark:border-zinc-800 dark:bg-zinc-800/50">
              <h2 className="text-sm font-semibold text-fg">{grupo.titulo}</h2>
              <span className="text-xs text-fg-subtle">
                {grupo.itens.length} {grupo.itens.length === 1 ? "etapa" : "etapas"}
              </span>
            </div>
            <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {[...planejadas, ...incompletas, ...naoPlanejadas].map((item) => {
                const responsaveis = rotuloDeResponsaveis(item, contexto, usuarioDoGrupo);
                const origem = rotuloDeOrigem(item);
                return (
                  <li key={item.etapaId}>
                    <button type="button" onClick={() => contexto.onOpenDetails(item.demandaId)} className="grid w-full grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 px-4 py-3 text-left transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 md:grid-cols-[minmax(0,1fr)_minmax(0,16rem)_11rem_4.5rem]">
                      <span className="min-w-0">
                        <span className="flex items-center gap-2">
                          <span className="min-w-0 truncate text-sm font-semibold text-fg">
                            <span className="mr-1 font-normal text-fg-subtle">{item.demandaIdentificador}</span>
                            {item.demandaNome}
                          </span>
                          {contexto.emExecucaoIds.has(item.demandaId) && <Badge tone="green">Em execução agora</Badge>}
                        </span>
                        <span className="block truncate text-xs text-fg-subtle">
                          {item.etapaNome}
                          {item.etapaAtual ? " · etapa atual" : ""} · tarefa {(statusDemandaLabels[item.demandaStatus as DemandaStatus] ?? item.demandaStatus).toLowerCase()}
                        </span>
                      </span>
                      <span className="hidden min-w-0 md:block">
                        <span className="block truncate text-xs text-fg-muted">{contextoDoItem(item, contexto) || "Sem cliente / projeto"}</span>
                        <span className="block truncate text-xs text-fg-subtle" title={origem ?? undefined}>
                          {responsaveis ?? origem ?? ""}
                        </span>
                      </span>
                      <span className={item.planejamento.estado === "planejado" ? "text-xs font-medium text-fg" : "text-xs text-amber-700 dark:text-amber-400"}>{janelaDoItem(item)}</span>
                      <span className="justify-self-end"><PrioridadeTag prioridade={item.prioridade} /></span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
