"use client";

import { Check } from "lucide-react";

interface MultiSelectOption {
  value: string;
  label: string;
}

interface MultiSelectProps {
  label: string;
  placeholder?: string;
  values: string[];
  onChange: (values: string[]) => void;
  options: MultiSelectOption[];
}

export function MultiSelect({ label, values, onChange, options }: MultiSelectProps) {
  function toggle(value: string) {
    if (values.includes(value)) {
      onChange(values.filter((item) => item !== value));
    } else {
      onChange([...values, value]);
    }
  }

  return (
    <div className="text-sm">
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">{label}</span>
      <div className="flex flex-wrap gap-1.5 rounded-xl border border-zinc-200/80 bg-zinc-50/70 p-2 dark:border-zinc-800 dark:bg-zinc-900/60">
        {options.map((option) => {
          const active = values.includes(option.value);
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => toggle(option.value)}
              aria-pressed={active}
              className={
                active
                  ? "inline-flex items-center gap-1 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 px-3 py-1 text-xs font-semibold text-white"
                  : "inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-xs font-medium text-zinc-600 ring-1 ring-zinc-200 hover:bg-zinc-100 dark:bg-zinc-900 dark:text-zinc-300 dark:ring-zinc-700"
              }
            >
              {active && <Check className="h-3.5 w-3.5" />}
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
