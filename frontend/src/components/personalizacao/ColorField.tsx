"use client";

import { useId } from "react";
import clsx from "clsx";
import { contraste, corSobre, hexValido } from "@/lib/branding-tokens";

// Seletor de cor (color picker nativo + campo hexadecimal). O texto digitado pode estar incompleto enquanto a
// pessoa digita; só um #RRGGBB válido é propagado como cor.
export function ColorField({
  label,
  descricao,
  valor,
  padrao,
  onChange,
}: {
  label: string;
  descricao: string;
  /** cor padrão do TaskFloww (usada como exemplo no campo vazio) */
  padrao: string;
  valor: string;
  onChange: (valor: string) => void;
}) {
  const id = useId();
  const valido = hexValido(valor);
  const sobre = valido ? corSobre(valor) : null;
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          type="color"
          aria-label={`${label} — seletor de cor`}
          value={valido ? valor : "#000000"}
          onChange={(event) => onChange(event.target.value.toLowerCase())}
          className="h-10 w-12 shrink-0 cursor-pointer rounded-lg border border-field-line bg-field p-1"
        />
        <input
          id={id}
          type="text"
          spellCheck={false}
          autoComplete="off"
          maxLength={7}
          value={valor}
          aria-invalid={!valido}
          aria-describedby={`${id}-ajuda`}
          onChange={(event) => onChange(event.target.value.trim())}
          placeholder={padrao}
          className="field w-32 rounded-xl px-3 py-2.5 font-mono text-sm"
        />
        {valido && sobre && (
          <span
            className="flex h-10 min-w-0 flex-1 items-center justify-center rounded-xl px-3 text-xs font-semibold"
            style={{ backgroundColor: valor, color: sobre }}
          >
            Texto sobre a cor · {contraste(valor, sobre).toFixed(1)}:1
          </span>
        )}
      </div>
      <p id={`${id}-ajuda`} className={clsx("mt-1.5 text-xs", valido ? "text-fg-muted" : "text-danger")}>
        {valido ? descricao : `Use o formato #RRGGBB (ex.: ${padrao}).`}
      </p>
    </div>
  );
}
