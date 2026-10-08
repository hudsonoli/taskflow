// Filtros avançados — lógica PURA (sem React/fetch), testável com `node --test`.
// Operadores, edição imutável da lista de filtros, resumo de valores, datas e estado na URL.
import type { DefinicaoFiltro, FiltroAtivo, OperadorFiltro, PresetData } from "../types/filtros.ts";

export const ROTULO_OPERADOR: Record<OperadorFiltro, string> = {
  is: "é",
  is_not: "não é",
  in: "é um de",
  not_in: "não é um de",
  before: "antes de",
  after: "depois de",
};

export const MAX_VALORES_POR_FILTRO = 50;

// ── Operadores ──────────────────────────────────────────────────────────────────────────────────────────────────

export function ehNegativo(operador: OperadorFiltro): boolean {
  return operador === "is_not" || operador === "not_in";
}

/** Operador de um campo enum a partir da polaridade e da quantidade de valores: 1 valor → "é", vários → "é um de". */
export function operadorEnum(negativo: boolean, quantidade: number): OperadorFiltro {
  if (quantidade > 1) return negativo ? "not_in" : "in";
  return negativo ? "is_not" : "is";
}

/** Operadores que a pessoa pode escolher no chip (para enum só a polaridade; "um de" é consequência da quantidade). */
export function operadoresEscolhiveis(definicao: DefinicaoFiltro, filtro: FiltroAtivo): OperadorFiltro[] {
  if (definicao.tipo === "data") return ["is", "before", "after"];
  const plural = filtro.valores.length > 1;
  if (definicao.permiteExcluir === false) return [plural ? "in" : "is"];
  return plural ? ["in", "not_in"] : ["is", "is_not"];
}

export function permiteMultiplos(definicao: DefinicaoFiltro): boolean {
  return definicao.tipo === "enum" && definicao.multiplo !== false;
}

export function campoBuscavel(definicao: DefinicaoFiltro): boolean {
  if (definicao.buscavel !== undefined) return definicao.buscavel;
  return Boolean(definicao.buscarOpcoes) || (definicao.opcoes?.length ?? 0) > 7;
}

// ── Edição da lista (sempre devolve uma lista nova) ────────────────────────────────────────────────────────────────

/** Coloca/substitui o filtro do campo (cada campo aparece uma vez), preservando a ordem em que foram adicionados. */
export function aplicarFiltro(filtros: readonly FiltroAtivo[], novo: FiltroAtivo): FiltroAtivo[] {
  const existe = filtros.some((filtro) => filtro.campo === novo.campo);
  return existe ? filtros.map((filtro) => (filtro.campo === novo.campo ? novo : filtro)) : [...filtros, novo];
}

export function removerFiltro(filtros: readonly FiltroAtivo[], campo: string): FiltroAtivo[] {
  return filtros.filter((filtro) => filtro.campo !== campo);
}

/** "Limpar": nenhum filtro. Devolve sempre a MESMA lista vazia — comparável por referência. */
export function limparFiltros(): FiltroAtivo[] {
  return [];
}

/** Liga/desliga um valor de um campo enum. Sem valores restantes o filtro deixa de existir (`null`). */
export function alternarValor(filtro: FiltroAtivo | undefined, definicao: DefinicaoFiltro, valor: string): FiltroAtivo | null {
  const negativo = filtro ? ehNegativo(filtro.operador) : false;
  const atuais = filtro?.valores ?? [];
  let valores: string[];
  if (!permiteMultiplos(definicao)) {
    valores = atuais.includes(valor) ? [] : [valor];
  } else if (atuais.includes(valor)) {
    valores = atuais.filter((existente) => existente !== valor);
  } else {
    valores = [...atuais, valor].slice(0, MAX_VALORES_POR_FILTRO);
  }
  if (valores.length === 0) return null;
  return { campo: definicao.id, operador: operadorEnum(negativo, valores.length), valores };
}

/** Troca o operador. Enum: só a polaridade muda (o "um de" segue a quantidade). Data: troca direta, validando o valor. */
export function trocarOperador(filtro: FiltroAtivo, definicao: DefinicaoFiltro, operador: OperadorFiltro): FiltroAtivo {
  if (definicao.tipo === "enum") {
    if (definicao.permiteExcluir === false) return filtro;
    return { ...filtro, operador: operadorEnum(ehNegativo(operador), filtro.valores.length) };
  }
  if (operador !== "is" && operador !== "before" && operador !== "after") return filtro;
  // "antes de"/"depois de" exigem uma data real: um atalho ("hoje", "atrasado"…) vira a data de hoje.
  const valor = filtro.valores[0];
  const valores = operador !== "is" && !dataIsoValida(valor) ? [formatarDataIso(new Date())] : [valor];
  return { ...filtro, operador, valores };
}

/** Filtro de data com operador e valor (data `AAAA-MM-DD` ou atalho). */
export function filtroDeData(campo: string, operador: OperadorFiltro, valor: string): FiltroAtivo {
  return { campo, operador, valores: [valor] };
}

