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
    <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-line-strong bg-surface-2/50 p-10 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface text-fg-subtle shadow-xs ring-1 ring-inset ring-line">
        {icon ?? <Inbox size={18} />}
      </div>
      <div>
        <p className="text-sm font-semibold text-fg">{title}</p>
        <p className="mt-1 text-sm text-fg-subtle">{description}</p>
      </div>
    </div>
  );
}
