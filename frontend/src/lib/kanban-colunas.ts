// Colunas vazias recolhidas do Kanban (preferência VISUAL; nada vai ao servidor). Regras PURAS, testáveis com `node --test`.
//
// "Vazia" aqui é só "nenhum card visível/carregado nesta coluna": NÃO afirma que o status inteiro está sem Demandas no banco (a lista pode ser apenas o universo carregado — ver P2_KANBAN_PAGINATION_SCOPE).
// A coluna recolhida continua no DOM e continua sendo destino válido de soltura; só muda a largura.

export const LARGURA_COLUNA_RECOLHIDA_PX = 56;

export type EntradaDeRecolhimento = {
  /** preferência "Recolher colunas vazias automaticamente" */
  recolherVazias: boolean;
  /** cards visíveis na coluna */
  quantidade: number;
  /** a pessoa expandiu a coluna (ou soltou um card nela) nesta sessão */
  expandidaManual: boolean;
  /** o arraste em curso passou por cima dela */
  expandidaPorArraste: boolean;
  /** decisão congelada no início do arraste (`null` = sem arraste em curso) */
  congelada: boolean | null;
};

/**
 * A coluna está recolhida? Fora de um arraste: preferência ligada + sem cards + não expandida à mão nem pelo arraste. DURANTE um arraste a decisão fica congelada no que era no início do gesto
 * (a última tarefa saindo da coluna não a faz colapsar no meio do movimento): só uma coluna recolhida que o arraste atravessou se abre — e fica aberta até o fim do gesto, para a soltura nunca cair
 * numa coluna que muda de largura debaixo do ponteiro.
 */
export function colunaRecolhida(entrada: EntradaDeRecolhimento): boolean {
  if (entrada.congelada !== null) return entrada.congelada && !entrada.expandidaPorArraste;
  return entrada.recolherVazias && entrada.quantidade === 0 && !entrada.expandidaManual && !entrada.expandidaPorArraste;
}

export type CaixaDeColuna = { id: string; left: number; right: number; top: number; bottom: number };

/** Qual coluna está debaixo do ponteiro (ou `null`)? Usado para abrir a coluna recolhida que o arraste atravessa; a soltura em si continua sendo decidida pelo dnd-kit. */
export function colunaSobOPonteiro(x: number, y: number, caixas: readonly CaixaDeColuna[]): string | null {
  const achada = caixas.find((caixa) => x >= caixa.left && x <= caixa.right && y >= caixa.top && y <= caixa.bottom);
  return achada?.id ?? null;
}

/** Tooltip/nome acessível da coluna recolhida (o nome completo nunca se perde). */
export function rotuloDaColunaRecolhida(titulo: string, quantidade: number): string {
  return `${titulo} — ${quantidade} ${quantidade === 1 ? "tarefa" : "tarefas"}. Clique para expandir.`;
}
