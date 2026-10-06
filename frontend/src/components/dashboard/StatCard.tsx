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

export function StatCard({ label, value, icon: Icon, accent, onAccent, index }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: "easeOut" }}
      whileHover={{ y: -2 }}
      className="rounded-2xl border border-line bg-surface p-5 shadow-sm"
    >
      <div
        className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl text-white"
        style={{ background: accent, color: onAccent }}
      >
        <Icon size={18} />
      </div>
      <p className="text-sm text-fg-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold tracking-tight text-fg">
        {value}
      </p>
    </motion.div>
  );
}
