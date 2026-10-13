// MemberSelector — regras puras (sem DOM) do seletor canônico de pessoas: busca, ordem, limite, estouro de avatares e substituição single.
// `npm run test:member-selector` (node --test). O componente só desenha; as decisões ficam aqui para serem testadas de verdade.

export type PessoaSelecionavel = {
  id: string;
  nome: string;
  email?: string;
  subtitulo?: string;
  inativo?: boolean;
};

/** Minúsculas e sem acento: "JOÃO" casa com "joao". */
export function normalizarBusca(texto: string): string {
  return texto
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

/** Busca local por NOME e por E-MAIL (e pelo subtítulo, quando houver), sem acento e sem diferenciar caixa. Termo vazio = tudo. */
export function filtrarPessoas<T extends PessoaSelecionavel>(pessoas: readonly T[], termo: string): T[] {
  const alvo = normalizarBusca(termo);
  if (!alvo) return [...pessoas];
  return pessoas.filter((pessoa) =>
    [pessoa.nome, pessoa.email, pessoa.subtitulo].some((campo) => (campo ? normalizarBusca(campo).includes(alvo) : false)),
  );
}

/** Selecionados primeiro (na ordem em que já estavam), depois os demais na ordem original. Sem duplicar ninguém. */
export function selecionadosPrimeiro<T extends { id: string }>(pessoas: readonly T[], selecionados: readonly string[]): T[] {
  const marcado = new Set(selecionados);
  return [...pessoas.filter((pessoa) => marcado.has(pessoa.id)), ...pessoas.filter((pessoa) => !marcado.has(pessoa.id))];
}

/** Primeiro nome para o rótulo curto abaixo do avatar ("Hudson de Oliveira" -> "Hudson"). */
export function primeiroNome(nome: string): string {
  return nome.trim().split(/\s+/)[0] ?? "";
}

/** Quantos avatares aparecem e quantos viram "+N". `maxVisible` inválido (<1) mostra todos. */
export function dividirVisiveis<T>(selecionados: readonly T[], maxVisible: number | undefined): { visiveis: T[]; restantes: T[] } {
  if (!maxVisible || maxVisible < 1 || selecionados.length <= maxVisible) return { visiveis: [...selecionados], restantes: [] };
  return { visiveis: selecionados.slice(0, maxVisible), restantes: selecionados.slice(maxVisible) };
}

export type EntradaSelecao = {
  /** ids selecionados agora (a ORDEM é preservada: o payload continua sendo `string[]` de ids) */
  values: readonly string[];
  /** id clicado */
  id: string;
  multiple: boolean;
  /** limite do multi (ignorado no single) */
  max?: number;
};

export type ResultadoSelecao = {
  /** novos ids — o mesmo formato que o consumidor sempre recebeu em `onChange` */
  values: string[];
  /** true = o clique foi recusado por causa do limite (nada mudou) */
  bloqueadoPorLimite: boolean;
  /** true = fecha o dropdown (single: a escolha encerra a interação) */
  fechar: boolean;
};

/**
 * O que acontece ao clicar numa pessoa no dropdown.
 * - multi: marca/desmarca; marcar além de `max` é recusado (desmarcar é sempre possível);
 * - single: escolher OUTRA pessoa SUBSTITUI a anterior; clicar na já escolhida a remove (comportamento de sempre dos campos opcionais) e fecha.
 */
export function proximaSelecao({ values, id, multiple, max }: EntradaSelecao): ResultadoSelecao {
  const jaEscolhido = values.includes(id);
  if (multiple) {
    if (jaEscolhido) return { values: values.filter((valor) => valor !== id), bloqueadoPorLimite: false, fechar: false };
    if (max !== undefined && max >= 1 && values.length >= max) return { values: [...values], bloqueadoPorLimite: true, fechar: false };
    return { values: [...values, id], bloqueadoPorLimite: false, fechar: false };
  }
  return { values: jaEscolhido ? [] : [id], bloqueadoPorLimite: false, fechar: true };
}

/** Uma opção pode ser ESCOLHIDA agora? Quem já está selecionado sempre pode ser tirado; inativo não entra de novo (a menos que o campo permita) e o limite vale. */
export function podeEscolher({
  selecionado,
  inativo,
  permitirInativos,
  totalSelecionados,
  max,
  multiple,
}: {
  selecionado: boolean;
  inativo?: boolean;
  permitirInativos?: boolean;
  totalSelecionados: number;
  max?: number;
  multiple: boolean;
}): boolean {
  if (selecionado) return true;
  if (inativo && !permitirInativos) return false;
  if (multiple && max !== undefined && max >= 1 && totalSelecionados >= max) return false;
  return true;
}

/**
 * Posição do popover dentro da viewport: largura = a pedida limitada a (viewport − 2·margem); `deslocamentoX` (px relativos ao campo) empurra o popover para dentro
 * quando ele estouraria pela direita ou pela esquerda (campo recuado no celular, campo na borda direita no desktop); abre para cima se faltar espaço embaixo
 * e sobrar em cima.
 */
export function posicionarPopover({
  caixa,
  larguraPopover,
  alturaPopover,
  viewport,
  margem = 16,
}: {
  caixa: { left: number; right: number; top: number; bottom: number };
  larguraPopover: number;
  alturaPopover: number;
  viewport: { largura: number; altura: number };
  margem?: number;
}): { largura: number; deslocamentoX: number; vertical: "baixo" | "cima" } {
  const largura = Math.max(0, Math.min(larguraPopover, viewport.largura - 2 * margem));
  const esquerdaDesejada = Math.min(Math.max(caixa.left, margem), viewport.largura - largura - margem);
  const espacoBaixo = viewport.altura - caixa.bottom - margem;
  const espacoCima = caixa.top - margem;
  const vertical = espacoBaixo < alturaPopover && espacoCima > espacoBaixo ? "cima" : "baixo";
  return { largura, deslocamentoX: Math.round(esquerdaDesejada - caixa.left), vertical };
}
