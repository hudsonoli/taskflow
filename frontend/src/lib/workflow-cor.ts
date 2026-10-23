// Cor do MODELO de workflow (P1_WORKFLOW_COLOR): identidade visual, nunca estado. Regras PURAS (testáveis com `node --test`).
//
// O banco guarda só o HEX canônico `#RRGGBB` em maiúsculas, ou NULL = "sem cor personalizada" (a interface usa o neutro; nunca se sorteia nem se persiste uma cor por padrão). A paleta abaixo é só atalho:
// qualquer HEX válido é aceito e só o HEX é persistido (nunca o nome da paleta). Cor é dado dinâmico: vai em `style` controlado de UM componente (WorkflowCor), nunca em classe Tailwind montada.
import { hexValido } from "./branding-tokens.ts";

export type CorDaPaleta = { hex: string; nome: string };

export const PALETA_WORKFLOW: ReadonlyArray<CorDaPaleta> = [
  { hex: "#8B5CF6", nome: "Violeta" },
  { hex: "#6366F1", nome: "Índigo" },
  { hex: "#3B82F6", nome: "Azul" },
  { hex: "#06B6D4", nome: "Ciano" },
  { hex: "#14B8A6", nome: "Turquesa" },
  { hex: "#22C55E", nome: "Verde" },
  { hex: "#EAB308", nome: "Amarelo" },
  { hex: "#F97316", nome: "Laranja" },
  { hex: "#EC4899", nome: "Rosa" },
  { hex: "#78716C", nome: "Pedra" },
];

/** `#RRGGBB` válido (qualquer caixa) → maiúsculas; qualquer outra coisa (vazio, `#FFF`, nome CSS, rgb(), texto) → `null`. */
export function normalizarCorWorkflow(valor: string | null | undefined): string | null {
  const texto = (valor ?? "").trim();
  return hexValido(texto) ? texto.toUpperCase() : null;
}

/** O que a interface pode PINTAR: só HEX canônico válido; qualquer outro valor (dado velho, injeção) cai no neutro. */
export function corParaPintar(cor: string | null | undefined): string | null {
  return normalizarCorWorkflow(cor);
}

/** Estado do campo de texto enquanto a pessoa digita: vazio = "sem cor"; incompleto/ inválido não é propagado. */
export type EstadoDoCampoDeCor = { texto: string; valida: boolean; cor: string | null };

export function estadoDoCampoDeCor(texto: string): EstadoDoCampoDeCor {
  const aparado = texto.trim();
  if (aparado === "") return { texto, valida: true, cor: null };
  const cor = normalizarCorWorkflow(aparado);
  return { texto, valida: cor !== null, cor };
}

/** Conteúdo para o `payload`: só um HEX válido ou `null` (remover). */
export function corParaPayload(cor: string | null | undefined): string | null {
  return normalizarCorWorkflow(cor);
}
