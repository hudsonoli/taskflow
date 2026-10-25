// Estilo visual PESSOAL do navegador (P1_GLASS_CALENDAR_THEME): `default | glass`. É um eixo SEPARADO do modo de cor (`data-theme` claro/escuro, ver `lib/tema.ts`) — Glass não é um terceiro tema.
// Módulo PURO (sem React/Next): roda no layout, no cliente e no `node --test`.
//
// Persistência: só `localStorage` deste navegador (nada vai ao servidor nesta fase). O estilo vale como ATRIBUTO GLOBAL do <html> (`data-visual-style`); o CSS (globals.css) lê esse atributo e os
// componentes não recebem props de estilo. Para não haver "Padrão → Glass" visível depois da hidratação, um script mínimo inline (abaixo) grava o atributo ANTES do primeiro paint; o servidor
// nunca renderiza o atributo em JSX, então não há hydration mismatch (o <html> já usa suppressHydrationWarning).

export type EstiloVisual = "default" | "glass";

export const ESTILOS_VISUAIS = ["default", "glass"] as const;
export const ESTILO_VISUAL_PADRAO: EstiloVisual = "default";

/** Chave do localStorage (grafia oficial do produto no prefixo). */
export const CHAVE_ESTILO_VISUAL = "taskflow.estilo-visual";
export const ATRIBUTO_ESTILO_VISUAL = "data-visual-style";

export function estiloVisualValido(valor: unknown): valor is EstiloVisual {
  return typeof valor === "string" && (ESTILOS_VISUAIS as readonly string[]).includes(valor);
}

/** Qualquer coisa fora da lista (chave ausente, valor antigo ou adulterado) vira o padrão — nunca quebra a tela. */
export function normalizarEstiloVisual(valor: unknown): EstiloVisual {
  return estiloVisualValido(valor) ? valor : ESTILO_VISUAL_PADRAO;
}

/**
 * Script inline (antes da hidratação): lê o localStorage e grava `data-visual-style` no <html>. Sem localStorage (navegação privada/bloqueio) cai no padrão. Não lê nada sensível e não depende de
 * sessão — é só a preferência visual deste navegador.
 */
export const SCRIPT_ESTILO_VISUAL =
  `(function(){var e=document.documentElement;try{var v=localStorage.getItem(${JSON.stringify(CHAVE_ESTILO_VISUAL)});e.setAttribute(${JSON.stringify(ATRIBUTO_ESTILO_VISUAL)},v==="glass"?"glass":"default")}` +
  `catch(x){e.setAttribute(${JSON.stringify(ATRIBUTO_ESTILO_VISUAL)},"default")}})()`;

export const ROTULOS_ESTILO_VISUAL: Record<EstiloVisual, string> = { default: "Padrão", glass: "Glass" };
