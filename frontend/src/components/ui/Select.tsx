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
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">{label}</span>
      <select
        className={clsx(
          "w-full rounded-xl border border-zinc-200/80 bg-zinc-50/70 px-3 py-2.5 text-sm text-zinc-900 outline-none transition focus:border-indigo-300 focus:bg-white focus:shadow-sm",
          "dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100 dark:focus:bg-zinc-900",
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
