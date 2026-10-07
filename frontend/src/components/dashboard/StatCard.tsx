"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: string;
  /** cor do ícone sobre o fundo (padrão: branco; cards da marca usam a cor legível sobre a marca) */
  onAccent?: string;
  index: number;
}

/**
 * KPI compacto do Meu Dia: ícone pequeno à esquerda, rótulo discreto e valor em destaque.
 * O destaque no hover (sobe e cresce levemente) é só CSS `transform` numa camada interna — não ocupa
 * espaço no layout, então não empurra os vizinhos. `hover:` só vale em ponteiro com hover (nunca em touch)
 * e `motion-safe:` desliga o movimento para quem pede menos animação (sombra/borda continuam).
 */
export function StatCard({ label, value, icon: Icon, accent, onAccent, index }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: "easeOut" }}
      className="group relative hover:z-10"
    >
      <div className="flex h-full items-start gap-3 rounded-xl border border-line bg-surface p-4 shadow-sm transition-[transform,box-shadow,border-color] duration-200 ease-out group-hover:border-line-strong group-hover:shadow-lg motion-safe:group-hover:-translate-y-0.5 motion-safe:group-hover:scale-[1.03]">
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white"
          style={{ background: accent, color: onAccent }}
        >
          <Icon size={16} />
        </div>
        <div className="min-w-0">
          <p className="text-xs leading-4 text-fg-muted">{label}</p>
          <p className="mt-0.5 text-[1.75rem] font-semibold leading-9 tracking-tight text-fg">{value}</p>
        </div>
      </div>
    </motion.div>
  );
}
