"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";
import { TriangleAlert, X } from "lucide-react";
import { agendarFechamento, DURACAO_AVISO_MS } from "@/lib/trafego-ui";

/**
 * Aviso flutuante temporário (canto superior direito). `position: fixed` e renderizado no `body` (portal): não ocupa espaço nem desloca nada da tela. Tom de ATENÇÃO
 * (âmbar), não de erro crítico. Acessível: região `status` (leitor de tela anuncia sem roubar o foco), botão "Fechar" focável e Esc fecha. `chave` muda a cada novo
 * disparo — repetir a ação reinicia o prazo de ~5 s. Não aparece sozinho: quem usa só o abre como resposta a uma ação do usuário.
 */
export function AvisoFlutuante({
  mensagem,
  aberto,
  chave,
  onFechar,
  duracaoMs = DURACAO_AVISO_MS,
}: {
  mensagem: string;
  aberto: boolean;
  chave: number;
  onFechar: () => void;
  duracaoMs?: number;
}) {
  useEffect(() => {
    if (!aberto) return;
    const cancelar = agendarFechamento(onFechar, duracaoMs);
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") onFechar();
    };
    document.addEventListener("keydown", aoTeclar);
    return () => {
      cancelar();
      document.removeEventListener("keydown", aoTeclar);
    };
    // `chave` reinicia o prazo quando o aviso é disparado de novo com ele já aberto
  }, [aberto, chave, duracaoMs, onFechar]);

  // `aberto` só vira true como resposta a uma ação do usuário (no cliente): nunca na renderização do servidor — o `document` existe aqui.
  if (!aberto) return null;
  return createPortal(
    <div
      role="status"
      aria-live="polite"
      className="fixed right-4 top-4 z-[70] flex max-w-sm items-start gap-3 rounded-xl border border-amber-300/70 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900 shadow-lg dark:border-amber-500/40 dark:bg-amber-950 dark:text-amber-200"
    >
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <p className="flex-1">{mensagem}</p>
      <button
        type="button"
        onClick={onFechar}
        aria-label="Fechar aviso"
        className="-mr-1 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-amber-700 transition hover:bg-amber-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 dark:text-amber-300 dark:hover:bg-amber-900"
      >
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>,
    document.body,
  );
}