// ── Resumo para o chip ────────────────────────────────────────────────────────────────────────────────────────────

/**
 * Valores em poucas palavras: "Maria", "Maria, João" ou "Maria, João +1". `rotulo` resolve o texto do valor;
 * enquanto um rótulo remoto não chegou usa `pendente` (nunca mostra o id cru).
 */
export function resumirValores(valores: readonly string[], rotulo: (valor: string) => string | undefined, pendente = "…"): string {
  const nomes = valores.map((valor) => rotulo(valor) ?? pendente);
  if (nomes.length <= 2) return nomes.join(", ");
  return `${nomes.slice(0, 2).join(", ")} +${nomes.length - 2}`;
}

export function rotuloDeData(valor: string, presets: readonly PresetData[] | undefined): string {
  const preset = presets?.find((item) => item.value === valor);
  if (preset) return preset.label;
  return dataIsoValida(valor) ? formatarDataBr(valor) : "—";
}

// ── Datas (sempre no fuso local da pessoa) ────────────────────────────────────────────────────────────────────────

const RE_DATA_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

/** `AAAA-MM-DD` de um dia que existe no calendário (rejeita 2026-02-30). */
export function dataIsoValida(valor: string | undefined): valor is string {
  if (!valor) return false;
  const m = RE_DATA_ISO.exec(valor);
  if (!m) return false;
  const [ano, mes, dia] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const data = new Date(ano, mes - 1, dia);
  return data.getFullYear() === ano && data.getMonth() === mes - 1 && data.getDate() === dia;
}

