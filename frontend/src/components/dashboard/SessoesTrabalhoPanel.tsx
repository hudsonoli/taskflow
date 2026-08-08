"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Clock, PlayCircle, StopCircle } from "lucide-react";
import clsx from "clsx";
import { listSessoesTrabalho } from "@/lib/api";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";

function formatDuracao(segundos: number | null): string {
  if (segundos === null) return "em andamento";
  const minutos = Math.floor(segundos / 60);
  const resto = segundos % 60;
  return `${minutos}m ${resto}s`;
}

export function SessoesTrabalhoPanel() {
  const [sessoes, setSessoes] = useState<SessaoTrabalho[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    listSessoesTrabalho()
      .then(setSessoes)
      .catch(() => setErro("Não foi possível conectar à API (http://localhost:8010)."));
  }, []);

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
          Sessões de trabalho recentes
        </h2>
        <span className="text-xs text-zinc-400">motor de horas</span>
      </div>

      {erro && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
          {erro}
        </p>
      )}

      {!erro && sessoes === null && (
        <p className="text-sm text-zinc-400">Carregando…</p>
      )}

      {!erro && sessoes !== null && sessoes.length === 0 && (
        <p className="text-sm text-zinc-400">
          Nenhuma sessão de trabalho registrada ainda. Inicie uma sessão para começar a acompanhar o tempo.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        <AnimatePresence>
          {sessoes?.map((sessao, index) => (
            <motion.li
              key={sessao.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className="flex items-center justify-between rounded-xl border border-zinc-100 px-3 py-2.5 dark:border-zinc-800"
            >
              <div className="flex items-center gap-3">
                {sessao.status === "ativa" ? (
                  <PlayCircle size={16} className="text-emerald-500" />
                ) : (
                  <StopCircle size={16} className="text-zinc-400" />
                )}
                <div>
                  <p className="text-sm font-medium text-zinc-800 dark:text-zinc-100">
                    {sessao.demandaId}
                  </p>
                  <p className="text-xs text-zinc-400">
                    {sessao.usuarioId ?? sessao.departamentoId ?? "sem responsável"}
                  </p>
                </div>
              </div>
              <div
                className={clsx(
                  "flex items-center gap-1.5 text-xs font-medium",
                  sessao.status === "ativa" ? "text-emerald-500" : "text-zinc-400",
                )}
              >
                <Clock size={13} />
                {formatDuracao(sessao.duracaoSegundos)}
              </div>
            </motion.li>
          ))}
        </AnimatePresence>
      </ul>
    </div>
  );
}
