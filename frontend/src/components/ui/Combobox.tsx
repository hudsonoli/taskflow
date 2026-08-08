"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Search, X } from "lucide-react";
import clsx from "clsx";

interface ComboboxOption {
  value: string;
  label: string;
}

export function Combobox({
  label,
  value,
  onChange,
  options,
  placeholder = "Buscar…",
  emptyLabel = "Nenhum resultado",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: ComboboxOption[];
  placeholder?: string;
  emptyLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = query.trim()
    ? options.filter((option) => option.label.toLowerCase().includes(query.trim().toLowerCase()))
    : options;

  return (
    <div className="relative" ref={containerRef}>
      <label className="block text-sm">
        <span className="mb-1 block font-medium text-zinc-700 dark:text-zinc-300">{label}</span>
        <span className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400" />
          <input
            value={open ? query : (selected?.label ?? "")}
            onChange={(event) => {
              setQuery(event.target.value);
              if (!open) setOpen(true);
            }}
            onFocus={() => {
              setOpen(true);
              setQuery("");
            }}
            placeholder={placeholder}
            className="w-full rounded-xl border border-zinc-200 bg-zinc-50/70 py-2.5 pl-9 pr-8 text-sm text-zinc-900 outline-none transition placeholder:text-zinc-400 focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
          />
          {value && (
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onChange("");
                setQuery("");
              }}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              aria-label="Limpar seleção"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </span>
      </label>

      {open && (
        <div className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-zinc-200 bg-white p-1 shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
          {filtered.length === 0 ? (
            <p className="px-3 py-2 text-sm text-zinc-400">{emptyLabel}</p>
          ) : (
            filtered.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => {
                  onChange(option.value);
                  setOpen(false);
                  setQuery("");
                }}
                className={clsx(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition hover:bg-zinc-50 dark:hover:bg-zinc-800",
                  option.value === value
                    ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400"
                    : "text-zinc-700 dark:text-zinc-200",
                )}
              >
                {option.label}
                {option.value === value && <Check className="h-3.5 w-3.5" />}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
