// Cores da marca → tokens de CSS com contraste garantido. Módulo PURO (sem imports): roda no servidor
// (layout raiz), no cliente (preview da tela Personalizar) e no teste de contraste (`node --test`).
//
// A empresa escolhe só DUAS cores (principal e secundária). Tudo o que depende delas é derivado aqui:
//  - a escala 50…950 de cada uma (o app inteiro usa as classes `indigo-*` e `violet-*` do Tailwind, que
//    o globals.css redireciona para `--brand-*` / `--accent-*`);
//  - a cor do texto sobre elas (branco ou quase-preto, a de maior contraste WCAG);
//  - o gradiente da marca — só quando o texto continua legível sobre as duas pontas.
// Nenhuma cor da empresa é usada como texto sobre fundo claro/escuro sem passar pela escala (passos 600/700
// e 400 são forçados a ter contraste suficiente com a superfície onde são usados).

export const COR_PRIMARIA_PADRAO = "#6366f1";
export const COR_SECUNDARIA_PADRAO = "#7c3aed";

export const PASSOS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950] as const;
export type Passo = (typeof PASSOS)[number];

const BRANCO = "#ffffff";
const QUASE_PRETO = "#0b0b0c";
// Superfícies de referência para garantir legibilidade do texto colorido: o PIOR caso de cada tema (a superfície
// secundária, a mais próxima do texto: zinc-100 no claro, zinc-800 no escuro — as outras superfícies são mais
// contrastantes, então se passa nelas passa em todas). 4.5:1 = WCAG AA para texto normal.
const SUPERFICIE_CLARA = "#f4f4f5";
const SUPERFICIE_ESCURA = "#27272a";
export const CONTRASTE_TEXTO = 4.5;

// ── conversões ────────────────────────────────────────────────────────────────────────────────
export function hexValido(valor: string): boolean {
  return /^#[0-9a-fA-F]{6}$/.test(valor);
}

function hexParaRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbParaHex(r: number, g: number, b: number): string {
  const c = (v: number) => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, "0");
  return `#${c(r)}${c(g)}${c(b)}`;
}

const paraLinear = (v: number) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
const deLinear = (v: number) => (v <= 0.0031308 ? v * 12.92 : 1.055 * v ** (1 / 2.4) - 0.055);

