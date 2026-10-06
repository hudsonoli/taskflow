"use client";

import { motion } from "framer-motion";
import { Settings } from "lucide-react";

export function ConfiguracoesView() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-center justify-between gap-4 rounded-2xl border border-line bg-surface p-5 shadow-sm"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <Settings className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-fg">Configurações</h1>
          <p className="text-sm text-fg-muted">Escolha um item no menu ao lado para gerenciar cadastros e regras do workspace.</p>
        </div>
      </div>
    </motion.div>
  );
}
