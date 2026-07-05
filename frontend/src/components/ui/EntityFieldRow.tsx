"use client";

import type { ReactNode } from "react";

type EntityFieldRowProps = {
  label: string;
  value?: ReactNode;
  emptyValue?: string;
  variant?: "default" | "muted" | "badge";
  className?: string;
};

export function EntityFieldRow({
  label,
  value,
  emptyValue = "-",
  variant = "default",
  className = "",
}: EntityFieldRowProps) {
  const isEmpty = value === undefined || value === null || value === "";

  const valueClassName =
    variant === "muted"
      ? "text-sm text-zinc-500"
      : variant === "badge"
        ? "text-sm"
        : "text-sm font-medium text-zinc-900";

  return (
    <div className={`grid gap-1 ${className}`.trim()}>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-zinc-400">
        {label}
      </dt>
      <dd className={valueClassName}>{isEmpty ? emptyValue : value}</dd>
    </div>
  );
}
