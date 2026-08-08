import type { ReactNode } from "react";
import clsx from "clsx";

export type BadgeTone = "neutral" | "blue" | "green" | "amber" | "red";

const toneClassNames: Record<BadgeTone, string> = {
  neutral: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300",
  blue: "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400",
  green: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400",
  amber: "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
  red: "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400",
};

export function Badge({ tone = "neutral", children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold",
        toneClassNames[tone],
      )}
    >
      {children}
    </span>
  );
}
