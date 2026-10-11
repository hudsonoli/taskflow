// Seleção em lote de Arquivos (Fase 8B) — lógica PURA (testável com `node --test`), sem React nem fetch.
//
// Duas formas de seleção, nunca misturadas:
// - "ids": conjunto de IDs explícitos (os cards marcados), até LIMITE_IDS_EXPLICITOS;
// - "todos": "todos os resultados do filtro" — NÃO carrega IDs no navegador: guarda só o total e as exceções (itens desmarcados depois).
//   O servidor reexecuta a consulta autorizada (tenant + escopo + filtros) com `excludedIds`.
// IDs nunca são índices da página: marcar/desmarcar não depende de posição, página ou rolagem.
import type { ArquivosCentralFiltros } from "../types/arquivo.ts";

export const LIMITE_IDS_EXPLICITOS = 500;
export const LIMITE_EXCLUIDOS = 1000;

export type SelecaoArquivos =
  | { modo: "ids"; ids: ReadonlySet<string> }
  | { modo: "todos"; excluidos: ReadonlySet<string>; total: number };

/** Filtros que viajam no corpo do lote: os MESMOS da listagem (CSV), sem paginação. */
export type FiltrosDoLote = Omit<ArquivosCentralFiltros, "limit" | "offset">;
export type ContextoDoLote = { clienteId?: string; projetoId?: string; demandaId?: string };

export type CorpoSelecaoLote =
  | { mode: "ids"; ids: string[]; contexto?: ContextoDoLote }
  | { mode: "all_filtered"; excludedIds: string[]; filtros?: FiltrosDoLote; contexto?: ContextoDoLote };

export function selecaoVazia(): SelecaoArquivos {
  return { modo: "ids", ids: new Set() };
}

export function quantidadeSelecionada(selecao: SelecaoArquivos): number {
  return selecao.modo === "ids" ? selecao.ids.size : Math.max(0, selecao.total - selecao.excluidos.size);
}

export function estaSelecionado(selecao: SelecaoArquivos, id: string): boolean {
  return selecao.modo === "ids" ? selecao.ids.has(id) : !selecao.excluidos.has(id);
}

export function textoDoContador(quantidade: number): string {
  return quantidade === 1 ? "1 selecionado" : `${quantidade} selecionados`;
}

/** Marca/desmarca UM arquivo. Respeita os tetos do contrato: acima deles devolve a seleção intacta (a interface avisa). */
export function alternarArquivo(selecao: SelecaoArquivos, id: string): SelecaoArquivos {
  if (selecao.modo === "ids") {
    const ids = new Set(selecao.ids);
    if (ids.has(id)) ids.delete(id);
    else if (ids.size < LIMITE_IDS_EXPLICITOS) ids.add(id);
    else return selecao;
    return { modo: "ids", ids };
  }
  const excluidos = new Set(selecao.excluidos);
  if (excluidos.has(id)) excluidos.delete(id);
  else if (excluidos.size < LIMITE_EXCLUIDOS) excluidos.add(id);
  else return selecao;
  return { ...selecao, excluidos };
}

/** Checkbox do cabeçalho: SÓ os arquivos carregados na página atual — nunca "todos os resultados". */
export function selecionarPagina(selecao: SelecaoArquivos, idsDaPagina: readonly string[]): SelecaoArquivos {
  if (selecao.modo === "todos") {
    const excluidos = new Set(selecao.excluidos);
    for (const id of idsDaPagina) excluidos.delete(id);
    return { ...selecao, excluidos };
  }
  const ids = new Set(selecao.ids);
  for (const id of idsDaPagina) {
    if (ids.size >= LIMITE_IDS_EXPLICITOS) break;
    ids.add(id);
  }
  return { modo: "ids", ids };
}

export function desmarcarPagina(selecao: SelecaoArquivos, idsDaPagina: readonly string[]): SelecaoArquivos {
  if (selecao.modo === "todos") {
    const excluidos = new Set(selecao.excluidos);
    for (const id of idsDaPagina) if (excluidos.size < LIMITE_EXCLUIDOS) excluidos.add(id);
    return { ...selecao, excluidos };
  }
  const ids = new Set(selecao.ids);
  for (const id of idsDaPagina) ids.delete(id);
  return { modo: "ids", ids };
}

export type EstadoDoCabecalho = "nenhum" | "parcial" | "todos";

/** Estado do checkbox do cabeçalho: marcado só se TODA a página está marcada; indeterminado se algumas estão. */
export function estadoDoCabecalho(selecao: SelecaoArquivos, idsDaPagina: readonly string[]): EstadoDoCabecalho {
  if (idsDaPagina.length === 0) return "nenhum";
  const marcados = idsDaPagina.filter((id) => estaSelecionado(selecao, id)).length;
  if (marcados === 0) return "nenhum";
  return marcados === idsDaPagina.length ? "todos" : "parcial";
}

