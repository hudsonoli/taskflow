"use client";

import { useId, useRef, useState } from "react";
import { CalendarDays } from "lucide-react";
import clsx from "clsx";
import { PainelFlutuante } from "@/components/filtros/PainelFlutuante";
import {
  formatarDataBr,
  interpretarTextos,
  MENSAGEM_DATA_OBRIGATORIA,
  parseDataBr,
  parseHora,
  sanitizarData,
  sanitizarHora,
  separarValor,
} from "@/lib/data-hora-campo";
import { Calendario } from "./Calendario";

/**
 * Campo de DATA + HORA do TaskFlow (substitui o `datetime-local` nativo): a data abre um calendário compacto (só data) e a hora é DIGITADA em HH:MM — sem listas, rodas nem spinners.
 * O contrato com o formulário é o do campo antigo: `value`/`onChange` usam "YYYY-MM-DDTHH:MM" no relógio local, sem fuso, ou "" (sem valor); a conversão para o instante da API segue em
 * `lib/prazo-operacional.ts`. Só valores COMPLETOS e válidos sobem (`onChange`): digitação parcial ("10:", "21/10") fica no campo sem bloquear nem emitir nada, e nenhuma hora é inventada.
 * `onCommit` dispara quando a pessoa conclui a edição (sai de um dos campos, escolhe um dia, Hoje ou Limpar) com um valor completo ou vazio — o gatilho de quem salva ao concluir.
 * Estrutura sem tema próprio (usa os tokens do TaskFlow): a parte visual pode ser trocada depois sem tocar na lógica.
 */
