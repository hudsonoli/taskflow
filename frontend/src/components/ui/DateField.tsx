"use client";

import { useId, useRef, useState } from "react";
import { CalendarDays } from "lucide-react";
import clsx from "clsx";
import { PainelFlutuante } from "@/components/filtros/PainelFlutuante";
import { formatarDataBr, interpretarData, parseDataBr, sanitizarData } from "@/lib/data-hora-campo";
import { Calendario } from "./Calendario";

/**
 * Campo só de DATA do TaskFlow (substitui o `<input type="date">` nativo): digitação em DD/MM/AAAA ou calendário compacto (o mesmo `Calendario` do DateTimeField, no mesmo `PainelFlutuante`).
 * O contrato com o formulário é o do campo nativo: `value`/`onChange` usam "YYYY-MM-DD" ou "" — data completa e válida sobe como ISO; vazio, parcial ou inválido sobe como "" (como o nativo fazia).
 * Nada é salvo por conta própria: quem salva é o botão/envio do formulário. `min`/`max` só tornam os dias inertes no calendário; a validação de intervalo segue com o formulário.
 * `anulavel` mostra "Limpar" no calendário. Sem tema próprio: o estilo visual opcional vem do atributo global do <html> (globals.css).
 */
export function DateField({
  label,
  rotuloAcessivel,
  value,
  onChange,
  disabled = false,
  readOnly = false,
  anulavel = true,
  min,
  max,
  className,
}: {
  label: string;
  /** nome acessível do campo quando precisa ser mais específico que o rótulo visível (ex.: inclui a etapa) */
  rotuloAcessivel?: string;
  /** "YYYY-MM-DD" ou "" */
  value: string;
  onChange?: (valor: string) => void;
  disabled?: boolean;
  readOnly?: boolean;
  /** permite limpar pelo calendário */
  anulavel?: boolean;
  min?: string;
  max?: string;
  className?: string;
}) {
  const id = useId();
  const [texto, setTexto] = useState(formatarDataBr(value));
  const [tocou, setTocou] = useState(false);
  const [valorVisto, setValorVisto] = useState(value);
  const [ancora, setAncora] = useState<HTMLDivElement | null>(null);
  const [aberto, setAberto] = useState(false);
  const [focarCalendario, setFocarCalendario] = useState(false);
  const entradaRef = useRef<HTMLInputElement>(null);

  // O valor mudou POR FORA (abriu o formulário, reverteu, limpou): o texto acompanha — comparado no render (padrão do projeto), sem tocar no que a pessoa digita quando já equivale ao valor.
  if (value !== valorVisto) {
    setValorVisto(value);
    if (interpretarData(texto).valor !== value) {
      setTexto(formatarDataBr(value));
      setTocou(false);
    }
  }

  const erro = tocou ? interpretarData(texto).erro : null;
  const bloqueado = disabled || readOnly;
  const idErro = `${id}-erro`;

  function fechar() {
    setAberto(false);
    setFocarCalendario(false);
  }

  function emitir(proximoTexto: string) {
    const { valor } = interpretarData(proximoTexto);
    if (valor !== value) onChange?.(valor);
  }

  function aoEscolherDia(iso: string) {
    const dataBr = formatarDataBr(iso);
    setTexto(dataBr);
    setTocou(true);
    fechar();
    emitir(dataBr);
    entradaRef.current?.focus();
  }

  function aoLimpar() {
    setTexto("");
    setTocou(false);
    fechar();
    if (value !== "") onChange?.("");
    entradaRef.current?.focus();
  }

  function aoSair() {
    setTocou(true);
    const normalizada = parseDataBr(texto);
    if (normalizada) setTexto(formatarDataBr(normalizada)); // "1/2/2026" → "01/02/2026"
  }

  return (
    <div className={clsx("block text-sm", className)}>
      <span id={`${id}-rotulo`} className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
        {label}
      </span>
      <div ref={setAncora} tabIndex={-1} onFocus={(evento) => evento.target === evento.currentTarget && entradaRef.current?.focus()} className="relative">
        <input
          ref={entradaRef}
          id={`${id}-data`}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          spellCheck={false}
          placeholder="DD/MM/AAAA"
          aria-label={rotuloAcessivel ?? `${label} — data`}
          aria-invalid={Boolean(erro)}
          aria-describedby={erro ? idErro : undefined}
          disabled={disabled}
          readOnly={readOnly}
          value={texto}
          maxLength={10}
          onChange={(evento) => {
            const proximo = sanitizarData(evento.target.value);
            setTexto(proximo);
            emitir(proximo);
          }}
          onBlur={aoSair}
          onClick={() => !bloqueado && setAberto(true)}
          onKeyDown={(evento) => {
            if (evento.key === "ArrowDown" && !bloqueado) {
              evento.preventDefault();
              setFocarCalendario(true);
              setAberto(true);
            }
          }}
          className={clsx("field w-full rounded-xl py-2.5 pl-3 pr-9 text-sm tabular-nums", erro && "border-red-400 dark:border-red-500/60")}
        />
        <button
          type="button"
          aria-label="Abrir calendário"
          aria-haspopup="dialog"
          aria-expanded={aberto}
          disabled={bloqueado}
          onClick={() => {
            setFocarCalendario(true);
            setAberto((atual) => !atual);
          }}
          className="absolute right-1.5 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-lg text-fg-subtle transition hover:bg-zinc-100 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-zinc-800"
        >
          <CalendarDays className="h-4 w-4" aria-hidden />
        </button>
      </div>
      {erro && (
        <p id={idErro} role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}

      {aberto && ancora && !bloqueado && (
        <PainelFlutuante ancora={ancora} rotulo={`Calendário — ${label}`} superficie="calendario" largura={296} onFechar={fechar}>
          <Calendario
            valor={parseDataBr(texto) ?? ""}
            aoEscolher={aoEscolherDia}
            aoLimpar={anulavel ? aoLimpar : undefined}
            aoFechar={() => {
              fechar();
              entradaRef.current?.focus();
            }}
            focarAoAbrir={focarCalendario}
            min={min}
            max={max}
          />
        </PainelFlutuante>
      )}
    </div>
  );
}
