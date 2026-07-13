type ProgressBarTone = "neutral" | "blue" | "green" | "amber" | "red";

type ProgressBarProps = {
  value: number;
  tone?: ProgressBarTone;
  label?: string;
  className?: string;
};

const toneClassNames: Record<ProgressBarTone, string> = {
  neutral: "bg-zinc-500",
  blue: "bg-blue-600",
  green: "bg-emerald-500",
  amber: "bg-amber-500",
  red: "bg-red-500",
};

export function ProgressBar({
  value,
  tone = "blue",
  label,
  className,
}: ProgressBarProps) {
  const safeValue = Math.max(0, Math.min(100, value));

  return (
    <div className={className}>
      {label && (
        <div className="mb-1 flex items-center justify-between text-[11px] font-medium text-zinc-500">
          <span>{label}</span>
          <span>{safeValue}%</span>
        </div>
      )}

      <div className="h-2 overflow-hidden rounded-full bg-zinc-100 ring-1 ring-inset ring-zinc-200/70">
        <div
          className={`h-full rounded-full transition-all ${toneClassNames[tone]}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
}
