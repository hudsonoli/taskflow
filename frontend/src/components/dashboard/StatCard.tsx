"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: string;
  index: number;
}

export function StatCard({ label, value, icon: Icon, accent, index }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06, ease: "easeOut" }}
      whileHover={{ y: -2 }}
      className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div
        className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl text-white"
        style={{ background: accent }}
      >
        <Icon size={18} />
      </div>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="mt-1 text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        {value}
      </p>
    </motion.div>
  );
}