export function DateTimeField({
  label,
  value,
  onChange,
  onCommit,
  disabled = false,
  readOnly = false,
  exigeHora = true,
  anulavel = true,
  className,
}: {
  label: string;
  /** "YYYY-MM-DDTHH:MM" (relógio local) ou "" */
  value: string;
  onChange?: (valor: string) => void;
  onCommit?: (valor: string) => void;
  disabled?: boolean;
  readOnly?: boolean;
  /** data sem horário é pendência (padrão): nunca vira 00:00 sozinha */
  exigeHora?: boolean;
  /** permite limpar (volta a "") */
  anulavel?: boolean;
  className?: string;
}) {
  const id = useId();
  const inicial = separarValor(value);
  const [textoData, setTextoData] = useState(formatarDataBr(inicial.data));
  const [textoHora, setTextoHora] = useState(inicial.hora);
  const [tocouData, setTocouData] = useState(false);
  const [tocouHora, setTocouHora] = useState(false);
  const [valorVisto, setValorVisto] = useState(value);
  // Último valor que JÁ foi concluído (`onCommit`): escolher o dia no calendário e depois sair do campo concluem o MESMO valor — só o primeiro conta, para não haver dois salvamentos enquanto o primeiro ainda está em voo.
  const [comprometido, setComprometido] = useState(value);
  const [ancora, setAncora] = useState<HTMLDivElement | null>(null);
  const [aberto, setAberto] = useState(false);
  const [focarCalendario, setFocarCalendario] = useState(false);
  const entradaDataRef = useRef<HTMLInputElement>(null);
  const entradaHoraRef = useRef<HTMLInputElement>(null);

  // O valor mudou POR FORA (hidratação, salvou, reverteu): os textos acompanham — comparado no render (padrão do projeto), sem tocar no que a pessoa digita quando já equivale ao valor.
  if (value !== valorVisto) {
    setValorVisto(value);
    if (interpretarTextos(textoData, textoHora, { exigeHora }).valor !== value) {
      // vindo de fora (hidratou, reverteu por falha): é o novo ponto de partida e pode ser concluído de novo. O eco da PRÓPRIA digitação (textos já equivalem ao valor) não conta como concluído.
      setComprometido(value);
      const partes = separarValor(value);
      setTextoData(formatarDataBr(partes.data));
      setTextoHora(partes.hora);
      setTocouData(false);
      setTocouHora(false);
    }
  }

  const interpretado = interpretarTextos(textoData, textoHora, { exigeHora });
  const esvaziadoObrigatorio = !anulavel && textoData.trim() === "" && textoHora.trim() === "" && (tocouData || tocouHora);
  const erroData = esvaziadoObrigatorio ? MENSAGEM_DATA_OBRIGATORIA : tocouData || (tocouHora && textoData.trim() === "") ? interpretado.erroData : null;
  const erroHora = tocouHora ? interpretado.erroHora : null;
  const bloqueado = disabled || readOnly;

  function fechar() {
    setAberto(false);
    setFocarCalendario(false);
  }

  function emitir(proximaData: string, proximaHora: string, { concluir }: { concluir: boolean }) {
    const estado = interpretarTextos(proximaData, proximaHora, { exigeHora });
    if (estado.valor === undefined) return; // parcial/inválido: nada sobe
    if (estado.valor === "" && !anulavel) return; // campo obrigatório: esvaziar não é um valor
    if (estado.valor !== value) onChange?.(estado.valor);
    if (concluir && estado.valor !== comprometido) {
      setComprometido(estado.valor);
      onCommit?.(estado.valor);
    }
  }

  function aoEscolherDia(iso: string) {
    const dataBr = formatarDataBr(iso);
    setTextoData(dataBr);
    setTocouData(true);
    fechar();
    if (textoHora.trim() === "") {
      // escolhida a data, o próximo passo natural é a hora
      entradaHoraRef.current?.focus();
      return;
    }
    emitir(dataBr, textoHora, { concluir: true });
    entradaDataRef.current?.focus();
  }

  function aoLimpar() {
    setTextoData("");
    setTextoHora("");
    setTocouData(false);
    setTocouHora(false);
    fechar();
    if (value !== "") onChange?.("");
    if (comprometido !== "") {
      setComprometido("");
      onCommit?.("");
    }
    entradaDataRef.current?.focus();
  }

  function sairDaData() {
    setTocouData(true);
    const normalizada = parseDataBr(textoData);
    if (normalizada) setTextoData(formatarDataBr(normalizada)); // "1/2/2026" → "01/02/2026"
    emitir(normalizada ? formatarDataBr(normalizada) : textoData, textoHora, { concluir: true });
  }

  function sairDaHora() {
    setTocouHora(true);
    const normalizada = parseHora(textoHora);
    if (normalizada) setTextoHora(normalizada); // "5:49" → "05:49"
    emitir(textoData, normalizada ?? textoHora, { concluir: true });
  }

  const descricaoErro = erroData ?? erroHora;
  const idErro = `${id}-erro`;

  return (
    <div className={clsx("block text-sm", className)}>
      <span id={`${id}-rotulo`} className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
        {label}
      </span>
      <div role="group" aria-labelledby={`${id}-rotulo`} className="flex items-start gap-2">
        <div ref={setAncora} tabIndex={-1} onFocus={(evento) => evento.target === evento.currentTarget && entradaDataRef.current?.focus()} className="relative min-w-0 flex-1">
          <input
            ref={entradaDataRef}
            id={`${id}-data`}
            type="text"
            inputMode="numeric"
            autoComplete="off"
            spellCheck={false}
            placeholder="DD/MM/AAAA"
            aria-label={`${label} — data`}
            aria-invalid={Boolean(erroData)}
            aria-describedby={descricaoErro ? idErro : undefined}
            disabled={disabled}
            readOnly={readOnly}
            value={textoData}
            maxLength={10}
            onChange={(evento) => {
              const proximo = sanitizarData(evento.target.value);
              setTextoData(proximo);
              emitir(proximo, textoHora, { concluir: false });
            }}
            onBlur={sairDaData}
            onClick={() => !bloqueado && setAberto(true)}
            onKeyDown={(evento) => {
              if (evento.key === "ArrowDown" && !bloqueado) {
                evento.preventDefault();
                setFocarCalendario(true);
                setAberto(true);
              }
            }}
            className={clsx("field w-full rounded-xl py-2.5 pl-3 pr-9 text-sm tabular-nums", erroData && "border-red-400 dark:border-red-500/60")}
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
        <input
          ref={entradaHoraRef}
          id={`${id}-hora`}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          spellCheck={false}
          placeholder="HH:MM"
          aria-label={`${label} — horário`}
          aria-invalid={Boolean(erroHora)}
          aria-describedby={descricaoErro ? idErro : undefined}
          disabled={disabled}
          readOnly={readOnly}
          value={textoHora}
          maxLength={5}
          onChange={(evento) => {
            const proximo = sanitizarHora(evento.target.value);
            setTextoHora(proximo);
            emitir(textoData, proximo, { concluir: false });
          }}
          onBlur={sairDaHora}
          className={clsx("field w-[5.25rem] shrink-0 rounded-xl px-3 py-2.5 text-center text-sm tabular-nums", erroHora && "border-red-400 dark:border-red-500/60")}
        />
      </div>
      {descricaoErro && (
        <p id={idErro} role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
          {descricaoErro}
        </p>
      )}

      {aberto && ancora && !bloqueado && (
        <PainelFlutuante
          ancora={ancora}
          rotulo={`Calendário — ${label}`}
          largura={296}
          onFechar={fechar}
        >
          <Calendario
            valor={parseDataBr(textoData) ?? ""}
            aoEscolher={aoEscolherDia}
            aoLimpar={anulavel ? aoLimpar : undefined}
            aoFechar={() => {
              fechar();
              entradaDataRef.current?.focus();
            }}
            focarAoAbrir={focarCalendario}
          />
        </PainelFlutuante>
      )}
    </div>
  );
}
