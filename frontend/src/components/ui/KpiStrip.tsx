"use client";

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import clsx from "clsx";
import type { BadgeTone } from "@/components/ui/Badge";
import { toneClassNames } from "@/components/ui/MetricCard";
import { centroTooltip, rotuloKpi } from "@/lib/kpiStrip";

/**
 * Faixa única de indicadores (apresentação apenas — dados, regras e escopo ficam na tela que a usa).
 *
 * - Uma linha, sem quebrar: `flex-nowrap` + `overflow-x-auto` LOCAL (a página nunca ganha rolagem horizontal).
 * - lg+: cada item é ícone + valor e divide o espaço; o rótulo (e a descrição, se houver) aparece num tooltip no
 *   hover e no foco do teclado. O tooltip é `fixed` e não ocupa espaço — não muda a largura do item nem empurra
 *   os vizinhos, e não é cortado pela rolagem da faixa.
 * - Abaixo de lg: sem hover confiável em touch, então o rótulo curto fica visível sob o ícone.
 * - Acessibilidade: cada item tem `aria-label="Nome: valor"` (descrição em `aria-description`). O indicador não é
 *   botão (não faz ação); `tabIndex=0` existe só para o teclado alcançar o tooltip.
 * - Movimento (sobe/cresce) só com `motion-safe:` e em ponteiro com hover.
 */
export interface KpiItem {
  key: string;
  label: string;
  value: number | string;
  icon: ReactNode;
  /** texto secundário mostrado no tooltip (desktop) e em `aria-description` */
  description?: string;
  /** identidade do ícone no padrão suave dos MetricCard (ignorado se houver `accent`) */
  tone?: BadgeTone;
  /** identidade do ícone em gradiente (ícone branco, ou `onAccent`) */
  accent?: string;
  onAccent?: string;
}

export function KpiStrip({ ariaLabel, itens }: { ariaLabel: string; itens: KpiItem[] }) {
  return (
    <ul
      aria-label={ariaLabel}
      className="-m-1 flex flex-nowrap gap-2 overflow-x-auto p-1 [scrollbar-width:thin]"
    >
      {itens.map((item, index) => (
        <KpiChip key={item.key} item={item} index={index} />
      ))}
    </ul>
  );
}

function KpiChip({ item, index }: { item: KpiItem; index: number }) {
  const { label, value, icon, description, tone = "neutral", accent, onAccent } = item;
  const itemRef = useRef<HTMLLIElement>(null);
  const tooltipRef = useRef<HTMLSpanElement>(null);
  const [alvo, setAlvo] = useState<{ centro: number; topo: number } | null>(null);

  function mostrar() {
    const caixa = itemRef.current?.getBoundingClientRect();
    if (caixa) setAlvo({ centro: caixa.left + caixa.width / 2, topo: caixa.top });
  }

  // Tooltip fixo: se algo rolar/redimensionar enquanto ele está aberto, fecha (a posição ficaria velha).
  useEffect(() => {
    if (!alvo) return;
    const fechar = () => setAlvo(null);
    window.addEventListener("scroll", fechar, true);
    window.addEventListener("resize", fechar);
    return () => {
      window.removeEventListener("scroll", fechar, true);
      window.removeEventListener("resize", fechar);
    };
  }, [alvo]);

  // Mede o tooltip já renderizado e mantém ele inteiro dentro da janela.
  useLayoutEffect(() => {
    const tooltip = tooltipRef.current;
    if (!alvo || !tooltip) return;
    tooltip.style.left = `${centroTooltip(alvo.centro, tooltip.offsetWidth, window.innerWidth)}px`;
  }, [alvo]);

  return (
    <motion.li
      ref={itemRef}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04, ease: "easeOut" }}
      tabIndex={0}
      aria-label={rotuloKpi(label, value)}
      aria-description={description}
      onMouseEnter={mostrar}
      onMouseLeave={() => setAlvo(null)}
      onFocus={(evento) => {
        if (evento.currentTarget.matches(":focus-visible")) mostrar();
      }}
      onBlur={() => setAlvo(null)}
      className="group relative w-24 shrink-0 rounded-xl outline-none hover:z-20 focus-visible:z-20 lg:w-auto lg:min-w-fit lg:max-w-60 lg:flex-1"
    >
      <div
        aria-hidden
        className="flex h-full flex-col items-center justify-center gap-1.5 rounded-xl border border-line bg-surface px-2 py-2.5 shadow-sm transition-[transform,box-shadow,border-color] duration-200 ease-out group-hover:border-line-strong group-hover:shadow-md group-focus-visible:border-focus group-focus-visible:ring-2 group-focus-visible:ring-focus motion-safe:group-hover:-translate-y-0.5 motion-safe:group-hover:scale-[1.03] lg:flex-row lg:gap-2.5 lg:px-3 lg:py-4"
      >
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg lg:h-9 lg:w-9",
              accent ? "text-white" : toneClassNames[tone],
            )}
            style={accent ? { background: accent, color: onAccent } : undefined}
          >
            {icon}
          </span>
          <span className="whitespace-nowrap text-xl font-semibold tabular-nums tracking-tight text-fg">{value}</span>
        </div>
        <span className="line-clamp-3 text-center text-[11px] leading-[13px] text-fg-muted lg:hidden">{label}</span>
      </div>
      {alvo && (
        <span
          ref={tooltipRef}
          aria-hidden
          style={{ left: alvo.centro, top: alvo.topo }}
          className="pointer-events-none fixed z-50 hidden max-w-[min(20rem,calc(100vw-1rem))] -translate-x-1/2 -translate-y-[calc(100%+0.5rem)] rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-fg shadow-lg lg:block"
        >
          <span className="block whitespace-nowrap font-medium">{label}</span>
          {description && <span className="mt-0.5 block text-fg-muted">{description}</span>}
        </span>
      )}
    </motion.li>
  );
}