export function formatarDataIso(data: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${data.getFullYear()}-${pad(data.getMonth() + 1)}-${pad(data.getDate())}`;
}

export function formatarDataBr(valorIso: string): string {
  const [ano, mes, dia] = valorIso.split("-");
  return `${dia}/${mes}/${ano}`;
}

function inicioDoDia(data: Date): Date {
  return new Date(data.getFullYear(), data.getMonth(), data.getDate(), 0, 0, 0, 0);
}
function fimDoDia(data: Date): Date {
  return new Date(data.getFullYear(), data.getMonth(), data.getDate(), 23, 59, 59, 999);
}
function somarDias(data: Date, dias: number): Date {
  return new Date(data.getFullYear(), data.getMonth(), data.getDate() + dias, data.getHours(), data.getMinutes(), data.getSeconds(), data.getMilliseconds());
}
function dataLocal(valorIso: string): Date {
  const [ano, mes, dia] = valorIso.split("-").map(Number);
  return new Date(ano, mes - 1, dia);
}

export type IntervaloData = { inicio: Date | null; fim: Date | null };

/** Atalhos de data conhecidos. Cada domínio escolhe quais oferece (ex.: "atrasado" só faz sentido para prazo). */
export const PRESETS_DATA: Record<string, PresetData> = {
  hoje: { value: "hoje", label: "Hoje" },
  amanha: { value: "amanha", label: "Amanhã" },
  ontem: { value: "ontem", label: "Ontem" },
  esta_semana: { value: "esta_semana", label: "Esta semana" },
  este_mes: { value: "este_mes", label: "Este mês" },
  atrasado: { value: "atrasado", label: "Atrasado" },
};

/**
 * Operador + valor de uma data → intervalo `[inicio, fim]` INCLUSIVO (qualquer ponta pode ser aberta). Valor inválido
 * (data inexistente, atalho desconhecido) devolve `null`: quem chama simplesmente não aplica o filtro.
 *
 * - `is` + data: o dia inteiro; `before` + data: tudo antes da meia-noite do dia; `after`: tudo depois do fim do dia;
 * - `is` + atalho: hoje/amanhã/ontem (dia inteiro), esta semana (segunda a domingo), este mês, atrasado (já passou).
 */
export function intervaloDaData(operador: OperadorFiltro, valor: string, agora: Date = new Date()): IntervaloData | null {
  if (dataIsoValida(valor)) {
    const dia = dataLocal(valor);
    if (operador === "is") return { inicio: inicioDoDia(dia), fim: fimDoDia(dia) };
    if (operador === "before") return { inicio: null, fim: new Date(inicioDoDia(dia).getTime() - 1) };
    if (operador === "after") return { inicio: new Date(fimDoDia(dia).getTime() + 1), fim: null };
    return null;
  }
  if (operador !== "is") return null; // atalhos só existem com "é"
  switch (valor) {
    case "hoje":
      return { inicio: inicioDoDia(agora), fim: fimDoDia(agora) };
    case "amanha":
      return { inicio: inicioDoDia(somarDias(agora, 1)), fim: fimDoDia(somarDias(agora, 1)) };
    case "ontem":
      return { inicio: inicioDoDia(somarDias(agora, -1)), fim: fimDoDia(somarDias(agora, -1)) };
    case "esta_semana": {
      const diasDesdeSegunda = (agora.getDay() + 6) % 7;
      const segunda = inicioDoDia(somarDias(agora, -diasDesdeSegunda));
      return { inicio: segunda, fim: fimDoDia(somarDias(segunda, 6)) };
    }
    case "este_mes":
      return {
        inicio: new Date(agora.getFullYear(), agora.getMonth(), 1, 0, 0, 0, 0),
        fim: new Date(agora.getFullYear(), agora.getMonth() + 1, 0, 23, 59, 59, 999),
      };
    case "atrasado":
      return { inicio: null, fim: new Date(agora.getTime() - 1) };
    default:
      return null;
  }
}

// ── Estado na URL ─────────────────────────────────────────────────────────────────────────────────────────────────

const OPERADORES: readonly OperadorFiltro[] = ["is", "is_not", "in", "not_in", "before", "after"];
const RE_VALOR_REMOTO = /^[A-Za-z0-9_.:-]{1,64}$/;

/** `operador:v1,v2` — cada valor com `encodeURIComponent` (vírgula/dois-pontos dentro de um valor não quebram o formato). */
export function codificarFiltro(filtro: FiltroAtivo): string {
  return `${filtro.operador}:${filtro.valores.map(encodeURIComponent).join(",")}`;
}

/** Filtros → parâmetros da URL (um parâmetro por campo, na ordem da lista). */
export function filtrosParaParametros(filtros: readonly FiltroAtivo[]): Array<[string, string]> {
  return filtros.map((filtro) => [filtro.campo, codificarFiltro(filtro)]);
}

function valorEhValido(definicao: DefinicaoFiltro, valor: string): boolean {
  if (definicao.tipo === "data") {
    return dataIsoValida(valor) || Boolean(definicao.presets?.some((preset) => preset.value === valor));
  }
  if (definicao.opcoes && !definicao.buscarOpcoes && !definicao.valoresAbertos) return definicao.opcoes.some((opcao) => opcao.value === valor);
  return RE_VALOR_REMOTO.test(valor); // ids / opções no servidor: não dá para conferir a lista, mas o formato é restrito
}

/**
 * Um parâmetro da URL → filtro, ou `null` se estiver malformado. NUNCA lança e nunca confia no que veio: operador, quantidade
 * e valores são revalidados contra a definição do campo; valores inválidos são descartados (o resto do filtro vale).
 */
export function decodificarFiltro(definicao: DefinicaoFiltro, bruto: string | null | undefined): FiltroAtivo | null {
  if (!bruto) return null;
  const separador = bruto.indexOf(":");
  if (separador <= 0) return null;
  const operador = bruto.slice(0, separador) as OperadorFiltro;
  if (!OPERADORES.includes(operador)) return null;

  const valores: string[] = [];
  for (const parte of bruto.slice(separador + 1).split(",")) {
    if (!parte) continue;
    let valor: string;
    try {
      valor = decodeURIComponent(parte);
    } catch {
      continue; // % mal formado
    }
    if (valorEhValido(definicao, valor) && !valores.includes(valor)) valores.push(valor);
    if (valores.length >= MAX_VALORES_POR_FILTRO) break;
  }
  if (valores.length === 0) return null;

  if (definicao.tipo === "data") {
    if (operador === "in" || operador === "not_in" || operador === "is_not") return null;
    const valor = valores[0];
    if ((operador === "before" || operador === "after") && !dataIsoValida(valor)) return null;
    return { campo: definicao.id, operador, valores: [valor] };
  }

  // enum: "é"/"não é" vs "é um de"/"não é um de" seguem a quantidade; sem exclusão, "não é" é descartado.
  if (operador === "before" || operador === "after") return null;
  const negativo = ehNegativo(operador);
  if (negativo && definicao.permiteExcluir === false) return null;
  const unicos = permiteMultiplos(definicao) ? valores : valores.slice(0, 1);
  return { campo: definicao.id, operador: operadorEnum(negativo, unicos.length), valores: unicos };
}

/**
 * Parâmetros da URL → filtros, na ordem das DEFINIÇÕES (estável entre refreshes). Campos desconhecidos e parâmetros que não
 * são filtros (`q`, `periodo`…) são ignorados.
 */
export function decodificarFiltros(obter: (nome: string) => string | null, definicoes: readonly DefinicaoFiltro[]): FiltroAtivo[] {
  const filtros: FiltroAtivo[] = [];
  for (const definicao of definicoes) {
    const filtro = decodificarFiltro(definicao, obter(definicao.id));
    if (filtro) filtros.push(filtro);
  }
  return filtros;
}

/** Mesma lista de filtros? (campo, operador e valores; a ordem entre campos não importa) — evita regravar a URL à toa. */
export function filtrosIguais(a: readonly FiltroAtivo[], b: readonly FiltroAtivo[]): boolean {
  if (a.length !== b.length) return false;
  const assinatura = (filtro: FiltroAtivo) => `${filtro.campo}|${filtro.operador}|${filtro.valores.join("\u0000")}`;
  const outro = new Set(b.map(assinatura));
  return a.every((filtro) => outro.has(assinatura(filtro)));
}
