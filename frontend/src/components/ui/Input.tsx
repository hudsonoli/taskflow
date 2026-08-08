import type { InputHTMLAttributes } from "react";
import clsx from "clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, className, disabled, ...props }: InputProps) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">{label}</span>
      <input
        disabled={disabled}
        className={clsx(
          "w-full rounded-xl border border-zinc-200/80 bg-zinc-50/70 px-3 py-2.5 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm disabled:text-zinc-400",
          "dark:border-zinc-800 dark:bg-zinc-900/60 dark:text-zinc-100 dark:focus:bg-zinc-900",
          className,
        )}
        {...props}
      />
    </label>
  );
}
