import type { SelectHTMLAttributes } from "react";
import clsx from "clsx";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
}

export function Select({ label, options, className, ...props }: SelectProps) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{label}</span>
      <select
        className={clsx(
          "field w-full rounded-xl px-3 py-2.5 text-sm",
          className,
        )}
        {...props}
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
