type SwitchProps = {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  label?: string;
  className?: string;
};

export function Switch({ checked, onCheckedChange, label, className }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onCheckedChange(!checked)}
      className={`relative inline-flex h-7 w-12 items-center rounded-full transition ${checked ? "bg-zinc-900" : "bg-zinc-200"} ${className ?? ""}`}
    >
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition ${checked ? "translate-x-6" : "translate-x-1"}`}
      />
    </button>
  );
}
