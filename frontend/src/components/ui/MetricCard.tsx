import type { ReactNode } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";
import type { BadgeTone } from "@/components/ui/Badge";

const toneClassNames: Record<BadgeTone, string> = {
  neutral: "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400",
  blue: "bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400",
  green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
  amber: "bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400",
  red: "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400",
};

export function MetricCard({
  title,
  value,
  description,
  icon,
  tone = "neutral",
  index = 0,
}: {
  title: string;
  value: number | string;
  description: string;
  icon: ReactNode;
  tone?: BadgeTone;
  index?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: "easeOut" }}
      className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className={clsx("mb-3 flex h-9 w-9 items-center justify-center rounded-xl", toneClassNames[tone])}>
        {icon}
      </div>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">{title}</p>
      <p className="mt-1.5 text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">{value}</p>
      <p className="mt-1 text-xs text-zinc-400">{description}</p>
    </motion.div>
  );
}
