// 11B.2D-B — regras PURAS da UI administrativa de Jornada e Ausências do Usuário. `npm run test:usuario-capacidade` (node --test, sem DOM).
//
// É PLANEJAMENTO DE CAPACIDADE, não folha: nada aqui fala em horas trabalhadas, banco de horas, saldo de férias ou produtividade. A jornada individual SUBSTITUI a semana recorrente da empresa;
// a ausência zera dias inteiros. Quem calcula o efeito é o backend (a Carga) — esta camada só valida o formulário, formata e monta o envio. O backend segue sendo a autoridade de tudo.
import {
  DIAS_ORDEM,
  DIAS_SIGLA,
  diasNormalizados,
  errosDaSemana,
  formatarDataIso,
  horasDoDia,
  normalizarHora,
  ordenarPeriodos,
  resumoDoDia,
} from "./expediente-periodos.ts";
import type { DiaSemana, PeriodoExpediente } from "../types/regra-expediente.ts";
import type { AusenciaDraft, AusenciaPatch, AusenciaUsuario, JornadaDiaUsuario, JornadaUsuario, TipoAusencia } from "../types/usuario-capacidade.ts";

// ── Textos ────────────────────────────────────────────────────────────────────────────────────────────────────

export const TITULO_SECAO = "Jornada e ausências";
export const TEXTO_JORNADA_EMPRESA = "Este usuário segue os horários definidos no expediente da empresa.";
export const TEXTO_JORNADA_PERSONALIZADA = "A jornada personalizada substitui a semana do expediente da empresa para este usuário. Dia sem período fica fechado.";
export const TEXTO_IMPACTO_CARGA = "As jornadas e ausências alteram a capacidade exibida em Tráfego → Carga.";
export const TEXTO_DIAS_ESPECIAIS = "Dias especiais da empresa (feriados, recessos e trabalho excepcional) continuam sendo aplicados.";
export const TEXTO_CONFIRMAR_VOLTAR_EMPRESA = "Remover a jornada personalizada deste usuário? Ele voltará a usar o expediente da empresa.";
export const TEXTO_CONFIRMAR_REMOVER_AUSENCIA = "Remover esta ausência?";
export const TEXTO_AUSENCIA_DIA_INTEIRO = "Toda ausência cobre dias inteiros, do início ao fim, inclusive.";
export const TEXTO_SOBREPOSICAO = "Este período se sobrepõe a outra ausência.";
export const TEXTO_JORNADA_TODA_FECHADA = "Todos os dias estão fechados: a capacidade deste usuário será zero.";
export const TEXTO_SEM_AUSENCIAS = "Nenhuma ausência cadastrada.";
export const TEXTO_SOMENTE_LEITURA = "Você pode consultar, mas não editar a jornada e as ausências deste usuário.";

/** Expressões que NUNCA podem aparecer nesta UI (leitura de folha, produtividade ou "descontado"). */
export const TEXTOS_PROIBIDOS_NA_CAPACIDADE: readonly RegExp[] = [/capacidade contratual/i, /SLA pessoal/i, /horas produtivas/i, /produtividade/i, /horas trabalhadas/i, /banco de horas/i, /saldo de f[eé]rias/i, /descontad/i];

// ── Ausências: tipos e rótulos ────────────────────────────────────────────────────────────────────────────────

export const OPCOES_TIPO_AUSENCIA: ReadonlyArray<{ value: TipoAusencia; label: string }> = [
  { value: "ferias", label: "Férias" },
  { value: "afastamento", label: "Afastamento" },
  { value: "folga", label: "Folga" },
  { value: "outro", label: "Outro" },
];

/** Nunca mostra o enum cru: tipo desconhecido vira "Outro". */
export function rotuloDoTipoAusencia(tipo: string): string {
  return OPCOES_TIPO_AUSENCIA.find((opcao) => opcao.value === tipo)?.label ?? "Outro";
}

// ── Datas (sempre sobre strings do calendário; nunca `new Date("YYYY-MM-DD")`, que deslocaria o dia pelo fuso) ──────

