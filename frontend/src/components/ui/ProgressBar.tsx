import { motion } from "framer-motion";
import clsx from "clsx";
import type { BadgeTone } from "@/components/ui/Badge";

const toneClassNames: Record<BadgeTone, string> = {
  neutral: "bg-zinc-400",
  blue: "bg-indigo-500",
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

export function ProgressBar({
  value,
  tone = "blue",
  label,
}: {
  value: number;
  tone?: BadgeTone;
  label?: string;
}) {
  return (
    <div>
      {label && (
        <div className="mb-1.5 flex items-center justify-between text-xs font-medium text-zinc-500 dark:text-zinc-400">
          <span>{label}</span>
          <span>{value}%</span>
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className={clsx("h-full rounded-full", toneClassNames[tone])}
        />
      </div>
    </div>
  );
}
