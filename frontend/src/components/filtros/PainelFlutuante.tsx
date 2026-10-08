"use client";

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

const MARGEM = 8;
const LARGURA_PADRAO = 288;

/**
 * Painel ancorado a um elemento, posicionado com `position: fixed` num portal. Fixo porque os chips vivem numa linha com
 * rolagem horizontal (mobile): um painel `absolute` ali dentro seria cortado pelo `overflow`. A posição é recalculada ao abrir e
 * o painel fecha com rolagem de página, redimensionamento, clique fora e Escape (devolvendo o foco à âncora).
 * Cabe em ~375px: largura `min(288px, 100vw - 16px)` e deslocamento horizontal limitado à viewport.
 */
export function PainelFlutuante({
  ancora,
  onFechar,
  rotulo,
  children,
  largura = LARGURA_PADRAO,
}: {
  ancora: HTMLElement;
  onFechar: () => void;
  /** nome acessível do painel */
  rotulo: string;
  children: ReactNode;
  largura?: number;
}) {
  const painelRef = useRef<HTMLDivElement>(null);
  const [posicao, setPosicao] = useState<{ top: number; left: number } | null>(null);
  const fecharRef = useRef(onFechar);
  useEffect(() => {
    fecharRef.current = onFechar;
  });

  useLayoutEffect(() => {
    const caixa = ancora.getBoundingClientRect();
    const larguraReal = Math.min(largura, window.innerWidth - MARGEM * 2);
    const left = Math.max(MARGEM, Math.min(caixa.left, window.innerWidth - larguraReal - MARGEM));
    // Se não cabe embaixo, abre para cima (limitado ao topo da viewport).
    const alturaPainel = painelRef.current?.offsetHeight ?? 0;
    const cabeEmbaixo = caixa.bottom + 6 + alturaPainel <= window.innerHeight - MARGEM;
    const top = cabeEmbaixo ? caixa.bottom + 6 : Math.max(MARGEM, caixa.top - 6 - alturaPainel);
    setPosicao({ top, left });
  }, [ancora, largura]);

  useEffect(() => {
    function aoClicarFora(evento: MouseEvent) {
      const alvo = evento.target as Node;
      if (painelRef.current?.contains(alvo) || ancora.contains(alvo)) return;
      fecharRef.current();
    }
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key !== "Escape") return;
      evento.stopPropagation();
      fecharRef.current();
      ancora.focus();
    }
    function aoMoverPagina(evento: Event) {
      // rolar a lista de opções dentro do painel não fecha; rolar a página, sim
      if (painelRef.current && evento.target instanceof Node && painelRef.current.contains(evento.target)) return;
      fecharRef.current();
    }
    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoTeclar);
    window.addEventListener("resize", aoMoverPagina);
    window.addEventListener("scroll", aoMoverPagina, true);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoTeclar);
      window.removeEventListener("resize", aoMoverPagina);
      window.removeEventListener("scroll", aoMoverPagina, true);
    };
  }, [ancora]);

  if (typeof document === "undefined") return null;
  return createPortal(
    <div
      ref={painelRef}
      role="dialog"
      aria-label={rotulo}
      style={{
        position: "fixed",
        top: posicao?.top ?? 0,
        left: posicao?.left ?? 0,
        width: `min(${largura}px, calc(100vw - ${MARGEM * 2}px))`,
        // invisível até medir (opacity, não visibility: um elemento `visibility:hidden` não aceita foco)
        opacity: posicao ? 1 : 0,
        pointerEvents: posicao ? undefined : "none",
      }}
      className="z-[60] overflow-hidden rounded-xl border border-line-strong bg-surface text-sm text-fg shadow-lg"
    >
      {children}
    </div>,
    document.body,
  );
}
