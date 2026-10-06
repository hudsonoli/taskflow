"use client";

export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled = false,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
}) {
  const track = (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={!label ? "Alternar" : undefined}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-10 shrink-0 items-center rounded-full transition-colors duration-200 ease-out focus:outline-none focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-surface ${
        disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"
      } ${checked ? "bg-emerald-600 dark:bg-emerald-500" : "bg-field-line"}`}
    >
      <span
        className={`pointer-events-none inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow-[0_1px_2px_rgba(0,0,0,0.25)] transition-transform duration-200 ease-out ${
          checked ? "translate-x-[19px]" : "translate-x-[3px]"
        }`}
      />
    </button>
  );

  if (!label && !description) return track;

  return (
    <label className={`flex items-center justify-between gap-3 ${disabled ? "opacity-50" : "cursor-pointer"}`}>
      <span className="min-w-0">
        {label && <span className="block text-sm font-medium text-fg">{label}</span>}
        {description && <span className="block text-xs text-fg-muted">{description}</span>}
      </span>
      {track}
    </label>
  );
}