/** "Selecionar todos os N resultados": só guarda o total; as exceções começam vazias. */
export function selecionarTodosOsResultados(total: number): SelecaoArquivos {
  return { modo: "todos", excluidos: new Set(), total };
}

/**
 * Oferece "Selecionar todos os N arquivos encontrados" quando a página inteira está marcada (modo ids), há resultados além do que foi carregado e
 * o total já é conhecido. Nunca assume isso sozinho.
 */
export function deveOferecerTodosOsResultados(
  selecao: SelecaoArquivos,
  idsDaPagina: readonly string[],
  totalEncontrado: number | null,
): boolean {
  return (
    selecao.modo === "ids" &&
    idsDaPagina.length > 0 &&
    estadoDoCabecalho(selecao, idsDaPagina) === "todos" &&
    totalEncontrado !== null &&
    totalEncontrado > idsDaPagina.length
  );
}

/** Tira da seleção arquivos que deixaram de existir (exclusão individual ou em lote). */
export function removerDaSelecao(selecao: SelecaoArquivos, removidos: readonly string[]): SelecaoArquivos {
  if (selecao.modo === "ids") {
    const ids = new Set(selecao.ids);
    for (const id of removidos) ids.delete(id);
    return { modo: "ids", ids };
  }
  const excluidos = new Set(selecao.excluidos);
  let total = selecao.total;
  for (const id of removidos) {
    excluidos.delete(id); // se já era exceção, deixa de ser contado como exceção…
    total -= 1; // …e o universo encolheu em um arquivo de qualquer forma
  }
  return { modo: "todos", excluidos, total: Math.max(0, total) };
}

/** Corpo do `POST /arquivos/{resumo,download,excluir}-lote`. `contexto` é o recorte fixo da tela (Cliente/Projeto); os filtros só estreitam. */
export function corpoDaSelecao(
  selecao: SelecaoArquivos,
  universo: { filtros: FiltrosDoLote; contexto?: ContextoDoLote },
): CorpoSelecaoLote {
  const contexto = universo.contexto && Object.values(universo.contexto).some(Boolean) ? limparVazios(universo.contexto) : undefined;
  if (selecao.modo === "ids") {
    return { mode: "ids", ids: [...selecao.ids], ...(contexto ? { contexto } : {}) };
  }
  const filtros = limparVazios(universo.filtros);
  return {
    mode: "all_filtered",
    excludedIds: [...selecao.excluidos],
    ...(Object.keys(filtros).length > 0 ? { filtros } : {}),
    ...(contexto ? { contexto } : {}),
  };
}

function limparVazios<T extends Record<string, unknown>>(valores: T): T {
  return Object.fromEntries(Object.entries(valores).filter(([, valor]) => valor !== undefined && valor !== null && valor !== "")) as T;
}

export type ConfirmacaoDeExclusao = {
  titulo: string;
  aviso: string;
  /** "Selecionar todos os resultados": exige uma ciência explícita extra (checkbox) antes de habilitar o botão. */
  exigeCiencia: boolean;
  textoCiencia: string | null;
};

/** A exclusão é DEFINITIVA (registro e arquivo físico) — o texto diz isso. */
export function confirmacaoDeExclusao(selecao: SelecaoArquivos): ConfirmacaoDeExclusao {
  const quantidade = quantidadeSelecionada(selecao);
  const aviso = "Esta ação não pode ser desfeita.";
  if (selecao.modo === "todos") {
    return {
      titulo: `Excluir todos os ${quantidade} arquivos encontrados?`,
      aviso,
      exigeCiencia: true,
      textoCiencia: `Entendo que todos os ${quantidade} arquivos deste filtro serão excluídos`,
    };
  }
  return {
    titulo: quantidade === 1 ? "Excluir 1 arquivo?" : `Excluir ${quantidade} arquivos?`,
    aviso,
    exigeCiencia: false,
    textoCiencia: null,
  };
}

function temCaractereProibido(nome: string): boolean {
  for (const caractere of nome) {
    const codigo = caractere.charCodeAt(0);
    if (caractere === "/" || caractere === "\\" || codigo < 32) return true;
  }
  return false;
}

/** `filename="..."` do Content-Disposition; o servidor só envia ASCII seguro, mas valida mesmo assim antes de usar como nome de download. */
export function nomeDoDownload(contentDisposition: string | null, padrao = "taskflow-arquivos.zip"): string {
  const encontrado = contentDisposition?.match(/filename="?([^";]+)"?/i)?.[1]?.trim();
  if (!encontrado || temCaractereProibido(encontrado) || !encontrado.toLowerCase().endsWith(".zip")) return padrao;
  return encontrado;
}
