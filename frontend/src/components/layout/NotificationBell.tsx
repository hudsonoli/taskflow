"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, ClipboardList } from "lucide-react";
import { useRouter } from "next/navigation";
import { useAppData } from "@/lib/AppDataContext";
import { demandaTemResponsavel } from "@/lib/demandas";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda } from "@/types/demanda";

// A notificação de menção (@Nome em comentário) saiu daqui na Fase 2E.4: Comentários reais
// não trazem @mention nesta primeira versão (decisão explícita da fase), e o comentário de
// TODAS as demandas carregadas de uma vez também não existe mais — é buscado por Demanda, sob
// demanda, para não inflar a listagem (ver DemandaComentario/AtividadeDemandaSection). Volta
// quando @mention for implementado, com uma fonte de dado compatível.
type TarefaNotificacao = { tipo: "tarefa"; demanda: Demanda };

export function NotificationBell() {
  const { demandas, usuarioAtual, setDemandaParaAbrir } = useAppData();
  const { usuarios: diretorio } = useDiretorioUsuarios();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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

  const totalNotificacoes = tarefasAtribuidas.length;

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
