"use client";

import { useEffect, useRef, useState, type MouseEvent } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";

export interface MemberOption {
  id: string;
  nome: string;
  subtitulo?: string;
  corIdentificacao?: string;
  fotoUrl?: string;
}

export function MemberSelector({
  label,
  options,
  values,
  onChange,
  multiple = true,
  placeholder = "Selecionar membros…",
  emptyLabel = "Nenhum membro encontrado",
}: {
  label: string;
  options: MemberOption[];
  values: string[];
  onChange: (values: string[]) => void;
  multiple?: boolean;
  placeholder?: string;
  emptyLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: globalThis.MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selecionados = options.filter((option) => values.includes(option.id));
  const filtrados = query.trim()
    ? options.filter((option) => option.nome.toLowerCase().includes(query.trim().toLowerCase()))
    : options;

  function toggle(id: string) {
    if (multiple) {
      onChange(values.includes(id) ? values.filter((value) => value !== id) : [...values, id]);
    } else {
      onChange(values.includes(id) ? [] : [id]);
      setOpen(false);
      setQuery("");
    }
  }

  function remove(id: string, event: MouseEvent) {
    event.stopPropagation();
    onChange(values.filter((value) => value !== id));
  }

  return (
    <div className="relative" ref={containerRef}>
      <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">{label}</span>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setOpen((current) => !current);
          }
        }}
        className="flex min-h-[42px] w-full cursor-pointer items-center justify-between gap-2 rounded-xl border border-zinc-200/80 bg-zinc-50/70 px-3 py-1.5 text-left text-sm outline-none transition focus:border-indigo-300 focus:bg-white dark:border-zinc-800 dark:bg-zinc-900/60 dark:focus:bg-zinc-900"
      >
        {selecionados.length === 0 ? (
          <span className="text-zinc-400">{placeholder}</span>
        ) : (
          <div className="flex flex-1 flex-wrap items-center gap-1.5 py-0.5">
            {selecionados.map((option) => (
              <span
                key={option.id}
                className="inline-flex items-center gap-1.5 rounded-full bg-white py-0.5 pl-0.5 pr-2 ring-1 ring-zinc-200 dark:bg-zinc-800 dark:ring-zinc-700"
              >
                <Avatar
                  nome={option.nome}
                  corIdentificacao={option.corIdentificacao ?? "zinc"}
                  fotoUrl={option.fotoUrl}
                  className="h-5 w-5 rounded-full text-[10px]"
                />
                <span className="text-xs font-medium text-zinc-700 dark:text-zinc-200">{option.nome}</span>
                {multiple && (
                  <button
                    type="button"
                    onClick={(event) => remove(option.id, event)}
                    aria-label={`Remover ${option.nome}`}
                    className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
        <ChevronDown className={`h-4 w-4 shrink-0 text-zinc-400 transition ${open ? "rotate-180" : ""}`} />
      </div>

      {open && (
        <div className="absolute z-20 mt-1 w-full min-w-[260px] overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
          <div className="border-b border-zinc-100 p-2 dark:border-zinc-800">
            <span className="relative block">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
              <input
                autoFocus
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Buscar…"
                className="w-full rounded-lg border border-transparent bg-zinc-50 py-1.5 pl-8 pr-2 text-sm text-zinc-900 outline-none focus:border-indigo-300 dark:bg-zinc-800 dark:text-zinc-100"
              />
            </span>
          </div>
          <div className="max-h-60 overflow-y-auto p-1.5">
            {filtrados.length === 0 ? (
              <p className="px-3 py-2 text-sm text-zinc-400">{emptyLabel}</p>
            ) : (
              filtrados.map((option) => {
                const isSelected = values.includes(option.id);
                return (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => toggle(option.id)}
                    className={
                      isSelected
                        ? "flex w-full items-center gap-2.5 rounded-lg bg-indigo-50/60 px-2.5 py-2 text-left text-sm transition dark:bg-indigo-500/10"
                        : "flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm transition hover:bg-zinc-50 dark:hover:bg-zinc-800"
                    }
                  >
                    <Avatar
                      nome={option.nome}
                      corIdentificacao={option.corIdentificacao ?? "zinc"}
                      fotoUrl={option.fotoUrl}
                      className="h-7 w-7 shrink-0 rounded-full text-xs"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-zinc-800 dark:text-zinc-100">{option.nome}</p>
                      {option.subtitulo && <p className="truncate text-xs text-zinc-400">{option.subtitulo}</p>}
                    </div>
                    {isSelected && <Check className="h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400" />}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
