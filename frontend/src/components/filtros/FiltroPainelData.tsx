"use client";

import { useId, useState } from "react";
import { Check } from "lucide-react";
import { ROTULO_OPERADOR, dataIsoValida, formatarDataIso } from "@/lib/filtros-avancados";
import type { DefinicaoFiltro, FiltroAtivo, OperadorFiltro } from "@/types/filtros";

const OPERADORES_DATA: OperadorFiltro[] = ["is", "before", "after"];

/**
 * Editor de um filtro de data: operador (é / antes de / depois de), atalhos relativos a hoje (só com "é") e o seletor de
 * data real. Aplica a cada escolha — não há botão "OK". Sem filtro ainda, a primeira escolha o cria.
 */
export function FiltroPainelData({
  definicao,
  filtro,
  onAplicar,
}: {
  definicao: DefinicaoFiltro;
  filtro: FiltroAtivo | undefined;
  onAplicar: (operador: OperadorFiltro, valor: string) => void;
}) {
  const nome = useId();
  // Sem filtro ainda, o operador escolhido fica só aqui até a pessoa indicar a data (aí o filtro nasce).
  const [operadorPendente, setOperadorPendente] = useState<OperadorFiltro>("is");
  const operador = filtro?.operador ?? operadorPendente;
  const valor = filtro?.valores[0] ?? "";
  const dataReal = dataIsoValida(valor) ? valor : "";
  const presets = operador === "is" ? (definicao.presets ?? []) : [];

  return (
    <div className="flex flex-col gap-3 p-3">
      <div role="radiogroup" aria-label={`Operador de ${definicao.label}`} className="grid grid-cols-3 gap-1 rounded-lg bg-surface-hover p-0.5">
        {OPERADORES_DATA.map((candidato) => (
          <label
            key={candidato}
            className={`cursor-pointer rounded-md px-2 py-1 text-center text-[11px] font-medium has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus ${
              operador === candidato ? "bg-surface text-fg shadow-sm" : "text-fg-muted hover:text-fg"
            }`}
          >
            <input
              type="radio"
              name={nome}
              value={candidato}
              checked={operador === candidato}
              onChange={() => {
                if (!filtro) {
                  setOperadorPendente(candidato);
                  return;
                }
                // "antes de"/"depois de" exigem uma data real: um atalho ("hoje", "atrasado") vira a data de hoje
                const exigeData = candidato !== "is" && !dataIsoValida(valor);
                onAplicar(candidato, exigeData ? formatarDataIso(new Date()) : valor);
              }}
              className="sr-only"
            />
            {ROTULO_OPERADOR[candidato]}
          </label>
        ))}
      </div>

      {presets.length > 0 && (
        <div role="group" aria-label="Atalhos" className="flex flex-wrap gap-1.5">
          {presets.map((preset) => {
            const marcado = valor === preset.value;
            return (
              <button
                key={preset.value}
                type="button"
                aria-pressed={marcado}
                onClick={() => onAplicar("is", preset.value)}
                className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                  marcado ? "border-transparent bg-brand-gradient" : "border-line-strong text-fg-muted hover:text-fg"
                }`}
              >
                {marcado && <Check className="h-3 w-3" aria-hidden />}
                {preset.label}
              </button>
            );
          })}
        </div>
      )}

      <label className="block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
        Data
        <input
          type="date"
          value={dataReal}
          onChange={(evento) => {
            if (evento.target.value) onAplicar(operador, evento.target.value);
          }}
          className="field mt-1 w-full rounded-lg px-2.5 py-1.5 text-xs normal-case tracking-normal"
        />
      </label>
    </div>
  );
}
