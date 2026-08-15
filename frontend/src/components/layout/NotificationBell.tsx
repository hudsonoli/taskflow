"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AtSign, Bell, ClipboardList } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAppData } from "@/lib/AppDataContext";
import { demandaTemResponsavel } from "@/lib/demandas";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { resolverUsuarioPorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda, DemandaComentario } from "@/types/demanda";

type MencaoNotificacao = { tipo: "mencao"; demanda: Demanda; comentario: DemandaComentario };
type TarefaNotificacao = { tipo: "tarefa"; demanda: Demanda };

export function NotificationBell() {
  const { demandas, usuarioAtual, setDemandaParaAbrir } = useAppData();
  const { usuarios: diretorio } = useDiretorioUsuarios();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  // Menção/responsável gravados como codigoInterno enquanto Demanda continuar mock — ver
  // lib/referencias.ts.
  const meuCodigoInterno = usuarioAtual ? resolverUsuarioPorReferencia(usuarioAtual.id, diretorio)?.codigoInterno : undefined;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const mencoes = useMemo<MencaoNotificacao[]>(() => {
    if (!usuarioAtual) return [];
    const items: MencaoNotificacao[] = [];
    for (const demanda of demandas) {
      for (const comentario of demanda.comentarios) {
        const mencionado = comentario.mencoes.includes(usuarioAtual.id) || (meuCodigoInterno && comentario.mencoes.includes(meuCodigoInterno));
        if (mencionado && comentario.usuarioId !== usuarioAtual.id) {
          items.push({ tipo: "mencao", demanda, comentario });
        }
      }
    }
    return items.slice(0, 5);
  }, [demandas, usuarioAtual, meuCodigoInterno]);

  const tarefasAtribuidas = useMemo<TarefaNotificacao[]>(() => {
    if (!usuarioAtual) return [];
    return demandas
      .filter(
        (demanda) =>
          demandaTemResponsavel(demanda, usuarioAtual.id, diretorio) &&
          demanda.status !== "concluida" &&
          demanda.status !== "cancelada",
      )
      .slice(0, 5)
      .map((demanda) => ({ tipo: "tarefa", demanda }));
  }, [demandas, usuarioAtual, diretorio]);

  const totalNotificacoes = mencoes.length + tarefasAtribuidas.length;

  function abrirDemanda(demandaId: string, aba: string) {
    setDemandaParaAbrir({ demandaId, aba });
    setOpen(false);
    router.push("/tarefas");
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label="Notificações"
        className="relative flex h-9 w-9 items-center justify-center rounded-full border border-zinc-200 bg-white text-zinc-500 transition-colors hover:text-zinc-900 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        <Bell size={16} />
        {totalNotificacoes > 0 && (
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-indigo-500" />
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-30 mt-2 w-80 overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-lg dark:border-zinc-800 dark:bg-zinc-900"
          >
            <div className="border-b border-zinc-100 px-4 py-3 dark:border-zinc-800">
              <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Notificações</p>
            </div>

            <div className="max-h-96 overflow-y-auto">
              {totalNotificacoes === 0 && (
                <p className="px-4 py-6 text-center text-sm text-zinc-400">Nenhuma notificação por aqui.</p>
              )}

              {mencoes.length > 0 && (
                <div className="p-1.5">
                  <p className="px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-400">Menções</p>
                  {mencoes.map(({ demanda, comentario }) => (
                    <button
                      key={comentario.id}
                      type="button"
                      onClick={() => abrirDemanda(demanda.id, "atividade")}
                      className="flex w-full items-start gap-2.5 rounded-xl px-2.5 py-2 text-left transition hover:bg-zinc-50 dark:hover:bg-zinc-800"
                    >
                      <AtSign className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
                      <div className="min-w-0">
                        <p className="text-sm text-zinc-700 dark:text-zinc-200">
                          <span className="font-semibold text-zinc-900 dark:text-zinc-100">{comentario.usuario}</span> mencionou você em{" "}
                          <span className="font-medium">{demanda.nome}</span>
                        </p>
                        <p className="mt-0.5 truncate text-xs text-zinc-400">{comentario.texto}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {tarefasAtribuidas.length > 0 && (
                <div className="p-1.5">
                  <p className="px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-400">Tarefas atribuídas a você</p>
                  {tarefasAtribuidas.map(({ demanda }) => (
                    <button
                      key={demanda.id}
                      type="button"
                      onClick={() => abrirDemanda(demanda.id, "dados")}
                      className="flex w-full items-start gap-2.5 rounded-xl px-2.5 py-2 text-left transition hover:bg-zinc-50 dark:hover:bg-zinc-800"
                    >
                      <ClipboardList className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-zinc-800 dark:text-zinc-100">
                          {rotuloDemanda(demanda)} · {demanda.nome}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
