import type { ReactNode } from "react";

type StatusPillTone = "neutral" | "blue" | "green" | "amber" | "red";
type StatusPillDensity = "default" | "compact";

type StatusPillProps = {
  children: ReactNode;
  tone?: StatusPillTone;
  dot?: boolean;
  density?: StatusPillDensity;
};

const toneClassNames: Record<StatusPillTone, string> = {
  neutral: "bg-zinc-100 text-zinc-700 ring-zinc-200",
  blue: "bg-blue-50 text-blue-700 ring-blue-100",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-100",
  amber: "bg-amber-50 text-amber-700 ring-amber-100",
  red: "bg-red-50 text-red-700 ring-red-100",
};

const dotClassNames: Record<StatusPillTone, string> = {
  neutral: "bg-zinc-400",
  blue: "bg-blue-500",
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

// default preserva exatamente as classes originais (font-semibold, padding
// px-2.5 py-1) — os ~20 consumidores atuais não mudam de aparência. compact
// é opt-in, hoje usado somente por Clientes (fonte mais leve, sem negrito,
// padding menor; ponto e cores de tone preservados).
const sizeClassNamesByDensity: Record<StatusPillDensity, string> = {
  default: "px-2.5 py-1 text-xs font-semibold",
  compact: "px-2 py-0.5 text-[11px] font-normal",
};

export function StatusPill({
  children,
  tone = "neutral",
  dot = true,
  density = "default",
}: StatusPillProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full ring-1 ${sizeClassNamesByDensity[density]} ${toneClassNames[tone]}`}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${dotClassNames[tone]}`} />}
      {children}
    </span>
  );
}
