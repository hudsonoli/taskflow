// Regras PURAS da Pauta operacional (testáveis com `node --test`): agrupamento, ordem e geometria da timeline. Nenhuma regra de domínio mora aqui — responsabilidade e planejamento
// já chegam resolvidos pelo servidor; a interface só reagrupa o MESMO conjunto de itens por colaborador ou por projeto.
import type { ParametrosPautaOperacional, PautaItem, PautaPessoa } from "../types/pauta-operacional.ts";

export type VisaoPauta = "colaborador" | "projeto";
export type ModoPauta = "gantt" | "lista";
export const VISOES_PAUTA: ReadonlyArray<VisaoPauta> = ["colaborador", "projeto"];
export const MODOS_PAUTA: ReadonlyArray<ModoPauta> = ["gantt", "lista"];
export const PERIODO_PAUTA_DIAS = 28;
export const PASSO_PERIODO_PAUTA_DIAS = 7;

export type TipoGrupoPauta = "colaborador" | "sem-individual" | "sem-responsavel" | "projeto" | "sem-projeto";

export type GrupoPauta = {
  chave: string;
  tipo: TipoGrupoPauta;
  titulo: string;
  /** Departamento(s) do grupo "Sem responsável individual" (rótulos resolvidos por quem chama). */
  itens: PautaItem[];
};

const SEM_INDIVIDUAL = "__sem-individual__";
const SEM_RESPONSAVEL = "__sem-responsavel__";
const SEM_PROJETO = "__sem-projeto__";

const comparadorNome = new Intl.Collator("pt-BR", { sensitivity: "base", numeric: true });

// ── datas puras (YYYY-MM-DD): aritmética em UTC, sem fuso nem horário de verão ───────────────────────────────────────

const FORMATO_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

function paraUtc(iso: string): number {
  const partes = FORMATO_ISO.exec(iso);
  if (!partes) return Number.NaN;
  return Date.UTC(Number(partes[1]), Number(partes[2]) - 1, Number(partes[3]));
}

export function adicionarDias(iso: string, dias: number): string {
  return new Date(paraUtc(iso) + dias * 86_400_000).toISOString().slice(0, 10);
}

export function diferencaEmDias(deIso: string, ateIso: string): number {
  return Math.round((paraUtc(ateIso) - paraUtc(deIso)) / 86_400_000);
}

export function listarDiasDoPeriodo(inicio: string, fim: string): string[] {
  const total = diferencaEmDias(inicio, fim) + 1;
  return Number.isFinite(total) && total > 0 ? Array.from({ length: total }, (_, indice) => adicionarDias(inicio, indice)) : [];
}

export function dataValida(iso: string | null | undefined): iso is string {
  return Boolean(iso) && FORMATO_ISO.test(iso as string) && !Number.isNaN(paraUtc(iso as string));
}

/** Sábado/domingo do calendário (só sombreia a coluna; a Pauta NÃO recalcula dia útil — isso é da Carga). */
export function ehFimDeSemana(iso: string): boolean {
  const dia = new Date(paraUtc(iso)).getUTCDay();
  return dia === 0 || dia === 6;
}

/** "2026-10-22" → "22/10" (sem passar por Date local: nunca desloca o dia). */
export function formatarDiaMes(iso: string | null | undefined): string {
  const partes = iso ? FORMATO_ISO.exec(iso) : null;
  return partes ? `${partes[3]}/${partes[2]}` : "—";
}

// ── geometria ─────────────────────────────────────────────────────────────────────────────────────────────────────

export type PosicaoNaGrade = {
  /** colunas 1-based da CSS grid (fim exclusivo) */
  colunaInicio: number;
  colunaFim: number;
  /** a janela continua além da borda do período exibido */
  cortadaAntes: boolean;
  cortadaDepois: boolean;
};

