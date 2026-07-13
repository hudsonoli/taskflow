import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

type EmptyStateIllustrationProps = {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
};

export function EmptyStateIllustration({
  title,
  description,
  icon,
  action,
}: EmptyStateIllustrationProps) {
  return (
    <div className="rounded-3xl border border-dashed border-zinc-200 bg-[#faf8f4] p-8 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-3xl bg-white text-zinc-500 shadow-sm ring-1 ring-zinc-100">
        {icon ?? <Inbox className="h-6 w-6" aria-hidden="true" />}
      </div>
      <h3 className="mt-4 text-base font-semibold text-zinc-950">{title}</h3>
      <p className="mx-auto mt-1 max-w-md text-sm text-zinc-500">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
