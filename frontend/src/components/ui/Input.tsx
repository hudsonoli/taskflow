import type { InputHTMLAttributes } from "react";
import clsx from "clsx";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, className, disabled, ...props }: InputProps) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{label}</span>
      <input
        disabled={disabled}
        className={clsx(
          "field w-full rounded-xl px-3 py-2.5 text-sm",
          className,
        )}
        {...props}
      />
    </label>
  );
}
