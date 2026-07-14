"use client";

import type { ReactNode } from "react";

type EntityFieldRowDensity = "compact" | "default";

type EntityFieldRowProps = {
  label: string;
  value?: ReactNode;
  emptyValue?: string;
  variant?: "default" | "muted" | "badge";
  density?: EntityFieldRowDensity;
  className?: string;
};

// compact segue a régua dos badges (label leve, valor sem negrito); default
// permanece byte-a-byte igual ao original — GruposClientesView (único outro
// consumidor) usa density="default" e não muda de aparência.
const labelClassNames: Record<EntityFieldRowDensity, string> = {
  compact: "text-[10px] font-normal uppercase tracking-wide text-zinc-400",
  default: "text-[11px] font-medium uppercase tracking-wide text-zinc-400",
};

const valueSizeClassNames: Record<EntityFieldRowDensity, string> = {
  compact: "text-[11px]",
  default: "text-sm",
};

const valueFontWeightClassNames: Record<EntityFieldRowDensity, string> = {
  compact: "font-normal",
  default: "font-medium",
};

export function EntityFieldRow({
  label,
  value,
  emptyValue = "-",
  variant = "default",
  density = "default",
  className = "",
}: EntityFieldRowProps) {
  const isEmpty = value === undefined || value === null || value === "";
  const sizeClassName = valueSizeClassNames[density];

  const valueClassName =
    variant === "muted"
      ? `${sizeClassName} text-zinc-500`
      : variant === "badge"
        ? sizeClassName
        : `${sizeClassName} ${valueFontWeightClassNames[density]} text-zinc-900`;

  return (
    <div className={`grid min-w-0 gap-1 ${className}`.trim()}>
      <dt className={labelClassNames[density]}>{label}</dt>
      <dd className={`min-w-0 break-words [overflow-wrap:anywhere] ${valueClassName}`}>
        {isEmpty ? emptyValue : value}
      </dd>
    </div>
  );
}
