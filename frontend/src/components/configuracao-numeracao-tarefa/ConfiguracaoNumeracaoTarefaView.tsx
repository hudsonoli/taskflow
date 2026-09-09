"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Hash, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { obterNumeracaoTarefaReal } from "@/lib/api-backend";
import type { ConfiguracaoNumeracaoTarefaRead } from "@/types/configuracao-numeracao-tarefa";

/**
 * Fase 2G.8B — substitui o mock/local state por leitura real, somente informativa. Sem
 * formulário, sem edição de ano/contador: o backend não oferece (nem deve oferecer) ajuste
 * via API — o único mecanismo de inicialização do contador é o CLI administrativo, usado uma
 * única vez antes da primeira Demanda ir para produção. Esta tela nunca escreve nada.
 */

function formatarNumero(numero: number): string {
  return `#${numero}`;
}

export function ConfiguracaoNumeracaoTarefaView() {
  const [dados, setDados] = useState<ConfiguracaoNumeracaoTarefaRead | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  async function carregar() {
    setCarregando(true);
    setErro(null);
    try {
      setDados(await obterNumeracaoTarefaReal());
    } catch (error) {
      setErro(
        error instanceof Error ? error.message : "Não foi possível carregar a numeração de tarefas.",
      );
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    // setTimeout(0) tira o setState síncrono de dentro do corpo do efeito — mesmo padrão já
    // usado em ConfiguracaoEmailView/AppDataContext.
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, []);

  if (carregando) {
    return (
      <div className="flex items-center justify-center gap-2 rounded-2xl border border-zinc-200 bg-white p-10 text-sm text-zinc-500 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        Carregando numeração de tarefas…
      </div>
    );
  }

  if (erro || !dados) {
    return <EstadoErro mensagem={erro ?? "Não foi possível carregar a numeração de tarefas."} onRetry={carregar} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <Hash className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Numeração de tarefas</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Gerenciado automaticamente pelo sistema.
              </p>
            </div>
          </div>
          <Badge tone="green">Banco real</Badge>
        </div>
      </motion.div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Entidade</p>
            <p className="mt-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">{dados.rotuloEntidade}</p>
          </div>
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Status</p>
            <p className="mt-1 flex items-center gap-1.5 text-lg font-semibold">
              {dados.consistente ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <span className="text-emerald-700 dark:text-emerald-400">Consistente</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                  <span className="text-amber-700 dark:text-amber-400">Atenção necessária</span>
                </>
              )}
            </p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-500 dark:text-indigo-400">Contador atual</p>
            <p className="mt-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">{formatarNumero(dados.contadorAtual)}</p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-500 dark:text-indigo-400">Próximo número</p>
            <p className="mt-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">{formatarNumero(dados.proximoNumeroEstimado)}</p>
          </div>
          <div className="rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30 sm:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Maior número emitido no TaskFloww</p>
            <p className="mt-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              {dados.maiorNumeroEmitido != null ? formatarNumero(dados.maiorNumeroEmitido) : "—"}
            </p>
          </div>
        </div>

        {!dados.consistente && (
          <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            A numeração precisa de verificação administrativa.
          </div>
        )}

        <div className="mt-5 flex flex-col gap-1.5 text-xs text-zinc-500 dark:text-zinc-400">
          <p>A numeração é contínua e não reinicia a cada ano.</p>
          <p>A inicialização para continuidade de sistemas anteriores é feita administrativamente antes da primeira emissão.</p>
        </div>
      </div>
    </div>
  );
}
