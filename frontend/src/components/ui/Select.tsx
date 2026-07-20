type SelectOption = {
  value: string;
  label: string;
};

type SelectDensity = "compact" | "default";

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: SelectOption[];
  density?: SelectDensity;
};

// Mesma régua de Input.tsx: compact menor/mais leve, default inalterado.
const labelClassNames: Record<SelectDensity, string> = {
  compact: "mb-1 block text-[11px] font-normal text-zinc-500",
  default: "mb-1 block font-medium text-zinc-700",
};

const fieldPaddingClassNames: Record<SelectDensity, string> = {
  compact: "px-3 py-1.5",
  default: "px-3 py-2",
};

const fieldTextClassNames: Record<SelectDensity, string> = {
  compact: "text-[12px]",
  default: "text-sm",
};

export function Select({
  label,
  options,
  className,
  density = "default",
  ...rest
}: SelectProps) {
  return (
    <label className="block text-sm">
      <span className={labelClassNames[density]}>{label}</span>

      <select
        className={`w-full rounded-2xl border border-zinc-200 bg-white ${fieldPaddingClassNames[density]} ${fieldTextClassNames[density]} text-zinc-900 outline-none transition focus:border-zinc-400 focus:ring-2 focus:ring-zinc-900/10 disabled:cursor-not-allowed disabled:bg-zinc-50 disabled:text-zinc-400 ${className ?? ""}`}
        {...rest}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