/** Posição da janela PLANEJADA na grade do período. Só planejado_inicio/planejado_fim — prazo nunca entra. `null` se a janela não cruza o período ou não é completa. */
export function posicaoDaJanela(inicio: string | null, fim: string | null, periodoInicio: string, periodoFim: string): PosicaoNaGrade | null {
  if (!dataValida(inicio) || !dataValida(fim) || fim < inicio) return null;
  if (fim < periodoInicio || inicio > periodoFim) return null;
  const visivelInicio = inicio < periodoInicio ? periodoInicio : inicio;
  const visivelFim = fim > periodoFim ? periodoFim : fim;
  return {
    colunaInicio: diferencaEmDias(periodoInicio, visivelInicio) + 1,
    colunaFim: diferencaEmDias(periodoInicio, visivelFim) + 2,
    cortadaAntes: inicio < periodoInicio,
    cortadaDepois: fim > periodoFim,
  };
}

// ── agrupamento ───────────────────────────────────────────────────────────────────────────────────────────────────

function chaveDeOrdem(item: PautaItem): [string, string, string, number, string] {
  return [item.planejamento.inicio ?? "9999-12-31", item.planejamento.fim ?? "9999-12-31", item.demandaIdentificador, item.etapaOrdem, item.etapaId];
}

export function ordenarItens(itens: readonly PautaItem[]): PautaItem[] {
  return [...itens].sort((a, b) => {
    const [ai, af, ad, ao, ae] = chaveDeOrdem(a);
    const [bi, bf, bd, bo, be] = chaveDeOrdem(b);
    return ai.localeCompare(bi) || af.localeCompare(bf) || comparadorNome.compare(ad, bd) || ao - bo || ae.localeCompare(be);
  });
}

/**
 * Colaboradores com itens, por nome; depois "Sem responsável individual" (tem departamento, falta pessoa) e "Sem responsável" (nem departamento). Um item multi-responsável aparece no grupo de CADA pessoa
 * (a Pauta é agenda/responsabilidade, não rateio: a janela não é dividida). Pessoa fora do catálogo não some: aparece com rótulo neutro.
 */
export function agruparPorColaborador(itens: readonly PautaItem[], pessoas: readonly PautaPessoa[]): GrupoPauta[] {
  const nomes = new Map(pessoas.map((pessoa) => [pessoa.id, pessoa.nome]));
  const porPessoa = new Map<string, PautaItem[]>();
  const semIndividual: PautaItem[] = [];
  const semResponsavel: PautaItem[] = [];
  for (const item of ordenarItens(itens)) {
    const { usuarioIds, departamentoIds } = item.responsabilidadeEfetiva;
    if (usuarioIds.length > 0) {
      for (const usuarioId of usuarioIds) porPessoa.set(usuarioId, [...(porPessoa.get(usuarioId) ?? []), item]);
    } else if (departamentoIds.length > 0) {
      semIndividual.push(item);
    } else {
      semResponsavel.push(item);
    }
  }
  const colaboradores = [...porPessoa.entries()]
    .map(([usuarioId, itensDaPessoa]): GrupoPauta => ({ chave: usuarioId, tipo: "colaborador", titulo: nomes.get(usuarioId) ?? "Usuário indisponível", itens: itensDaPessoa }))
    .sort((a, b) => comparadorNome.compare(a.titulo, b.titulo) || a.chave.localeCompare(b.chave));
  const especiais: GrupoPauta[] = [];
  if (semIndividual.length > 0) especiais.push({ chave: SEM_INDIVIDUAL, tipo: "sem-individual", titulo: "Sem responsável individual", itens: semIndividual });
  if (semResponsavel.length > 0) especiais.push({ chave: SEM_RESPONSAVEL, tipo: "sem-responsavel", titulo: "Sem responsável", itens: semResponsavel });
  return [...colaboradores, ...especiais];
}

