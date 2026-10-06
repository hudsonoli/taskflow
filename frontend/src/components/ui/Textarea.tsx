import type { TextareaHTMLAttributes } from "react";
import clsx from "clsx";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
}

export function Textarea({ label, className, ...props }: TextareaProps) {
  return (
    <label className="block text-sm">
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{label}</span>
      <textarea
        className={clsx(
          "field w-full rounded-xl px-3 py-2.5 text-sm",
          className,
        )}
        {...props}
      />
    </label>
  );
}
