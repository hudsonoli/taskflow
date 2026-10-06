"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

/**
 * Cabeçalho padrão das views (ver CLAUDE.md > Componentes UI).
 *
 * Proporções deliberadamente compactas — ícone 36px, título text-lg (17px), padding p-4.
 * Antes cada view repetia um bloco com ícone 48px, título text-2xl (24px) e p-5/sm:p-6, o
 * que deixava o topo da tela pesado e "ampliado" em relação ao conteúdo. Não aumentar
 * estes valores por view: se o cabeçalho parece apertado, encurte o texto.
 */
export function PageHeader({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description?: string;
  /** Badge, botão ou qualquer controle alinhado à direita. */
  action?: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
      className="rounded-xl border border-line bg-surface p-4 shadow-sm"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            {icon}
          </div>
          <div className="min-w-0">
            <h1 className="text-lg font-semibold tracking-tight text-fg">{title}</h1>
            {description && (
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-fg-muted">{description}</p>
            )}
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </motion.div>
  );
}
