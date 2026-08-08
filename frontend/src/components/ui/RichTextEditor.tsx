"use client";

import { useEffect, useRef } from "react";
import { Bold, Eraser } from "lucide-react";

const HIGHLIGHT_COLORS = [
  { label: "Amarelo", value: "#fef08a" },
  { label: "Verde", value: "#bbf7d0" },
  { label: "Rosa", value: "#fecdd3" },
];

const FONT_COLORS = [
  { label: "Azul", value: "#1d4ed8" },
  { label: "Vermelho", value: "#b91c1c" },
  { label: "Verde", value: "#15803d" },
];

export function RichTextEditor({ value, onChange }: { value: string; onChange: (html: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current && ref.current.innerHTML !== value) {
      ref.current.innerHTML = value;
    }
    // Só define o conteúdo inicial: reescrever o innerHTML a cada digitação reseta o cursor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function exec(command: string, arg?: string) {
    ref.current?.focus();
    document.execCommand(command, false, arg);
    if (ref.current) onChange(ref.current.innerHTML);
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-1.5 rounded-xl border border-zinc-200 bg-zinc-50/70 p-1.5 dark:border-zinc-700 dark:bg-zinc-800/60">
        <button
          type="button"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => exec("bold")}
          className="rounded-lg p-1.5 text-zinc-600 hover:bg-white dark:text-zinc-300 dark:hover:bg-zinc-900"
          title="Negrito"
          aria-label="Negrito"
        >
          <Bold size={14} />
        </button>

        <div className="mx-1 h-4 w-px bg-zinc-200 dark:bg-zinc-700" />
        <span className="px-0.5 text-xs text-zinc-400">Grifo</span>
        {HIGHLIGHT_COLORS.map((color) => (
          <button
            key={color.value}
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => exec("hiliteColor", color.value)}
            className="h-5 w-5 rounded-full ring-1 ring-zinc-200 transition hover:scale-110 dark:ring-zinc-700"
            style={{ backgroundColor: color.value }}
            title={`Grifar em ${color.label.toLowerCase()}`}
            aria-label={`Grifar em ${color.label.toLowerCase()}`}
          />
        ))}

        <div className="mx-1 h-4 w-px bg-zinc-200 dark:bg-zinc-700" />
        <span className="px-0.5 text-xs text-zinc-400">Cor</span>
        {FONT_COLORS.map((color) => (
          <button
            key={color.value}
            type="button"
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => exec("foreColor", color.value)}
            className="h-5 w-5 rounded-full ring-1 ring-zinc-200 transition hover:scale-110 dark:ring-zinc-700"
            style={{ backgroundColor: color.value }}
            title={`Fonte em ${color.label.toLowerCase()}`}
            aria-label={`Fonte em ${color.label.toLowerCase()}`}
          />
        ))}

        <button
          type="button"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => exec("removeFormat")}
          className="ml-auto flex items-center gap-1 rounded-lg px-2 py-1 text-xs text-zinc-500 hover:bg-white dark:text-zinc-400 dark:hover:bg-zinc-900"
          title="Limpar formatação"
          aria-label="Limpar formatação"
        >
          <Eraser size={12} />
          Limpar
        </button>
      </div>

      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        onInput={() => ref.current && onChange(ref.current.innerHTML)}
        className="min-h-[180px] rounded-xl border border-zinc-200 bg-zinc-50/70 px-3 py-2.5 text-sm leading-6 text-zinc-900 outline-none transition focus:border-indigo-300 focus:bg-white focus:shadow-sm dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-100 dark:focus:bg-zinc-900"
      />
    </div>
  );
}
