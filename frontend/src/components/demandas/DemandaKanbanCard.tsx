"use client";

import { CalendarDays, Clock, FolderKanban, Play } from "lucide-react";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { motion } from "framer-motion";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { formatPrazo, normalizarUsuarioId } from "@/lib/demandas";
import { prioridadeBordaClasse } from "@/lib/prioridade-demanda";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { resolverProjetoNome, resolverUsuarioPorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";
import { useUsuariosComIds } from "@/lib/useUsuariosComIds";
import type { Demanda } from "@/types/demanda";
import { KanbanProgressoAnel } from "./KanbanProgressoAnel";
import { PrioridadeTag } from "./PrioridadeTag";

/** Cantos contínuos (estilo iOS); onde o navegador não suporta, degrada para o raio comum. */
const SQUIRCLE = "[corner-shape:squircle]";

function CardContent({ demanda }: { demanda: Demanda }) {
  const { usuarios } = useUsuariosComIds(demanda.usuarioResponsavelIds);
  const { projetos } = useDiretorioProjetos();
  const responsaveis = demanda.usuarioResponsavelIds
    .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
    .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));
  const projeto = resolverProjetoNome(demanda.projetoId, projetos);

  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-[11px] font-medium tabular-nums text-fg-subtle">{rotuloDemanda(demanda)}</span>
        <PrioridadeTag prioridade={demanda.prioridade} />
      </div>

      <h3 className="mt-2 line-clamp-2 text-[14px] font-semibold leading-snug tracking-[-0.005em] text-fg transition group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
        {demanda.nome}
      </h3>

      {projeto && (
        <p className="mt-1.5 flex items-center gap-1.5 text-xs text-fg-muted">
          <FolderKanban aria-hidden className="h-3 w-3 shrink-0 text-fg-subtle" strokeWidth={2.25} />
          <span className="truncate">{projeto}</span>
        </p>
      )}

      {demanda.trabalhandoAgora && (
        <p className={`mt-2 inline-flex items-center gap-1.5 rounded-[7px] bg-indigo-50 px-2 py-1 text-[11px] font-semibold leading-none text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300 ${SQUIRCLE}`}>
          <span className="relative flex h-1.5 w-1.5" aria-hidden>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-60 motion-reduce:animate-none" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-indigo-500" />
          </span>
          Você está trabalhando nesta
        </p>
      )}

      <div className="mt-3 h-px bg-black/[0.06] dark:bg-white/[0.08]" />
      <div className="mt-2.5 flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="inline-flex shrink-0 items-center gap-1 text-[11.5px] font-medium tabular-nums text-fg-muted">
            <CalendarDays aria-hidden className="h-3 w-3 shrink-0" strokeWidth={2.25} />
            {formatPrazo(demanda.prazoEtapaAtual)}
          </span>
          <KanbanProgressoAnel demanda={demanda} />
        </div>
        <AvatarStack pessoas={responsaveis} max={3} size="h-[22px] w-[22px]" emptyLabel="" />
      </div>

      {demanda.status === "aguardando_cliente" && demanda.prazoRetornoCliente && (
        <div className={`mt-2.5 inline-flex items-center gap-1.5 rounded-[7px] bg-amber-50 px-2 py-1 text-[11px] font-semibold leading-none text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 ${SQUIRCLE}`}>
          <Clock aria-hidden className="h-3 w-3" strokeWidth={2.25} />
          Retorno até {formatPrazo(demanda.prazoRetornoCliente)}
        </div>
      )}
    </>
  );
}

export function DemandaKanbanCard({
  demanda,
  onOpenDetails,
  arrastavel = true,
  motivoBloqueio,
  onIniciarTrabalho,
  podeIniciar = true,
}: {
  demanda: Demanda;
  onOpenDetails: (demandaId: string) => void;
  /** "Iniciar trabalho" na tarefa que já está em execução mas em que a pessoa ainda não tem sessão (a ação por arraste é a mesma, só que na própria coluna). */
  onIniciarTrabalho?: (demandaId: string) => void;
  /** false fora do expediente: iniciar trabalho continua bloqueado (o servidor também recusa). */
  podeIniciar?: boolean;
  /** false fora do expediente — o card continua clicável (abre detalhes), mas não arrasta. */
  arrastavel?: boolean;
  motivoBloqueio?: string;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: demanda.id,
    disabled: !arrastavel,
  });

  const style = transform ? { transform: CSS.Translate.toString(transform) } : undefined;

  return (
    <motion.div layout initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} transition={{ duration: 0.18 }}>
      <button
        ref={setNodeRef}
        style={style}
        {...(arrastavel ? listeners : {})}
        {...attributes}
        type="button"
        onClick={() => onOpenDetails(demanda.id)}
        title={arrastavel ? undefined : motivoBloqueio}
        className={`group w-full touch-none rounded-[12px] border border-l-[3px] border-black/[0.06] bg-white p-3 text-left shadow-[0_1px_2px_rgba(0,0,0,0.05)] transition-all duration-200 ease-out hover:-translate-y-px hover:shadow-[0_6px_16px_-6px_rgba(0,0,0,0.18)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 dark:border-white/[0.08] dark:bg-zinc-900 ${SQUIRCLE} ${
          arrastavel ? "cursor-grab active:cursor-grabbing" : "cursor-pointer"
        } ${prioridadeBordaClasse[demanda.prioridade]} ${isDragging ? "opacity-30" : ""}`}
      >
        <CardContent demanda={demanda} />
      </button>
      {onIniciarTrabalho && demanda.status === "em_execucao" && demanda.podeIniciarTrabalho && !demanda.trabalhandoAgora && (
        <button
          type="button"
          onClick={() => onIniciarTrabalho(demanda.id)}
          disabled={!podeIniciar}
          title={podeIniciar ? "Começar a trabalhar nesta tarefa (encerra o seu trabalho em outra, se houver)" : motivoBloqueio}
          className={`mt-1.5 inline-flex w-full items-center justify-center gap-1.5 rounded-[10px] border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 transition hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300 ${SQUIRCLE}`}
        >
          <Play className="h-3.5 w-3.5" aria-hidden />
          Iniciar trabalho
        </button>
      )}
    </motion.div>
  );
}

export function DemandaKanbanCardOverlay({ demanda }: { demanda: Demanda }) {
  return (
    <div
      className={`w-[260px] rotate-[1.6deg] scale-[1.03] cursor-grabbing rounded-[12px] border border-l-[3px] border-black/[0.06] bg-white p-3 text-left shadow-[0_16px_32px_-12px_rgba(0,0,0,0.32)] dark:border-white/[0.08] dark:bg-zinc-900 ${SQUIRCLE} ${prioridadeBordaClasse[demanda.prioridade]}`}
    >
      <CardContent demanda={demanda} />
    </div>
  );
}
