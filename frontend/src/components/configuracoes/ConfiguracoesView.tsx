"use client";

import { motion } from "framer-motion";
import { Settings } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export function ConfiguracoesView() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-center justify-between gap-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          <Settings className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Configurações</h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Escolha um item no menu ao lado para gerenciar cadastros e regras do workspace.</p>
        </div>
      </div>
      <Badge tone="blue">Dados locais</Badge>
    </motion.div>
  );
}
