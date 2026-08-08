import type { ReactNode } from "react";
import { Inbox } from "lucide-react";

export function EmptyState({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50 p-10 text-center dark:border-zinc-800 dark:bg-zinc-900/40">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-100 text-zinc-400 dark:bg-zinc-800">
        {icon ?? <Inbox size={18} />}
      </div>
      <div>
        <p className="text-sm font-semibold text-zinc-700 dark:text-zinc-200">{title}</p>
        <p className="mt-1 text-sm text-zinc-400">{description}</p>
      </div>
    </div>
  );
}
