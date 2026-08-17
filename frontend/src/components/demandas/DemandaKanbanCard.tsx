"use client";

import { CalendarDays, Clock } from "lucide-react";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { motion } from "framer-motion";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { formatPrazo, normalizarUsuarioId, prioridadeDemandaLabels } from "@/lib/demandas";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverProjetoNome, resolverUsuarioPorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda, DemandaPrioridade } from "@/types/demanda";

// Esquema pedido pelo time: alta = azul marinho, média = azul céu, baixa = azul bebê.
const prioridadeClassNames: Record<DemandaPrioridade, string> = {
  alta: "border-blue-900 bg-blue-900/5 text-blue-900 dark:border-blue-300 dark:bg-blue-400/10 dark:text-blue-200",
  media: "border-sky-400 bg-sky-50 text-sky-700 dark:border-sky-400/60 dark:bg-sky-500/10 dark:text-sky-300",
  baixa: "border-sky-200 bg-sky-50/60 text-sky-500 dark:border-sky-200/40 dark:bg-sky-500/5 dark:text-sky-300",
};

const prioridadeBorderClassNames: Record<DemandaPrioridade, string> = {
  alta: "border-l-blue-900 dark:border-l-blue-300",
  media: "border-l-sky-400 dark:border-l-sky-400",
  baixa: "border-l-sky-200 dark:border-l-sky-300",
};

function CardContent({ demanda }: { demanda: Demanda }) {
  const { usuarios } = useDiretorioUsuarios();
  const { projetos } = useDiretorioProjetos();
  const responsaveis = demanda.usuarioResponsavelIds
    .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
    .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));

  return (
    <>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">
            {rotuloDemanda(demanda)}
          </span>
          <h3 className="mt-1 line-clamp-2 text-sm font-semibold leading-5 text-zinc-950 transition group-hover:text-indigo-600 dark:text-zinc-50 dark:group-hover:text-indigo-400">
            {demanda.nome}
          </h3>
        </div>
        <span className={`shrink-0 rounded-full border px-2 py-1 text-xs font-semibold ${prioridadeClassNames[demanda.prioridade]}`}>
          {prioridadeDemandaLabels[demanda.prioridade]}
        </span>
      </div>

      <p className="mt-2 truncate text-xs font-medium text-zinc-500 dark:text-zinc-400">
        {resolverProjetoNome(demanda.projetoId, projetos)}
      </p>

      <div className="mt-3 flex items-center justify-between gap-2">
        <AvatarStack pessoas={responsaveis} max={3} size="h-6 w-6" emptyLabel="" />
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-semibold text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
          <CalendarDays className="h-3.5 w-3.5" />
          {formatPrazo(demanda.prazoEtapaAtual)}
        </span>
      </div>

      {demanda.status === "aguardando_cliente" && demanda.prazoRetornoCliente && (
        <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
          <Clock className="h-3.5 w-3.5" />
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
}: {
  demanda: Demanda;
  onOpenDetails: (demandaId: string) => void;
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
        className={`group w-full touch-none rounded-2xl border border-l-4 border-zinc-100 bg-white p-3.5 text-left shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-lg dark:border-zinc-800 dark:bg-zinc-900 ${
          arrastavel ? "cursor-grab active:cursor-grabbing" : "cursor-pointer"
        } ${prioridadeBorderClassNames[demanda.prioridade]} ${isDragging ? "opacity-30" : ""}`}
      >
        <CardContent demanda={demanda} />
      </button>
    </motion.div>
  );
}

export function DemandaKanbanCardOverlay({ demanda }: { demanda: Demanda }) {
  return (
    <div
      className={`w-[260px] rotate-2 cursor-grabbing rounded-2xl border border-l-4 border-zinc-100 bg-white p-3.5 text-left shadow-2xl dark:border-zinc-800 dark:bg-zinc-900 ${prioridadeBorderClassNames[demanda.prioridade]}`}
    >
      <CardContent demanda={demanda} />
    </div>
  );
}
