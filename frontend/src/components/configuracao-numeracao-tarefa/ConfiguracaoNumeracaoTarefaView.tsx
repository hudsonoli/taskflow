"use client";

import { motion } from "framer-motion";
import { AlertTriangle, Hash } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { formatCodigoTarefa } from "@/lib/ids";
import { useAppData } from "@/lib/AppDataContext";

export function ConfiguracaoNumeracaoTarefaView() {
  const { configuracaoNumeracaoTarefa, setConfiguracaoNumeracaoTarefa } = useAppData();

  function updateConfig(patch: Partial<typeof configuracaoNumeracaoTarefa>) {
    setConfiguracaoNumeracaoTarefa((current) => ({ ...current, ...patch, updatedAt: new Date().toISOString() }));
  }

  const proximoCodigo = formatCodigoTarefa(configuracaoNumeracaoTarefa.ano, configuracaoNumeracaoTarefa.proximoNumero);

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
                Código de cada tarefa no formato #AA0000 (ano + sequencial), separado por ano.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Ano"
            type="number"
            value={configuracaoNumeracaoTarefa.ano}
            onChange={(event) => updateConfig({ ano: Number(event.target.value) || new Date().getFullYear() })}
          />
          <Input
            label="Iniciar tarefas a partir do número"
            type="number"
            min={1}
            value={configuracaoNumeracaoTarefa.proximoNumero}
            onChange={(event) => updateConfig({ proximoNumero: Math.max(1, Number(event.target.value) || 1) })}
          />
        </div>

        <div className="mt-5 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-500 dark:text-indigo-400">Próxima tarefa criada</p>
          <p className="mt-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">{proximoCodigo}</p>
        </div>

        <div className="mt-5 flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Ajuste manual — use apenas ao migrar a numeração já usada no iClips ou durante a implementação. A
          contagem vira automaticamente para 0001 a cada novo ano.
        </div>
      </div>
    </div>
  );
}