/** Com o filtro Colaborador ativo, a visão por colaborador mostra só os colaboradores filtrados (o co-responsável de uma etapa compartilhada não ganha grupo à parte); sem filtro, tudo. */
export function manterColaboradoresFiltrados(grupos: readonly GrupoPauta[], usuarioIds: readonly string[] | undefined): GrupoPauta[] {
  if (!usuarioIds || usuarioIds.length === 0) return [...grupos];
  return grupos.filter((grupo) => grupo.tipo === "colaborador" && usuarioIds.includes(grupo.chave));
}

/** Projetos por nome, depois "Sem projeto". CADA item aparece UMA vez (multi-responsável não duplica aqui). */
export function agruparPorProjeto(itens: readonly PautaItem[], nomeDoProjeto: (projetoId: string) => string): GrupoPauta[] {
  const porProjeto = new Map<string, PautaItem[]>();
  const semProjeto: PautaItem[] = [];
  for (const item of ordenarItens(itens)) {
    if (item.projetoId) porProjeto.set(item.projetoId, [...(porProjeto.get(item.projetoId) ?? []), item]);
    else semProjeto.push(item);
  }
  const projetos = [...porProjeto.entries()]
    .map(([projetoId, itensDoProjeto]): GrupoPauta => ({ chave: projetoId, tipo: "projeto", titulo: nomeDoProjeto(projetoId), itens: itensDoProjeto }))
    .sort((a, b) => comparadorNome.compare(a.titulo, b.titulo) || a.chave.localeCompare(b.chave));
  return semProjeto.length > 0 ? [...projetos, { chave: SEM_PROJETO, tipo: "sem-projeto", titulo: "Sem projeto", itens: semProjeto }] : projetos;
}

export type ItensDoGrupoPorEstado = { planejadas: PautaItem[]; incompletas: PautaItem[]; naoPlanejadas: PautaItem[] };

/** Separa os itens de um grupo pelo estado da JANELA (a timeline só desenha as planejadas; as outras ficam em seções próprias, visíveis). */
export function separarPorPlanejamento(itens: readonly PautaItem[]): ItensDoGrupoPorEstado {
  const grupos: ItensDoGrupoPorEstado = { planejadas: [], incompletas: [], naoPlanejadas: [] };
  for (const item of itens) {
    if (item.planejamento.estado === "planejado") grupos.planejadas.push(item);
    else if (item.planejamento.estado === "incompleto") grupos.incompletas.push(item);
    else grupos.naoPlanejadas.push(item);
  }
  return grupos;
}

/** Ids únicos das etapas do conjunto (a troca de visão nunca muda ESTE conjunto). */
export function idsDasEtapas(grupos: readonly GrupoPauta[]): string[] {
  return [...new Set(grupos.flatMap((grupo) => grupo.itens.map((item) => item.etapaId)))].sort();
}

// ── consulta ──────────────────────────────────────────────────────────────────────────────────────────────────────

/** Parâmetros do GET (só o que tem valor; listas em CSV). */
export function consultaDaPauta(parametros: ParametrosPautaOperacional): Array<[string, string]> {
  const consulta: Array<[string, string]> = [];
  if (parametros.inicio) consulta.push(["inicio", parametros.inicio]);
  if (parametros.fim) consulta.push(["fim", parametros.fim]);
  if (parametros.usuarioIds?.length) consulta.push(["usuarioIds", parametros.usuarioIds.join(",")]);
  if (parametros.departamentoIds?.length) consulta.push(["departamentoIds", parametros.departamentoIds.join(",")]);
  if (parametros.clienteIds?.length) consulta.push(["clienteIds", parametros.clienteIds.join(",")]);
  if (parametros.projetoIds?.length) consulta.push(["projetoIds", parametros.projetoIds.join(",")]);
  if (parametros.prioridades?.length) consulta.push(["prioridades", parametros.prioridades.join(",")]);
  if (parametros.busca?.trim()) consulta.push(["busca", parametros.busca.trim()]);
  return consulta;
}
