import type { ReactNode } from "react";
import clsx from "clsx";

export type BadgeTone = "neutral" | "blue" | "green" | "amber" | "red";

const toneClassNames: Record<BadgeTone, string> = {
  // `ring-inset` de baixa opacidade dá contorno ao badge (ele não "derrete" no fundo do card) sem mudar o tamanho nem as cores de texto.
  neutral: "bg-zinc-100 text-zinc-600 ring-zinc-500/15 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-400/15",
  blue: "bg-indigo-50 text-indigo-700 ring-indigo-600/15 dark:bg-indigo-500/10 dark:text-indigo-400 dark:ring-indigo-400/20",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/15 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-400/20",
  amber: "bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-400/20",
  red: "bg-red-50 text-red-700 ring-red-600/15 dark:bg-red-500/10 dark:text-red-400 dark:ring-red-400/20",
};

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ring-inset",
        toneClassNames[tone],
      )}
    >
      {children}
    </span>
  );
}