function paraUtc(iso: string): number {
  const [ano, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return Date.UTC(ano, mes - 1, dia);
}

/** Dias do intervalo, inclusive. Um dia só (início = fim) → 1. */
export function diasDaAusencia(inicio: string, fim: string): number {
  return Math.round((paraUtc(fim) - paraUtc(inicio)) / 86_400_000) + 1;
}

/** "20/11/2026" (um dia) ou "03/11/2026 – 13/11/2026". */
export function formatarPeriodoAusencia(inicio: string, fim: string): string {
  return inicio === fim ? formatarDataIso(inicio) : `${formatarDataIso(inicio)} – ${formatarDataIso(fim)}`;
}

export function rotuloDuracaoAusencia(inicio: string, fim: string): string {
  const dias = diasDaAusencia(inicio, fim);
  return dias === 1 ? "1 dia" : `${dias} dias`;
}

/** Data de hoje do NAVEGADOR (`YYYY-MM-DD`) — só para ordenar/esmaecer a lista; o cálculo de capacidade é todo do backend, no calendário da empresa. */
export function hojeLocalIso(agora: Date = new Date()): string {
  const dois = (n: number) => String(n).padStart(2, "0");
  return `${agora.getFullYear()}-${dois(agora.getMonth() + 1)}-${dois(agora.getDate())}`;
}

/**
 * Atuais e futuras primeiro (a mais próxima no topo), passadas depois (a mais recente primeiro) com visual secundário. Nada é escondido. `fim` é o último dia (inclusive): uma ausência
 * que termina hoje ainda é atual.
 */
export function separarAusencias(ausencias: readonly AusenciaUsuario[], hoje: string): { proximas: AusenciaUsuario[]; passadas: AusenciaUsuario[] } {
  const proximas = ausencias.filter((a) => a.fim >= hoje).sort((a, b) => (a.inicio < b.inicio ? -1 : a.inicio > b.inicio ? 1 : a.fim < b.fim ? -1 : 0));
  const passadas = ausencias.filter((a) => a.fim < hoje).sort((a, b) => (a.inicio < b.inicio ? 1 : a.inicio > b.inicio ? -1 : 0));
  return { proximas, passadas };
}

// ── Ausências: formulário ─────────────────────────────────────────────────────────────────────────────────────

export const MAX_OBSERVACAO = 500;

export const AUSENCIA_VAZIA: AusenciaDraft = { tipo: "ferias", inicio: "", fim: "", observacao: "" };

export function draftDaAusencia(ausencia: AusenciaUsuario): AusenciaDraft {
  const tipo = OPCOES_TIPO_AUSENCIA.some((opcao) => opcao.value === ausencia.tipo) ? (ausencia.tipo as TipoAusencia) : "outro";
  return { tipo, inicio: ausencia.inicio, fim: ausencia.fim, observacao: ausencia.observacao ?? "" };
}

export type ErrosAusencia = Partial<Record<"inicio" | "fim" | "observacao", string>>;

/** Validação do formulário (o backend repete). Só datas inteiras — não existe hora. */
export function validarAusencia(draft: AusenciaDraft): ErrosAusencia {
  const erros: ErrosAusencia = {};
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.inicio)) erros.inicio = "Informe a data inicial.";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.fim)) erros.fim = "Informe a data final.";
  if (!erros.inicio && !erros.fim && draft.fim < draft.inicio) erros.fim = "A data final não pode ser anterior à inicial.";
  if (draft.observacao.length > MAX_OBSERVACAO) erros.observacao = `A observação aceita até ${MAX_OBSERVACAO} caracteres.`;
  return erros;
}

/** Aviso (nunca bloqueio): o backend aceita ausências sobrepostas e o dia coberto por duas continua sem capacidade, sem desconto duplo. */
export function sobrepoeOutraAusencia(draft: Pick<AusenciaDraft, "inicio" | "fim">, existentes: readonly AusenciaUsuario[], ignorarId?: string): boolean {
  if (!draft.inicio || !draft.fim || draft.fim < draft.inicio) return false;
  return existentes.some((a) => a.id !== ignorarId && a.inicio <= draft.fim && a.fim >= draft.inicio);
}

/** Corpo do POST. `observacao` vazia vai como `null` (sem observação). */
export function corpoDaAusencia(draft: AusenciaDraft): { tipo: TipoAusencia; inicio: string; fim: string; observacao: string | null } {
  return { tipo: draft.tipo, inicio: draft.inicio, fim: draft.fim, observacao: draft.observacao.trim() || null };
}

/** Corpo do PATCH com SÓ o que mudou; `null` quando nada mudou (nenhuma chamada). */
export function patchDaAusencia(original: AusenciaUsuario, draft: AusenciaDraft): AusenciaPatch | null {
  const patch: AusenciaPatch = {};
  if (draft.tipo !== original.tipo) patch.tipo = draft.tipo;
  if (draft.inicio !== original.inicio) patch.inicio = draft.inicio;
  if (draft.fim !== original.fim) patch.fim = draft.fim;
  const observacao = draft.observacao.trim() || null;
  if (observacao !== (original.observacao ?? null)) patch.observacao = observacao;
  return Object.keys(patch).length === 0 ? null : patch;
}

// ── Jornada ───────────────────────────────────────────────────────────────────────────────────────────────────

export type ModoJornada = "empresa" | "personalizada";

type DiaApi = { diaSemana: number; periodos: Array<{ inicio: string; fim: string }> };

