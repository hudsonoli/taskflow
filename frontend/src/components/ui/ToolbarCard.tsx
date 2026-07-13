import type { ReactNode } from "react";

type ToolbarCardProps = {
  children: ReactNode;
  className?: string;
};

export function ToolbarCard({ children, className }: ToolbarCardProps) {
  return (
    <div
      className={`rounded-3xl border border-zinc-100 bg-white/95 p-4 shadow-sm ${className ?? ""}`}
    >
      {children}
    </div>
  );
}
