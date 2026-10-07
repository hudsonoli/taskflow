"use client";

import { useState } from "react";
import { Activity, Inbox, StopCircle } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { fecharSessaoTrabalho } from "@/lib/api";
import { formatTempoOperacional } from "@/lib/trafego";
import type { TrafegoAgoraLinha } from "@/types/trafego";

function formatInicio(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

/** `#2063 — Nome`; Demanda inexistente cai no id (nem inventa nome nem esconde a sessão). */
function nomeDaDemanda(linha: TrafegoAgoraLinha): string {
  return linha.demandaNumero !== null && linha.demandaNome !== null
    ? `#${linha.demandaNumero} — ${linha.demandaNome}`
    : linha.demandaId;
}

/**
 * D2-D3C3 — "Quem está trabalhando agora" sobre a listagem paginada do servidor
 * (`GET /sessoes-trabalho/trafego/agora`): nomes de usuário/departamento/Demanda já vêm nas linhas
 * (nada de diretório do cliente) e a ordem — mais tempo em execução primeiro — também. Não há
 * mais o array de 100 sessões: `total` é o do universo filtrado. `linhas === null` é "carregando";
 * `erro` é falha da requisição; lista vazia é "zero confirmado". O tempo de cada linha anda
 * localmente (`decorridoSegundos` + o que passou desde que a linha chegou) — sem polling.
 */
export function TrafegoAgoraTable({
  linhas,
  total,
  erro,
  now,
  onChanged,
  onCarregarMais,
  carregandoMais,
  erroMais,
}: {
  linhas: TrafegoAgoraLinha[] | null;
  total: number;
  erro: string | null;
  now: Date;
  onChanged: () => void;
  onCarregarMais: () => void;
  carregandoMais: boolean;
  erroMais: string | null;
}) {
  const [encerrandoId, setEncerrandoId] = useState<string | null>(null);

  async function handleEncerrar(sessaoId: string) {
    setEncerrandoId(sessaoId);
    try {
      await fecharSessaoTrabalho(sessaoId, "conclusao");
      onChanged();
    } finally {
      setEncerrandoId(null);
    }
  }

  const carregando = linhas === null && !erro;

  return (
    <section className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-fg">Quem está trabalhando agora</h2>
          <p className="text-sm text-fg-muted">Sessões ativas ordenadas por maior tempo em execução.</p>
        </div>
        <Badge tone="green">{erro ? "—" : linhas === null ? "…" : `${total} ativa(s)`}</Badge>
      </div>

      {erro ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erro}
        </div>
      ) : carregando ? (
        <EmptyState title="Carregando…" description="Buscando as sessões em execução no servidor." icon={<Inbox size={16} />} />
      ) : linhas === null || linhas.length === 0 ? (
        <EmptyState title="Nenhuma sessão em execução no momento" description="Inicie uma sessão de teste acima ou aguarde novas movimentações." icon={<Inbox size={16} />} />
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-line">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-line bg-surface-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-fg-subtle">
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
                    {linhas.map((linha) => (
                      <motion.tr
                        key={linha.sessaoId}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="border-b border-line transition last:border-0 hover:bg-surface-hover"
                      >
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-3">
                            <span className="bg-brand-gradient flex h-8 w-8 items-center justify-center rounded-xl">
                              <Activity className="h-4 w-4" />
                            </span>
                            <div>
                              <p className="font-semibold text-fg">{linha.usuarioNome ?? "Sem usuário"}</p>
                              <p className="text-xs text-fg-muted">{linha.departamentoNome ?? "Sem departamento"}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 font-medium text-fg">{nomeDaDemanda(linha)}</td>
                        <td className="px-4 py-3 font-mono text-xs text-fg-muted">{formatInicio(linha.inicioEm)}</td>
                        <td className="px-4 py-3 text-right font-mono font-bold tabular-nums text-fg">
                          {formatTempoOperacional(
                            linha.decorridoSegundos + Math.max(0, Math.floor((now.getTime() - linha.recebidoEm) / 1000)),
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          <Button
                            variant="secondary"
                            className="px-3 py-1.5 text-xs"
                            disabled={encerrandoId === linha.sessaoId}
                            onClick={() => handleEncerrar(linha.sessaoId)}
                          >
                            <StopCircle className="h-3.5 w-3.5" />
                            {encerrandoId === linha.sessaoId ? "Encerrando…" : "Encerrar"}
                          </Button>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-3 flex flex-col items-center gap-2">
            {linhas.length < total && (
              <Button type="button" variant="secondary" onClick={onCarregarMais} disabled={carregandoMais}>
                {carregandoMais ? "Carregando…" : "Carregar mais"}
              </Button>
            )}
            <p className="text-xs text-fg-subtle">
              Mostrando {linhas.length} de {total}
            </p>
            {erroMais && <p className="text-xs text-red-600 dark:text-red-400">{erroMais}</p>}
          </div>
        </>
      )}
    </section>
  );
}