/** Os 7 dias, em ordem, horas "HH:MM" (a API devolve "HH:MM:SS"). */
export function normalizarJornadaDaApi(api: Omit<JornadaUsuario, "dias"> & { dias: DiaApi[] }): JornadaUsuario {
  const dias = diasNormalizados(api.dias.map((dia) => ({ diaSemana: dia.diaSemana as DiaSemana, periodos: dia.periodos.map((p) => ({ inicio: p.inicio, fim: p.fim })) })));
  return { usuarioId: api.usuarioId, personalizada: api.personalizada, dias, updatedAt: api.updatedAt ?? null };
}

/** Cópia EDITÁVEL da grade (sugestão inicial ao escolher "Jornada personalizada": o expediente da empresa só como ponto de partida VISUAL — nada é gravado até Salvar). */
export function grade(dias: readonly JornadaDiaUsuario[]): JornadaDiaUsuario[] {
  return diasNormalizados(dias);
}

export function jornadaIgual(a: readonly JornadaDiaUsuario[], b: readonly JornadaDiaUsuario[]): boolean {
  return JSON.stringify(diasNormalizados(a)) === JSON.stringify(diasNormalizados(b));
}

/** Há algo a salvar? Escolher "Jornada personalizada" sem jornada gravada já é uma mudança pendente (a escolha só vale depois de Salvar). */
export function jornadaPendente(servidor: Pick<JornadaUsuario, "personalizada" | "dias">, modo: ModoJornada, dias: readonly JornadaDiaUsuario[]): boolean {
  if (modo !== "personalizada") return false;
  if (!servidor.personalizada) return true;
  return !jornadaIgual(servidor.dias, dias);
}

export function errosDaJornada(dias: readonly JornadaDiaUsuario[]): Partial<Record<DiaSemana, string>> {
  return errosDaSemana(dias);
}

export function podeSalvarJornada(args: { servidor: Pick<JornadaUsuario, "personalizada" | "dias">; modo: ModoJornada; dias: readonly JornadaDiaUsuario[]; somenteLeitura: boolean; salvando: boolean }): boolean {
  const { servidor, modo, dias, somenteLeitura, salvando } = args;
  return !somenteLeitura && !salvando && jornadaPendente(servidor, modo, dias) && Object.keys(errosDaJornada(dias)).length === 0;
}

/** Corpo do PUT: a grade completa (7 dias). */
export function corpoDaJornada(dias: readonly JornadaDiaUsuario[]): Array<{ diaSemana: DiaSemana; periodos: PeriodoExpediente[] }> {
  return diasNormalizados(dias).map((dia) => ({ diaSemana: dia.diaSemana, periodos: ordenarPeriodos(dia.periodos.map((p) => ({ inicio: normalizarHora(p.inicio), fim: normalizarHora(p.fim) }))) }));
}

export function jornadaTodaFechada(dias: readonly JornadaDiaUsuario[]): boolean {
  return dias.every((dia) => dia.periodos.length === 0);
}

export function horasDaSemana(dias: readonly JornadaDiaUsuario[]): number {
  return Math.round(dias.reduce((soma, dia) => soma + horasDoDia(dia.periodos), 0) * 10) / 10;
}

/** Resumo de leitura da semana, agrupando dias CONSECUTIVOS iguais: [{ dias: "Seg–Sex", texto: "09:00–12:00 · 13:00–18:00" }, { dias: "Sáb–Dom", texto: "Fechado" }]. */
export function resumoDaSemana(dias: readonly JornadaDiaUsuario[]): Array<{ dias: string; texto: string }> {
  const normalizados = diasNormalizados(dias);
  const grupos: Array<{ inicio: DiaSemana; fim: DiaSemana; texto: string }> = [];
  for (const dia of normalizados) {
    const texto = resumoDoDia(dia.periodos);
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.texto === texto && ultimo.fim === dia.diaSemana - 1) ultimo.fim = dia.diaSemana;
    else grupos.push({ inicio: dia.diaSemana, fim: dia.diaSemana, texto });
  }
  return grupos.map((g) => ({ dias: g.inicio === g.fim ? DIAS_SIGLA[g.inicio] : `${DIAS_SIGLA[g.inicio]}–${DIAS_SIGLA[g.fim]}`, texto: g.texto }));
}

export { DIAS_ORDEM };

// ── Erros ─────────────────────────────────────────────────────────────────────────────────────────────────────

/** A API já responde em português (403 "Seu perfil só administra Usuários.", 404 "Usuário não encontrado", 422 de validação): mostra a mensagem dela; sem mensagem, um texto neutro. 401 é do handler global. */
export function mensagemDeErroCapacidade(erro: unknown, padrao: string): string {
  return erro instanceof Error && erro.message && !/^Erro \d+$/.test(erro.message) ? erro.message : padrao;
}
