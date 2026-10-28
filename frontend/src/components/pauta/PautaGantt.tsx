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

const LARGURA_DIA_PX = 34;
// Painel da esquerda (etapa + contexto): 20rem no desktop, 14rem em telas estreitas (a timeline rola por dentro, nunca a página). Uma variável CSS só, usada pelo cabeçalho, pelas linhas e pelo fundo.
const VARIAVEL_NOME = "w-[var(--pauta-nome)]";
const ALTURA_MINIMA_LINHA = "min-h-[46px]";

/**
 * Gantt da Pauta: UMA linha por ETAPA dentro de cada grupo (colaborador ou projeto). A barra usa SÓ `planejado_inicio`/`planejado_fim` da etapa (planejamento ≠ prazo); janela incompleta e
 * etapa sem planejamento não ganham barra — aparecem em seções próprias do grupo, sem data inventada. Barras sobrepostas do mesmo colaborador ficam visíveis em linhas vizinhas.
 *
 * Apresentação: UMA superfície (o card herda o material do tema; nada de blur por linha/célula). O fundo da timeline (fim de semana, hoje, divisórias por dia) é UMA camada para o corpo inteiro,
 * não uma por linha. Nenhum identificador técnico (UUID/id interno) chega até aqui — só nomes e o código funcional da tarefa (`#1`).
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
    <div data-superficie="pauta" className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
      <div className="max-h-[calc(100dvh-14rem)] min-h-64 overflow-auto [--pauta-nome:14rem] sm:[--pauta-nome:20rem]">
        <div className="relative" style={{ minWidth: `calc(var(--pauta-nome) + ${dias.length * LARGURA_DIA_PX}px)` }}>
          {/* cabeçalho: fixo no topo ao rolar na vertical e, na horizontal, a coluna de nomes fica presa à esquerda */}
          <div data-pauta="cabecalho" className="sticky top-0 z-20 flex border-b border-line bg-surface">
            <div className={clsx(VARIAVEL_NOME, "sticky left-0 z-10 flex shrink-0 items-center border-r border-line bg-surface px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-fg-subtle")}>
              {contexto.visao === "colaborador" ? "Colaborador / etapa" : "Projeto / etapa"}
            </div>
            <div className="grid flex-1" style={grade}>
              {dias.map((dia, indice) => (
                <div
                  key={dia}
                  data-hoje={indice === indiceHoje ? "" : undefined}
                  className={clsx(
                    "px-0.5 py-1.5 text-center text-[11px] font-medium tabular-nums text-fg-subtle",
                    ehFimDeSemana(dia) && "bg-zinc-50 dark:bg-zinc-800/40",
                    indice === indiceHoje && "bg-indigo-50/70 font-semibold text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400",
                  )}
                >
                  {formatarDiaMes(dia)}
                </div>
              ))}
            </div>
          </div>

          {/* camada única da timeline: divisórias leves por dia, fim de semana e hoje — atrás de todas as linhas */}
          <div aria-hidden className="pointer-events-none absolute inset-y-0 right-0 left-[var(--pauta-nome)] grid" style={grade}>
            {dias.map((dia, indice) => (
              <div
                key={dia}
                className={clsx(
                  "border-l border-line/60",
                  ehFimDeSemana(dia) && "bg-zinc-500/[0.045]",
                  indice === indiceHoje && "relative bg-indigo-500/[0.07] after:absolute after:inset-y-0 after:left-1/2 after:w-px after:bg-indigo-400/50",
                )}
              />
            ))}
          </div>

          {grupos.map((grupo) => {
            const { planejadas, incompletas, naoPlanejadas } = separarPorPlanejamento(grupo.itens);
            const usuarioDoGrupo = grupo.tipo === "colaborador" ? grupo.chave : undefined;
            const linha = (item: PautaItem) => (
              <LinhaGantt key={item.etapaId} item={item} usuarioDoGrupo={usuarioDoGrupo} contexto={contexto} grade={grade} dias={dias} periodoInicio={periodoInicio} periodoFim={periodoFim} />
            );
            return (
              <section key={grupo.chave} aria-label={grupo.titulo} className="relative border-b border-line last:border-b-0">
                <div data-pauta="grupo" className="relative z-[1] flex items-baseline gap-1.5 border-b border-line bg-surface-2 px-3 py-1.5">
                  <h2 className={clsx("sticky left-3 text-[13px] font-semibold", grupo.tipo === "sem-responsavel" || grupo.tipo === "sem-individual" ? "text-amber-700 dark:text-amber-400" : "text-fg")}>{grupo.titulo}</h2>
                  <span className="sticky left-3 text-xs text-fg-subtle">
                    · {grupo.itens.length} {grupo.itens.length === 1 ? "etapa" : "etapas"}
                  </span>
                </div>
                <div className="relative z-[1] divide-y divide-line/70">
                  {planejadas.map(linha)}
                  {incompletas.length > 0 && <SubtituloSecao texto={`Planejamento incompleto · ${incompletas.length}`} />}
                  {incompletas.map(linha)}
                  {naoPlanejadas.length > 0 && <SubtituloSecao texto={`Não planejadas · ${naoPlanejadas.length}`} />}
                  {naoPlanejadas.map(linha)}
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
  return (
    <div data-pauta="secao" className="border-b border-line/70 px-3 py-0.5 text-[11px] font-medium text-fg-subtle">
      <span className="sticky left-3">{texto}</span>
    </div>
  );
}

function LinhaGantt({
  item,
  usuarioDoGrupo,
  contexto,
  grade,
  dias,
  periodoInicio,
  periodoFim,
}: {
  item: PautaItem;
  usuarioDoGrupo?: string;
  contexto: PautaContexto;
  grade: { gridTemplateColumns: string };
  dias: string[];
  periodoInicio: string;
  periodoFim: string;
}) {
  const { planejamento } = item;
  const posicao = planejamento.estado === "planejado" ? posicaoDaJanela(planejamento.inicio, planejamento.fim, periodoInicio, periodoFim) : null;
  const responsaveis = rotuloDeResponsaveis(item, contexto, usuarioDoGrupo);
  const origem = rotuloDeOrigem(item);
  const ondeFica = contextoDoItem(item, contexto);
  const janelaTexto = planejamento.estado === "planejado" ? `${formatarDiaMes(planejamento.inicio)} → ${formatarDiaMes(planejamento.fim)}` : null;
  const tom = statusDemandaTone[item.demandaStatus as DemandaStatus] ?? "neutral";
  // O texto completo (que a linha trunca) fica no tooltip: etapa, tarefa, cliente/projeto e responsabilidade. Nada técnico.
  const detalhe = [`${item.etapaNome}`, `${item.demandaIdentificador} ${item.demandaNome}`, ondeFica, responsaveis, origem].filter(Boolean).join(" — ");

  return (
    <div data-pauta="linha" className={clsx("flex items-stretch transition-colors hover:bg-indigo-500/[0.05]", ALTURA_MINIMA_LINHA)}>
      <button
        type="button"
        onClick={() => contexto.onOpenDetails(item.demandaId)}
        className={clsx(VARIAVEL_NOME, "group sticky left-0 z-10 flex shrink-0 flex-col justify-center gap-0.5 border-r border-line bg-surface px-3 py-1.5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus")}
        title={detalhe}
      >
        <span className="flex min-w-0 items-center gap-1.5">
          {contexto.emExecucaoIds.has(item.demandaId) && <span className="inline-block h-2 w-2 shrink-0 rounded-full bg-emerald-500" title="Em execução agora" aria-label="Em execução agora" />}
          <span className="min-w-0 truncate text-[13px] font-semibold leading-4 text-fg group-hover:text-indigo-600 dark:group-hover:text-indigo-400">{item.etapaNome}</span>
          <PrioridadeTag prioridade={item.prioridade} />
        </span>
        <span className="block truncate text-[11px] leading-4 text-fg-subtle">
          <span className="mr-1">{item.demandaIdentificador}</span>
          {item.demandaNome}
          {responsaveis && <span className="text-fg-muted"> · {responsaveis}</span>}
        </span>
      </button>

      <div className="relative grid flex-1 items-center py-1.5" style={grade}>
        {planejamento.estado === "planejado" ? (
          posicao ? (
            <div
              role="img"
              aria-label={`${item.etapaNome}: ${janelaTexto}`}
              title={`${item.etapaNome} — ${janelaTexto}`}
              style={{ gridColumn: `${posicao.colunaInicio} / ${posicao.colunaFim}`, gridRow: 1 }}
              className={clsx("relative h-2.5 min-w-0", toneClassNames[tom], posicao.cortadaAntes ? "rounded-l-none" : "rounded-l-full", posicao.cortadaDepois ? "rounded-r-none" : "rounded-r-full")}
            />
          ) : (
            <span className="px-2 text-[11px] italic text-fg-subtle" style={{ gridColumn: `1 / ${dias.length + 1}` }}>
              Planejada {janelaTexto} (fora do período)
            </span>
          )
        ) : planejamento.estado === "incompleto" ? (
          <span className="px-2 text-[11px] text-amber-700 dark:text-amber-400" style={{ gridColumn: `1 / ${dias.length + 1}` }}>
            Início: {formatarDiaMes(planejamento.inicio)} · Fim: não definido
          </span>
        ) : (
          <span className="px-2 text-[11px] text-fg-subtle" style={{ gridColumn: `1 / ${dias.length + 1}` }}>
            Não planejada
          </span>
        )}
      </div>
    </div>
  );
}
