"use client";

import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  accent: string;
  /** cor do ícone sobre o fundo (padrão: branco; cards da marca usam a cor legível sobre a marca) */
  onAccent?: string;
  index: number;
  total: number;
}

/**
 * Indicador da faixa única do Meu Dia (`<li>` dentro do `<ul>` de DashboardView): ícone + valor.
 *
 * - Acessibilidade: o item tem `aria-label="Atrasadas: 2"` (nome + valor), nunca só no hover. O conteúdo
 *   visual (ícone, valor, rótulo, tooltip) é `aria-hidden` para não duplicar a leitura.
 * - lg+ (faixa sem rolagem): o rótulo aparece num tooltip no hover e no foco do teclado (`tabIndex=0`
 *   só para chegar ao tooltip — o indicador não é botão nem faz ação). O tooltip é absoluto: não muda
 *   a largura do item nem empurra os vizinhos. O destaque (sobe/cresce) usa `motion-safe:` e `hover:` só
 *   vale em ponteiro com hover.
 * - abaixo de lg (faixa com rolagem horizontal local, que cortaria um tooltip): sem hover confiável em
 *   touch, então o rótulo curto fica visível sob o ícone.
 */
export function StatCard({ label, value, icon: Icon, accent, onAccent, index, total }: StatCardProps) {
  const alinhamentoTooltip =
    index === 0 ? "left-0" : index === total - 1 ? "right-0" : "left-1/2 -translate-x-1/2";

  return (
    <motion.li
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04, ease: "easeOut" }}
      tabIndex={0}
      aria-label={`${label}: ${value}`}
      className="group relative w-24 shrink-0 rounded-xl outline-none hover:z-20 focus-visible:z-20 lg:w-auto lg:min-w-0 lg:flex-1"
    >
      <div aria-hidden className="flex h-full flex-col items-center justify-center gap-1.5 rounded-xl border border-line bg-surface px-2 py-2.5 shadow-sm transition-[transform,box-shadow,border-color] duration-200 ease-out group-hover:border-line-strong group-hover:shadow-md group-focus-visible:border-focus group-focus-visible:ring-2 group-focus-visible:ring-focus motion-safe:group-hover:-translate-y-0.5 motion-safe:group-hover:scale-[1.03] lg:flex-row lg:gap-2.5 lg:px-3 lg:py-4">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white lg:h-9 lg:w-9"
            style={{ background: accent, color: onAccent }}
          >
            <Icon size={16} />
          </span>
          <span className="text-xl font-semibold tabular-nums tracking-tight text-fg">
            {value}
          </span>
        </div>
        <span aria-hidden className="line-clamp-2 text-center text-[11px] leading-[13px] text-fg-muted lg:hidden">
          {label}
        </span>
      </div>
      <span
        aria-hidden
        className={`pointer-events-none absolute bottom-full z-30 mb-2 hidden whitespace-nowrap rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs font-medium text-fg opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 lg:block ${alinhamentoTooltip}`}
      >
        {label}
      </span>
    </motion.li>
  );
}
