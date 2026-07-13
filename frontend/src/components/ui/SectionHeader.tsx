import type { ReactNode } from "react";

type SectionHeaderProps = {
  title: string;
  description?: string;
  eyebrow?: string;
  action?: ReactNode;
};

export function SectionHeader({
  title,
  description,
  eyebrow,
  action,
}: SectionHeaderProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-400">
            {eyebrow}
          </p>
        )}
        <h2 className="mt-1 text-base font-semibold tracking-tight text-zinc-950">
          {title}
        </h2>
        {description && <p className="mt-1 text-sm leading-5 text-zinc-500">{description}</p>}
      </div>

      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
