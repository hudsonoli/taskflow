"use client";

import clsx from "clsx";
import { EmptyState } from "@/components/ui/EmptyState";
import type { BadgeTone } from "@/components/ui/Badge";
import { PrioridadeTag } from "@/components/demandas/PrioridadeTag";
import { statusDemandaTone } from "@/lib/demandas";
import { ehFimDeSemana, formatarDiaMes, listarDiasDoPeriodo, posicaoDaJanela, separarPorPlanejamento, type GrupoPauta } from "@/lib/pauta-operacional";
import type { DemandaStatus } from "@/types/demanda";
import type { PautaItem } from "@/types/pauta-operacional";
import { contextoDoItem, rotuloDeOrigem, rotuloDeResponsaveis, type PautaContexto } from "./pautaContexto";

const toneClassNames: Record<BadgeTone, string> = {
  neutral: "bg-zinc-400",
  blue: "bg-indigo-500",
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

const LARGURA_NOME = "w-72";
const LARGURA_DIA_PX = 34;

/**
 * Gantt da Pauta: UMA linha por ETAPA dentro de cada grupo (colaborador ou projeto). A barra usa SÓ `planejado_inicio`/`planejado_fim` da etapa (planejamento ≠ prazo); janela incompleta e
 * etapa sem planejamento não ganham barra — aparecem em seções próprias do grupo, sem data inventada. Barras sobrepostas do mesmo colaborador ficam visíveis em linhas vizinhas.
 */
export function PautaGantt({
  grupos,
  periodoInicio,
  periodoFim,
  hoje,
  contexto,
}: {
  grupos: GrupoPauta[];
  periodoInicio: string;
  periodoFim: string;
  hoje: string;
  contexto: PautaContexto;
}) {
  if (grupos.length === 0) {
    return <EmptyState title="Nenhuma etapa na pauta" description="Ajuste a busca ou os filtros para visualizar as etapas em aberto." />;
  }
  const dias = listarDiasDoPeriodo(periodoInicio, periodoFim);
  const grade = { gridTemplateColumns: `repeat(${dias.length}, minmax(${LARGURA_DIA_PX}px, 1fr))` };
  const indiceHoje = dias.indexOf(hoje);

  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      <div className="overflow-x-auto">
        <div style={{ minWidth: `${288 + dias.length * LARGURA_DIA_PX}px` }}>
          <div className="flex border-b border-zinc-100 dark:border-zinc-800">
            <div className={clsx(LARGURA_NOME, "sticky left-0 z-10 shrink-0 bg-surface px-4 py-2.5 text-xs font-semibold uppercase tracking-[0.12em] text-fg-subtle")}>
              {contexto.visao === "colaborador" ? "Colaborador / etapa" : "Projeto / etapa"}
            </div>
            <div className="grid flex-1" style={grade}>
              {dias.map((dia, indice) => (
                <div
                  key={dia}
                  className={clsx(
                    "border-l border-zinc-100 px-0.5 py-2.5 text-center text-[11px] font-medium text-fg-subtle dark:border-zinc-800",
                    ehFimDeSemana(dia) && "bg-zinc-50 dark:bg-zinc-800/40",
                    indice === indiceHoje && "bg-indigo-50/70 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400",
                  )}
                >
                  {formatarDiaMes(dia)}
                </div>
              ))}
            </div>
          </div>

          {grupos.map((grupo) => {
            const { planejadas, incompletas, naoPlanejadas } = separarPorPlanejamento(grupo.itens);
            const usuarioDoGrupo = grupo.tipo === "colaborador" ? grupo.chave : undefined;
            return (
              <section key={grupo.chave} aria-label={grupo.titulo} className="border-b border-zinc-200 last:border-b-0 dark:border-zinc-800">
                <div className="flex items-baseline gap-2 bg-zinc-50 px-4 py-2 dark:bg-zinc-800/50">
                  <h2 className={clsx("text-sm font-semibold", grupo.tipo === "sem-responsavel" || grupo.tipo === "sem-individual" ? "text-amber-700 dark:text-amber-400" : "text-fg")}>{grupo.titulo}</h2>
                  <span className="text-xs text-fg-subtle">
                    {grupo.itens.length} {grupo.itens.length === 1 ? "etapa" : "etapas"}
                  </span>
                </div>
                <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                  {planejadas.map((item) => (
                    <LinhaGantt key={item.etapaId} item={item} usuarioDoGrupo={usuarioDoGrupo} contexto={contexto} grade={grade} dias={dias} indiceHoje={indiceHoje} periodoInicio={periodoInicio} periodoFim={periodoFim} />
                  ))}
                  {incompletas.length > 0 && <SubtituloSecao texto={`Planejamento incompleto (${incompletas.length})`} />}
                  {incompletas.map((item) => (
                    <LinhaGantt key={item.etapaId} item={item} usuarioDoGrupo={usuarioDoGrupo} contexto={contexto} grade={grade} dias={dias} indiceHoje={indiceHoje} periodoInicio={periodoInicio} periodoFim={periodoFim} />
                  ))}
                  {naoPlanejadas.length > 0 && <SubtituloSecao texto={`Não planejadas (${naoPlanejadas.length})`} />}
                  {naoPlanejadas.map((item) => (
                    <LinhaGantt key={item.etapaId} item={item} usuarioDoGrupo={usuarioDoGrupo} contexto={contexto} grade={grade} dias={dias} indiceHoje={indiceHoje} periodoInicio={periodoInicio} periodoFim={periodoFim} />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function SubtituloSecao({ texto }: { texto: string }) {
  return <div className="bg-zinc-50/60 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.1em] text-fg-subtle dark:bg-zinc-800/30">{texto}</div>;
}

function LinhaGantt({
  item,
  usuarioDoGrupo,
  contexto,
  grade,
  dias,
  indiceHoje,
  periodoInicio,
  periodoFim,
}: {
  item: PautaItem;
  usuarioDoGrupo?: string;
  contexto: PautaContexto;
  grade: { gridTemplateColumns: string };
  dias: string[];
  indiceHoje: number;
  periodoInicio: string;
  periodoFim: string;
}) {
  const { planejamento } = item;
  const posicao = planejamento.estado === "planejado" ? posicaoDaJanela(planejamento.inicio, planejamento.fim, periodoInicio, periodoFim) : null;
  const responsaveis = rotuloDeResponsaveis(item, contexto, usuarioDoGrupo);
  const origem = rotuloDeOrigem(item);
  const sub = [item.etapaNome, contextoDoItem(item, contexto)].filter(Boolean).join(" · ");
  const janelaTexto = planejamento.estado === "planejado" ? `${formatarDiaMes(planejamento.inicio)} → ${formatarDiaMes(planejamento.fim)}` : null;
  const tom = statusDemandaTone[item.demandaStatus as DemandaStatus] ?? "neutral";

  return (
    <div className="flex items-stretch transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
      <button type="button" onClick={() => contexto.onOpenDetails(item.demandaId)} className={clsx(LARGURA_NOME, "sticky left-0 z-10 shrink-0 bg-surface px-4 py-2.5 text-left")} title={origem ? `${item.etapaNome} — ${origem}` : item.etapaNome}>
        <span className="flex items-center gap-1.5">
          {contexto.emExecucaoIds.has(item.demandaId) && <span className="inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-500" title="Em execução agora" aria-label="Em execução agora" />}
          <span className="min-w-0 flex-1 truncate text-sm font-semibold text-fg hover:text-indigo-600 dark:hover:text-indigo-400">
            <span className="mr-1 font-normal text-fg-subtle">{item.demandaIdentificador}</span>
            {item.demandaNome}
          </span>
          <PrioridadeTag prioridade={item.prioridade} />
        </span>
        <span className="mt-0.5 block truncate text-xs text-fg-subtle">{sub}</span>
        {responsaveis && <span className="block truncate text-xs text-fg-muted">{responsaveis}</span>}
      </button>

      <div className="relative grid flex-1 items-center py-2.5" style={grade}>
        {dias.map((dia, indice) =>
          ehFimDeSemana(dia) ? (
            <div key={dia} className="pointer-events-none absolute inset-y-0 bg-zinc-50/70 dark:bg-zinc-800/30" style={{ left: `${(indice / dias.length) * 100}%`, width: `${100 / dias.length}%` }} />
          ) : null,
        )}
        {indiceHoje >= 0 && <div className="pointer-events-none absolute inset-y-0 w-px bg-indigo-400/60" style={{ left: `${((indiceHoje + 0.5) / dias.length) * 100}%` }} />}
        {planejamento.estado === "planejado" ? (
          posicao ? (
            <div
              role="img"
              aria-label={`${item.etapaNome}: ${janelaTexto}`}
              title={`${item.etapaNome} — ${janelaTexto}`}
              style={{ gridColumn: `${posicao.colunaInicio} / ${posicao.colunaFim}`, gridRow: 1 }}
              className={clsx("relative h-3 min-w-0", toneClassNames[tom], posicao.cortadaAntes ? "rounded-l-none" : "rounded-l-full", posicao.cortadaDepois ? "rounded-r-none" : "rounded-r-full")}
            />
          ) : (
            <span className="px-2 text-xs italic text-fg-subtle" style={{ gridColumn: `1 / ${dias.length + 1}` }}>
              Planejada {janelaTexto} (fora do período)
            </span>
          )
        ) : planejamento.estado === "incompleto" ? (
          <span className="px-2 text-xs text-amber-700 dark:text-amber-400" style={{ gridColumn: `1 / ${dias.length + 1}` }}>
            Início: {formatarDiaMes(planejamento.inicio)} · Fim: não definido
          </span>
        ) : (
          <span className="px-2 text-xs italic text-fg-subtle" style={{ gridColumn: `1 / ${dias.length + 1}` }}>
            Sem janela planejada
          </span>
        )}
      </div>
    </div>
  );
}
