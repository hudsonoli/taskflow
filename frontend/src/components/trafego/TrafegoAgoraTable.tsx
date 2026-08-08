"use client";

import { useState } from "react";
import { Activity, Inbox, StopCircle } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { fecharSessaoTrabalho } from "@/lib/api";
import { elapsedSeconds, formatTempoOperacional, resolveTrafegoDemandaNome, resolveTrafegoDepartamentoNome, resolveTrafegoUsuarioNome } from "@/lib/trafego";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";

function formatInicio(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function TrafegoAgoraTable({ sessoes, now, onChanged }: { sessoes: SessaoTrabalho[]; now: Date; onChanged: () => void }) {
  const [encerrandoId, setEncerrandoId] = useState<string | null>(null);

  const ordenadas = [...sessoes].sort((a, b) => elapsedSeconds(b, now) - elapsedSeconds(a, now));

  async function handleEncerrar(sessaoId: string) {
    setEncerrandoId(sessaoId);
    try {
      await fecharSessaoTrabalho(sessaoId, "conclusao");
      onChanged();
    } finally {
      setEncerrandoId(null);
    }
  }

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Quem está trabalhando agora</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Sessões ativas ordenadas por maior tempo em execução.</p>
        </div>
        <Badge tone="green">{sessoes.length} ativa(s)</Badge>
      </div>

      {ordenadas.length === 0 ? (
        <EmptyState title="Nenhuma sessão em execução no momento" description="Inicie uma sessão de teste acima ou aguarde novas movimentações." icon={<Inbox size={16} />} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-zinc-100 dark:border-zinc-800">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-100 bg-zinc-50/80 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-400 dark:border-zinc-800 dark:bg-zinc-950/40">
                <tr>
                  <th className="px-4 py-2.5">Colaborador</th>
                  <th className="px-4 py-2.5">Demanda</th>
                  <th className="px-4 py-2.5">Início</th>
                  <th className="px-4 py-2.5 text-right">Tempo estimado</th>
                  <th className="px-4 py-2.5" />
                </tr>
              </thead>
              <tbody>
                <AnimatePresence>
                  {ordenadas.map((sessao) => (
                    <motion.tr
                      key={sessao.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-800/40"
                    >
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-3">
                          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white">
                            <Activity className="h-4 w-4" />
                          </span>
                          <div>
                            <p className="font-semibold text-zinc-950 dark:text-zinc-50">{resolveTrafegoUsuarioNome(sessao.usuarioId)}</p>
                            <p className="text-xs text-zinc-500 dark:text-zinc-400">{resolveTrafegoDepartamentoNome(sessao.departamentoId)}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-medium text-zinc-900 dark:text-zinc-100">{resolveTrafegoDemandaNome(sessao.demandaId)}</td>
                      <td className="px-4 py-3 font-mono text-xs text-zinc-500 dark:text-zinc-400">{formatInicio(sessao.inicioEm)}</td>
                      <td className="px-4 py-3 text-right font-mono font-bold tabular-nums text-zinc-950 dark:text-zinc-50">
                        {formatTempoOperacional(elapsedSeconds(sessao, now))}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <Button
                          variant="secondary"
                          className="px-3 py-1.5 text-xs"
                          disabled={encerrandoId === sessao.id}
                          onClick={() => handleEncerrar(sessao.id)}
                        >
                          <StopCircle className="h-3.5 w-3.5" />
                          {encerrandoId === sessao.id ? "Encerrando…" : "Encerrar"}
                        </Button>
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
