"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, ClipboardList } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listarNotificacoes, listDemandasReais, marcarNotificacaoLida } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { formatarBadge } from "@/lib/notificacoes";
import { useNotificacoes } from "@/lib/NotificacoesContext";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda } from "@/types/demanda";
import type { Notificacao } from "@/types/notificacoes";

// O sino é o PREVIEW rápido; o histórico completo, os filtros e os prazos da equipe ficam em /notificacoes.
// A contagem de não lidas NÃO é consultada aqui: vem do estado único (NotificacoesContext) que o menu do avatar e
// a página também usam — marcar como lida em qualquer lugar reconcilia todos na hora.
//
// "Tarefas atribuídas a você" (abaixo das notificações) segue como antes: filtro e `limit=5` server-side
// (`responsavelId` + `naoFinalizada`), refeito a cada abertura do dropdown (sem polling).
type TarefaNotificacao = { tipo: "tarefa"; demanda: Demanda };

export function NotificationBell() {
  const { usuarioAtual, setDemandaParaAbrir } = useAppData();
  const { resumo, recarregar, aplicarResumo } = useNotificacoes();
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

  const [recentes, setRecentes] = useState<Notificacao[]>([]);
  const [tarefasAtribuidas, setTarefasAtribuidas] = useState<TarefaNotificacao[]>([]);
  useEffect(() => {
    if (!usuarioAtual || !open) return;
    let cancelado = false;
    void recarregar();
    listarNotificacoes({ limit: 5 })
      .then((pagina) => {
        if (!cancelado) setRecentes(pagina.itens);
      })
      .catch(() => {
        // Falha de rede não derruba a navbar — degrada em silêncio.
      });
    listDemandasReais({ responsavelId: usuarioAtual.id, naoFinalizada: true, limit: 5 })
      .then((demandas) => {
        if (!cancelado) setTarefasAtribuidas(demandas.map((demanda) => ({ tipo: "tarefa" as const, demanda })));
      })
      .catch(() => {});
    return () => {
      cancelado = true;
    };
  }, [usuarioAtual, open, recarregar]);

  const badge = formatarBadge(resumo.naoLidas.total);

  function abrirDemanda(demandaId: string, aba: string) {
    setDemandaParaAbrir({ demandaId, aba });
    setOpen(false);
    router.push("/tarefas");
  }

  async function abrirNotificacao(notificacao: Notificacao) {
    if (!notificacao.lida) {
      setRecentes((atuais) => atuais.map((item) => (item.id === notificacao.id ? { ...item, lida: true } : item)));
      try {
        aplicarResumo(await marcarNotificacaoLida(notificacao.id)); // badge reconciliado na hora
      } catch {
        void recarregar();
      }
    }
    if (notificacao.demandaId) abrirDemanda(notificacao.demandaId, "dados");
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label={badge ? `Notificações — ${resumo.naoLidas.total} não lidas` : "Notificações"}
        aria-expanded={open}
        className="relative flex h-9 w-9 items-center justify-center rounded-full border border-line bg-surface text-fg-muted transition-colors hover:text-fg"
      >
        <Bell size={16} />
        {badge && (
          <span
            aria-hidden
            className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-indigo-600 px-1 text-[10px] font-bold leading-none text-white ring-2 ring-surface"
          >
            {badge}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-x-2 top-16 z-30 overflow-hidden rounded-2xl border border-line bg-surface shadow-lg sm:absolute sm:inset-x-auto sm:right-0 sm:top-auto sm:mt-2 sm:w-80"
          >
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <p className="text-sm font-semibold text-fg">Notificações</p>
              <Link
                href="/notificacoes"
                onClick={() => setOpen(false)}
                className="text-xs font-medium text-indigo-600 underline-offset-2 hover:underline dark:text-indigo-400"
              >
                Ver todas
              </Link>
            </div>

            <div className="max-h-96 overflow-y-auto">
              {recentes.length === 0 && tarefasAtribuidas.length === 0 && (
                <p className="px-4 py-6 text-center text-sm text-fg-subtle">Nenhuma notificação por aqui.</p>
              )}

              {recentes.length > 0 && (
                <div className="p-1.5">
                  <p className="px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Recentes</p>
                  {recentes.map((notificacao) => (
                    <button
                      key={notificacao.id}
                      type="button"
                      onClick={() => void abrirNotificacao(notificacao)}
                      className="flex w-full items-start gap-2.5 rounded-xl px-2.5 py-2 text-left transition hover:bg-surface-hover"
                    >
                      <span
                        aria-hidden
                        className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${notificacao.lida ? "bg-transparent" : "bg-indigo-600 dark:bg-indigo-400"}`}
                      />
                      <div className="min-w-0">
                        <p className={`truncate text-sm text-fg ${notificacao.lida ? "font-normal" : "font-semibold"}`}>
                          {notificacao.titulo}
                          {!notificacao.lida && <span className="sr-only"> (não lida)</span>}
                        </p>
                        <p className="truncate text-xs text-fg-muted">
                          {[notificacao.demandaReferencia, notificacao.demandaNome].filter(Boolean).join(" · ")}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {tarefasAtribuidas.length > 0 && (
                <div className="p-1.5">
                  <p className="px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Tarefas atribuídas a você</p>
                  {tarefasAtribuidas.map(({ demanda }) => (
                    <button
                      key={demanda.id}
                      type="button"
                      onClick={() => abrirDemanda(demanda.id, "dados")}
                      className="flex w-full items-start gap-2.5 rounded-xl px-2.5 py-2 text-left transition hover:bg-surface-hover"
                    >
                      <ClipboardList className="mt-0.5 h-4 w-4 shrink-0 text-fg-subtle" />
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-fg">
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
