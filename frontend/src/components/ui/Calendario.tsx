"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import clsx from "clsx";
import { deIso, montarGrade, NOMES_DOS_MESES, paraIso, ROTULOS_SEMANA, rotuloDoDia, somarDias, somarMeses } from "@/lib/data-hora-campo";

/**
 * Calendário compacto (só DATA — nada de lista de horas/minutos; a hora é outro controle). Neutro: usa os tokens atuais do TaskFlow e não tem lógica de tema, para poder ser
 * estilizado depois sem tocar no comportamento. Semana de domingo a sábado (pt-BR). Teclado: setas movem o dia, Home/End o início/fim da semana, PageUp/PageDown o mês,
 * Enter/Espaço escolhem. O dia atual e o escolhido são distinguíveis sem depender só de cor (anel vs. preenchimento + `aria-current`/`aria-selected`).
 */
export function Calendario({
  valor,
  aoEscolher,
  aoLimpar,
  aoFechar,
  focarAoAbrir = true,
}: {
  /** "YYYY-MM-DD" ou "" */
  valor: string;
  aoEscolher: (iso: string) => void;
  /** presente = o campo é anulável: mostra "Limpar" */
  aoLimpar?: () => void;
  aoFechar?: () => void;
  focarAoAbrir?: boolean;
}) {
  const hoje = paraIso(new Date());
  const inicial = deIso(valor) ? valor : hoje;
  const [focado, setFocado] = useState(inicial);
  const [mes, setMes] = useState(() => {
    const d = deIso(inicial) ?? new Date();
    return { ano: d.getFullYear(), mes: d.getMonth() + 1 };
  });
  const gradeRef = useRef<HTMLDivElement>(null);
  const [devolverFoco, setDevolverFoco] = useState(focarAoAbrir);

  useEffect(() => {
    if (!devolverFoco) return;
    gradeRef.current?.querySelector<HTMLButtonElement>(`[data-dia="${focado}"]`)?.focus({ preventScroll: true });
  }, [focado, mes, devolverFoco]);

  function irParaMes(iso: string) {
    const d = deIso(iso);
    if (d) setMes({ ano: d.getFullYear(), mes: d.getMonth() + 1 });
  }

  function mover(iso: string) {
    setFocado(iso);
    irParaMes(iso);
    setDevolverFoco(true);
  }

  function aoTeclar(evento: KeyboardEvent) {
    const d = deIso(focado);
    if (!d) return;
    const passos: Record<string, () => string> = {
      ArrowLeft: () => somarDias(focado, -1),
      ArrowRight: () => somarDias(focado, 1),
      ArrowUp: () => somarDias(focado, -7),
      ArrowDown: () => somarDias(focado, 7),
      Home: () => somarDias(focado, -d.getDay()),
      End: () => somarDias(focado, 6 - d.getDay()),
      PageUp: () => somarMeses(focado, -1),
      PageDown: () => somarMeses(focado, 1),
    };
    const proximo = passos[evento.key];
    if (!proximo) return;
    evento.preventDefault();
    mover(proximo());
  }

  function mudarMes(delta: number) {
    const base = `${String(mes.ano).padStart(4, "0")}-${String(mes.mes).padStart(2, "0")}-01`;
    const alvo = somarMeses(base, delta);
    irParaMes(alvo);
    setFocado(alvo);
    setDevolverFoco(false); // trocar de mês pelos botões não rouba o foco dos botões
  }

  const grade = montarGrade(mes.ano, mes.mes);
  const titulo = `${NOMES_DOS_MESES[mes.mes - 1]} de ${mes.ano}`;

  return (
    <div className="w-[296px] max-w-full p-3" data-calendario>
      <div className="mb-2 flex items-center justify-between gap-2">
        <button type="button" onClick={() => mudarMes(-1)} aria-label="Mês anterior" className={botaoIcone}>
          <ChevronLeft className="h-4 w-4" aria-hidden />
        </button>
        <p className="text-sm font-semibold capitalize text-fg" aria-live="polite">
          {titulo}
        </p>
        <button type="button" onClick={() => mudarMes(1)} aria-label="Próximo mês" className={botaoIcone}>
          <ChevronRight className="h-4 w-4" aria-hidden />
        </button>
      </div>

      <div ref={gradeRef} role="grid" aria-label={titulo} onKeyDown={aoTeclar}>
        <div role="row" className="grid grid-cols-7">
          {ROTULOS_SEMANA.map((rotulo) => (
            <span key={rotulo} role="columnheader" className="py-1 text-center text-[11px] font-medium uppercase text-fg-subtle">
              {rotulo}
            </span>
          ))}
        </div>
        {grade.map((semana, indice) => (
          <div key={indice} role="row" className="grid grid-cols-7">
            {semana.map((dia) => {
              const escolhido = dia.iso === valor;
              const ehHoje = dia.iso === hoje;
              return (
                <button
                  key={dia.iso}
                  type="button"
                  role="gridcell"
                  data-dia={dia.iso}
                  tabIndex={dia.iso === focado ? 0 : -1}
                  aria-label={rotuloDoDia(dia.iso)}
                  aria-selected={escolhido}
                  aria-current={ehHoje ? "date" : undefined}
                  onClick={() => aoEscolher(dia.iso)}
                  onFocus={() => setFocado(dia.iso)}
                  className={clsx(
                    "mx-auto my-0.5 flex h-8 w-8 items-center justify-center rounded-lg text-[13px] tabular-nums transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60",
                    escolhido
                      ? "bg-indigo-600 font-semibold text-white dark:bg-indigo-500"
                      : clsx("hover:bg-zinc-100 dark:hover:bg-zinc-800", dia.doMes ? "text-fg" : "text-fg-subtle", ehHoje && "font-semibold ring-1 ring-inset ring-indigo-500/70"),
                  )}
                >
                  {dia.dia}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      <div className="mt-2 flex items-center justify-between border-t border-line pt-2">
        <button type="button" onClick={() => aoEscolher(hoje)} className={botaoTexto}>
          Hoje
        </button>
        <div className="flex items-center gap-1">
          {aoLimpar && (
            <button type="button" onClick={aoLimpar} className={botaoTexto}>
              Limpar
            </button>
          )}
          {aoFechar && (
            <button type="button" onClick={aoFechar} className={botaoTexto}>
              Fechar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

const botaoIcone =
  "flex h-8 w-8 items-center justify-center rounded-lg text-fg-muted transition hover:bg-zinc-100 hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60 dark:hover:bg-zinc-800";
const botaoTexto =
  "rounded-lg px-2.5 py-1.5 text-xs font-semibold text-indigo-600 transition hover:bg-indigo-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60 dark:text-indigo-400 dark:hover:bg-indigo-500/10";