export function luminanciaRelativa(hex: string): number {
  const [r, g, b] = hexParaRgb(hex).map((v) => paraLinear(v / 255));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Razão de contraste WCAG 2.x entre duas cores (1…21). */
export function contraste(a: string, b: string): number {
  const la = luminanciaRelativa(a);
  const lb = luminanciaRelativa(b);
  const [claro, escuro] = la >= lb ? [la, lb] : [lb, la];
  return (claro + 0.05) / (escuro + 0.05);
}

type Oklch = { l: number; c: number; h: number };

function hexParaOklch(hex: string): Oklch {
  const [r, g, b] = hexParaRgb(hex).map((v) => paraLinear(v / 255));
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
  const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
  const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
  const c = Math.hypot(A, B);
  const h = c < 1e-4 ? 0 : (Math.atan2(B, A) * 180) / Math.PI;
  return { l: L, c, h: (h + 360) % 360 };
}

function oklchParaRgbLinear({ l, c, h }: Oklch): [number, number, number] {
  const a = c * Math.cos((h * Math.PI) / 180);
  const b = c * Math.sin((h * Math.PI) / 180);
  const l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s_ = (l - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_,
  ];
}

const dentroDoGamut = (rgb: [number, number, number]) => rgb.every((v) => v >= -0.0005 && v <= 1.0005);

/** OKLCH → hex, reduzindo o croma até caber no sRGB (mantém luminosidade e matiz). */
function oklchParaHex(cor: Oklch): string {
  let { c } = cor;
  let rgb = oklchParaRgbLinear({ ...cor, c });
  for (let i = 0; i < 24 && !dentroDoGamut(rgb); i++) {
    c *= 0.93;
    rgb = oklchParaRgbLinear({ ...cor, c });
  }
  const [r, g, b] = rgb.map((v) => deLinear(Math.min(1, Math.max(0, v))) * 255) as [number, number, number];
  return rgbParaHex(r, g, b);
}

// ── escala ────────────────────────────────────────────────────────────────────────────────────
// Luminosidade e fração de croma de cada passo — extraídas da escala `indigo` do Tailwind (a atual do
// TaskFlow), de modo que uma cor parecida com o indigo reproduz a aparência atual.
const LADDER_L: Record<Passo, number> = { 50: 0.962, 100: 0.93, 200: 0.87, 300: 0.785, 400: 0.673, 500: 0.585, 600: 0.511, 700: 0.457, 800: 0.398, 900: 0.359, 950: 0.257 };
const LADDER_C: Record<Passo, number> = { 50: 0.077, 100: 0.146, 200: 0.279, 300: 0.494, 400: 0.78, 500: 1, 600: 1.12, 700: 1.03, 800: 0.837, 900: 0.618, 950: 0.386 };

/** Escala completa (50…950) a partir da cor da empresa, que ocupa EXATAMENTE o passo `ancora`. A luminosidade
 * dos demais passos é interpolada ENTRE a cor da empresa e os extremos (50 ≈ quase branco, 950 ≈ quase preto),
 * seguindo a proporção da escada do indigo — assim a escala é monotônica qualquer que seja a cor (um amarelo
 * claro continua tendo 300/400 mais claros que o 500, e não mais escuros). Os passos que viram TEXTO (600/700
 * sobre superfície clara, 400 sobre escura) são ajustados até ter contraste ≥ 4.5:1 com a pior superfície. */
export function gerarEscala(hex: string, ancora: Passo = 500): Record<Passo, string> {
  const base = hexParaOklch(hex);
  const croma = Math.min(base.c, 0.3);
  const fator = LADDER_C[ancora] || 1;
  const topo = Math.max(0.965, base.l);
  const fundo = Math.min(0.257, base.l);
  const larguraClara = LADDER_L[50] - LADDER_L[ancora];
  const larguraEscura = LADDER_L[ancora] - LADDER_L[950];
  const cores = {} as Record<Passo, Oklch>;
  for (const passo of PASSOS) {
    if (passo === ancora) {
      cores[passo] = base;
      continue;
    }
    const ref = LADDER_L[passo] - LADDER_L[ancora]; // >0: mais claro que a âncora · <0: mais escuro
    const l = ref > 0 ? base.l + (ref / larguraClara) * (topo - base.l) : base.l - (-ref / larguraEscura) * (base.l - fundo);
    cores[passo] = { l, c: (croma / fator) * LADDER_C[passo], h: base.h };
  }
  const escala = {} as Record<Passo, string>;
  const ajusta = (passo: Passo, sobe: boolean, superficie: string) => {
    const cor = { ...cores[passo] };
    while ((sobe ? cor.l < 0.99 : cor.l > 0.05) && contraste(oklchParaHex(cor), superficie) < CONTRASTE_TEXTO) cor.l += sobe ? 0.01 : -0.01;
    cores[passo] = cor;
  };
  if (ancora !== 600) ajusta(600, false, SUPERFICIE_CLARA);
  if (ancora !== 700) ajusta(700, false, SUPERFICIE_CLARA);
  if (ancora !== 400) ajusta(400, true, SUPERFICIE_ESCURA);
  // monotonia depois dos ajustes — a prioridade é o CONTRASTE (os passos ajustados não se movem): quem se acomoda
  // são os vizinhos, afastando-se da âncora (mais claros ficam mais claros, mais escuros ficam mais escuros).
  const idx = PASSOS.indexOf(ancora);
  for (let i = idx - 1; i >= 0; i--) cores[PASSOS[i]] = { ...cores[PASSOS[i]], l: Math.min(0.995, Math.max(cores[PASSOS[i]].l, cores[PASSOS[i + 1]].l + 0.02)) };
  for (let i = idx + 1; i < PASSOS.length; i++) cores[PASSOS[i]] = { ...cores[PASSOS[i]], l: Math.max(0, Math.min(cores[PASSOS[i]].l, cores[PASSOS[i - 1]].l - 0.02)) };
  for (const passo of PASSOS) escala[passo] = passo === ancora ? hex.toLowerCase() : oklchParaHex(cores[passo]);
  return escala;
}

/** Cor do texto sobre um fundo: branco ou quase-preto, a de maior contraste (sempre ≥ 4.5:1). */
export function corSobre(fundo: string): string {
  return contraste(BRANCO, fundo) >= contraste(QUASE_PRETO, fundo) ? BRANCO : QUASE_PRETO;
}

/** Pior contraste de `texto` sobre as cores dadas. */
function piorContraste(texto: string, fundos: string[]): number {
  return Math.min(...fundos.map((fundo) => contraste(texto, fundo)));
}

export type VariaveisMarca = Record<string, string>;

/** Variáveis CSS para o <html>. Cores iguais às padrão → `{}` (o CSS usa a escala original do Tailwind,
 * então nada muda na aparência atual). */
export function variaveisDaMarca(primaria: string, secundaria: string): VariaveisMarca {
  const primariaPadrao = primaria.toLowerCase() === COR_PRIMARIA_PADRAO;
  const secundariaPadrao = secundaria.toLowerCase() === COR_SECUNDARIA_PADRAO;
  if (primariaPadrao && secundariaPadrao) return {};

  const vars: VariaveisMarca = {};
  const principal = primariaPadrao ? COR_PRIMARIA_PADRAO : primaria.toLowerCase();
  const destaque = secundariaPadrao ? COR_SECUNDARIA_PADRAO : secundaria.toLowerCase();

  if (!primariaPadrao) {
    const escala = gerarEscala(principal, 500);
    for (const passo of PASSOS) vars[`--brand-${passo}`] = escala[passo];
  }
  if (!secundariaPadrao) {
    const escala = gerarEscala(destaque, 600);
    for (const passo of PASSOS) vars[`--accent-${passo}`] = escala[passo];
  }

  // Texto sobre cada cor sólida
  vars["--on-primary"] = corSobre(principal);
  vars["--on-secondary"] = corSobre(destaque);

  // Gradiente da marca (principal → secundária): só se UM texto legível serve às duas pontas; senão, cor sólida.
  const candidatos = [BRANCO, QUASE_PRETO];
  const melhor = candidatos.reduce((a, b) => (piorContraste(a, [principal, destaque]) >= piorContraste(b, [principal, destaque]) ? a : b));
  if (piorContraste(melhor, [principal, destaque]) >= CONTRASTE_TEXTO) {
    vars["--brand-gradient"] = `linear-gradient(135deg, ${principal}, ${destaque})`;
    vars["--on-brand"] = melhor;
  } else {
    vars["--brand-gradient"] = principal;
    vars["--on-brand"] = vars["--on-primary"];
  }
  return vars;
}

/** `{ "--x": "y" }` → `--x:y;--z:w` (para um <style> ou o atributo style). */
export function variaveisParaCss(vars: VariaveisMarca): string {
  return Object.entries(vars)
    .map(([k, v]) => `${k}:${v}`)
    .join(";");
}
