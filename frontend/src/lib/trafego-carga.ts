// Tráfego V2 — 11B.2B-C: peças PURAS da UI da CARGA semanal. `npm run test:trafego-carga` (node --test, sem DOM).
//
// CARGA ≠ TEMPO. Capacidade vem do expediente; carga vem da estimativa + janela planejada da ETAPA. Nada aqui lê sessões de trabalho (tempo pessoal) nem intervalos de estado (tempo operacional),
// e nenhum texto fala em "horas trabalhadas", ranking ou produtividade. O backend é a autoridade dos números: esta camada só AGREGA o que o contrato já separa (sem recalcular capacidade,
// sem refazer a divisão entre responsáveis/semanas) e FORMATA — e é cuidadosa para nunca apresentar "0% de ocupação" como disponibilidade confiável quando faltam estimativas ou janelas.
import type {
  DepartamentoCarga,
  FiltrosCarga,
  ItemEtapaCarga,
  JanelaCarga,
  ParametrosCarga,
  PessoaCarga,
  PoolSemDepartamentoCarga,
  TipoDetalheCarga,
  CargaSemanal,
} from "../types/trafego-carga.ts";
import { TrafegoOperacionalErro } from "./trafego-operacional.ts";

// ── Minutos e percentuais ─────────────────────────────────────────────────────────────────────────────────────

/**
 * Formatador ÚNICO de minutos de capacidade/carga. Sem decimais ("32h", nunca "32,0h"); negativo preserva o sinal (saldo de sobrecarga é informação, não vira zero).
 *   0 → "0h" · 30 → "30 min" · 480 → "8h" · 510 → "8h 30min" · 1920 → "32h" · -180 → "-3h". `null` (indisponível) → "—".
 */
export function formatarMinutos(minutos: number | null | undefined): string {
  if (minutos === null || minutos === undefined || Number.isNaN(minutos)) return "—";
  const total = Math.round(minutos);
  const sinal = total < 0 ? "-" : "";
  const absoluto = Math.abs(total);
  if (absoluto === 0) return "0h";
  const horas = Math.floor(absoluto / 60);
  const resto = absoluto % 60;
  if (horas === 0) return `${sinal}${resto} min`;
  return resto === 0 ? `${sinal}${horas}h` : `${sinal}${horas}h ${resto}min`;
}

/** Percentual com no máximo 1 casa ("128%", "87,5%"); NUNCA truncado em 100. `null` → "—". */
export function formatarPercentual(percentual: number | null | undefined): string {
  if (percentual === null || percentual === undefined || Number.isNaN(percentual)) return "—";
  const arredondado = Math.round(percentual * 10) / 10;
  return `${Number.isInteger(arredondado) ? String(arredondado) : arredondado.toFixed(1).replace(".", ",")}%`;
}

/** A partir deste percentual (inclusive) a ocupação pede atenção; acima de 100 é sobrecarga. */
export const LIMITE_ATENCAO_PERCENTUAL = 90;

export type TomOcupacao = "neutro" | "normal" | "atencao" | "sobrecarga";

/**
 * Semântica visual da ocupação. `percentual === null` (capacidade zero/indisponível) é neutro — exceto quando há carga sem capacidade nenhuma (planejado > 0 e capacidade 0), que é sobrecarga.
 * 0% nunca é "bom": é "normal" (cor neutra de barra vazia); a mensagem de dados incompletos é que impede a leitura de "equipe livre".
 */
export function tomDaOcupacao(percentual: number | null, planejadoMin: number | null, capacidadeMin: number | null): TomOcupacao {
  if (percentual === null) return planejadoMin !== null && planejadoMin > 0 && capacidadeMin === 0 ? "sobrecarga" : "neutro";
  if (percentual > 100) return "sobrecarga";
  if (percentual >= LIMITE_ATENCAO_PERCENTUAL) return "atencao";
  return "normal";
}

/** Preenchimento GEOMÉTRICO da barra (0–100). O texto continua mostrando o valor real (ex.: 128%). */
export function preenchimentoDaBarra(percentual: number | null): number {
  if (percentual === null || Number.isNaN(percentual)) return 0;
  return Math.min(100, Math.max(0, percentual));
}

// ── Semana e datas (sempre sobre as strings do calendário da EMPRESA; nunca o fuso do navegador) ─────────────

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"] as const;

function partesDaData(iso: string): { ano: number; mes: number; dia: number } {
  const [ano, mes, dia] = iso.slice(0, 10).split("-").map(Number);
  return { ano, mes, dia };
}

/** Soma dias a uma data `YYYY-MM-DD` (aritmética de calendário em UTC: sem horário de verão nem fuso do navegador). */
export function somarDias(iso: string, dias: number): string {
  const { ano, mes, dia } = partesDaData(iso);
  return new Date(Date.UTC(ano, mes - 1, dia + dias)).toISOString().slice(0, 10);
}

/** "20/10". */
export function rotuloDia(iso: string): string {
  const { mes, dia } = partesDaData(iso);
  return `${String(dia).padStart(2, "0")}/${String(mes).padStart(2, "0")}`;
}

/** "19–25 out" (mesmo mês) ou "28 out – 3 nov". Sem ano: a navegação cobre semanas próximas. */
export function rotuloSemana(inicio: string, fim: string): string {
  const a = partesDaData(inicio);
  const b = partesDaData(fim);
  if (a.mes === b.mes && a.ano === b.ano) return `${a.dia}–${b.dia} ${MESES[b.mes - 1]}`;
  return `${a.dia} ${MESES[a.mes - 1]} – ${b.dia} ${MESES[b.mes - 1]}`;
}

/** Dia local (`YYYY-MM-DD`) de um instante no fuso da empresa. */
export function diaNoFuso(instanteIso: string, fuso: string): string {
  const partes = new Intl.DateTimeFormat("en-CA", { timeZone: fuso, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date(instanteIso));
  const valor = (tipo: string) => partes.find((parte) => parte.type === tipo)?.value ?? "";
  return `${valor("year")}-${valor("month")}-${valor("day")}`;
}

export type CabecalhoSemana = {
  rotulo: string;
  /** Só na semana atual: a capacidade/carga contam de hoje até domingo. */
  aviso: string | null;
  /** A semana atual não permite voltar (a v1 não tem histórico de capacidade). */
  podeVoltar: boolean;
  anterior: string;
  proxima: string;
};

export const TEXTO_CAPACIDADE_RESTANTE = "Capacidade restante da semana";

export function cabecalhoDaSemana(dados: Pick<CargaSemanal, "semana" | "meta">): CabecalhoSemana {
  const { semana, meta } = dados;
  const hoje = diaNoFuso(meta.agoraServidor, meta.fusoEmpresa);
  return {
    rotulo: rotuloSemana(semana.inicio, semana.fim),
    aviso: semana.recorteHoje ? `${TEXTO_CAPACIDADE_RESTANTE}: considerando de hoje (${rotuloDia(hoje)}) até domingo (${rotuloDia(semana.fim)}).` : null,
    podeVoltar: !semana.recorteHoje,
    anterior: somarDias(semana.inicio, -7),
    proxima: somarDias(semana.inicio, 7),
  };
}

// ── Consultas ─────────────────────────────────────────────────────────────────────────────────────────────────

export const LIMITE_DETALHE = 100;

/** Query string da consulta. Só inclui o que foi pedido; a consulta PRINCIPAL nunca leva `detalhe`. */
export function consultaDaCarga(parametros: ParametrosCarga): string {
  const busca = new URLSearchParams();
  if (parametros.semana) busca.set("semana", parametros.semana);
  if (parametros.departamentoId) busca.set("departamentoId", parametros.departamentoId);
  if (parametros.usuarioId) busca.set("usuarioId", parametros.usuarioId);
  if (parametros.detalhe) busca.set("detalhe", parametros.detalhe);
  if (parametros.limite) busca.set("limite", String(parametros.limite));
  return busca.toString();
}

/** Consulta principal: semana + filtros. É o backend quem recorta — o cliente nunca filtra e "finge" que recalculou. */
export function parametrosPrincipais(semana: string | null, filtros: FiltrosCarga): ParametrosCarga {
  // Pessoa e departamento são recortes excludentes (o servidor dá precedência à pessoa): a UI nunca manda os dois.
  return { semana, departamentoId: filtros.usuarioId ? null : filtros.departamentoId, usuarioId: filtros.usuarioId, detalhe: null, limite: null };
}

export type AlvoDetalhe = { tipo: TipoDetalheCarga; id: string; nome: string };

/** Consulta do drill-down: UMA chamada ao abrir pessoa/departamento, na semana que está na tela. */
export function parametrosDoDetalhe(alvo: AlvoDetalhe, semana: string): ParametrosCarga {
  return {
    semana,
    departamentoId: alvo.tipo === "departamento" ? alvo.id : null,
    usuarioId: alvo.tipo === "usuario" ? alvo.id : null,
    detalhe: alvo.tipo,
    limite: LIMITE_DETALHE,
  };
}

// ── Qualidade do planejamento ─────────────────────────────────────────────────────────────────────────────────

export type SemEstimativaGlobal = { valor: number; exato: boolean };

/**
 * Quantas etapas distintas estão sem estimativa no recorte. O contrato dá contagens por pessoa/departamento/pool, que podem se sobrepor (uma etapa com dois responsáveis conta nos dois) —
 * somar duplicaria. Por isso:
 *  · com filtro de pessoa/departamento o valor do próprio alvo é EXATO (cada um já deduplica);
 *  · sem filtro, o valor é um LIMITE INFERIOR provado — o pool sem departamento é disjunto de pessoas e pools de departamento, e os baldes "sem janela"/"janela incompleta" são disjuntos entre si;
 *    se o limite inferior coincide com o superior (soma dos conjuntos), o valor é exato; senão a UI diz "pelo menos".
 */
export function semEstimativaDoRecorte(dados: CargaSemanal, filtros: FiltrosCarga): SemEstimativaGlobal {
  if (filtros.usuarioId) return { valor: dados.pessoas.find((p) => p.usuarioId === filtros.usuarioId)?.semEstimativaCount ?? 0, exato: true };
  if (filtros.departamentoId) return { valor: dados.departamentos.find((d) => d.departamentoId === filtros.departamentoId)?.semEstimativaCount ?? 0, exato: true };

  const pool = dados.poolSemDepartamento?.semEstimativaCount ?? 0;
  const maiorPessoa = Math.max(0, ...dados.pessoas.map((p) => p.semEstimativaCount));
  const maiorDepartamento = Math.max(0, ...dados.departamentos.map((d) => d.semEstimativaCount));
  const baldes = dados.naoPlanejado.semJanela.semEstimativaCount + dados.naoPlanejado.janelaIncompleta.semEstimativaCount;
  const inferior = Math.max(pool + Math.max(maiorPessoa, maiorDepartamento), baldes);

  const pessoasSemDepartamento = dados.pessoas.filter((p) => p.departamentoId === null).reduce((soma, p) => soma + p.semEstimativaCount, 0);
  const superior = pool + dados.departamentos.reduce((soma, d) => soma + d.semEstimativaCount, 0) + pessoasSemDepartamento;
  return { valor: inferior, exato: inferior === superior };
}

export type QualidadePlanejamento = {
  semJanela: number;
  janelaIncompleta: number;
  janelaVencida: number;
  semDiaUtil: number;
  semEstimativa: SemEstimativaGlobal;
  /** Qualquer pendência que torne a ocupação apenas "conhecida". */
  incompleto: boolean;
};

export function qualidadeDoPlanejamento(dados: CargaSemanal, filtros: FiltrosCarga): QualidadePlanejamento {
  const semEstimativa = semEstimativaDoRecorte(dados, filtros);
  const semJanela = dados.naoPlanejado.semJanela.etapasCount;
  const janelaIncompleta = dados.naoPlanejado.janelaIncompleta.etapasCount;
  const janelaVencida = dados.pendenciasPlanejamento.janelaVencida.etapasCount;
  const semDiaUtil = dados.pendenciasPlanejamento.semDiaUtil.etapasCount;
  return {
    semJanela,
    janelaIncompleta,
    janelaVencida,
    semDiaUtil,
    semEstimativa,
    incompleto: semEstimativa.valor > 0 || semJanela > 0 || janelaIncompleta > 0 || janelaVencida > 0 || semDiaUtil > 0,
  };
}

function plural(n: number, singular: string, pluralTexto: string): string {
  return `${n} ${n === 1 ? singular : pluralTexto}`;
}

/** Avisos âmbar do planejamento incompleto (vazio quando está tudo planejado e estimado). */
export function avisosDoPlanejamento(q: QualidadePlanejamento): string[] {
  const avisos: string[] = [];
  const sem = q.semEstimativa;
  if (sem.valor > 0) {
    const texto = plural(sem.valor, "etapa sem estimativa", "etapas sem estimativa");
    avisos.push(`${sem.exato ? texto[0].toUpperCase() + texto.slice(1) : `Pelo menos ${texto}`}. A ocupação pode estar subestimada.`);
  }
  const semPlanejamento = q.semJanela + q.janelaIncompleta;
  if (semPlanejamento > 0) {
    avisos.push(`${plural(semPlanejamento, "etapa", "etapas")} sem janela de planejamento completa — não ${semPlanejamento === 1 ? "entra" : "entram"} na ocupação.`);
  }
  if (q.janelaVencida > 0) avisos.push(`${plural(q.janelaVencida, "etapa", "etapas")} com janela vencida: precisa replanejar.`);
  if (q.semDiaUtil > 0) avisos.push(`${plural(q.semDiaUtil, "etapa", "etapas")} com janela sem capacidade disponível.`);
  return avisos;
}

export const TITULO_PLANEJAMENTO_INCOMPLETO = "O planejamento desta semana está incompleto";

// ── Resumo superior ───────────────────────────────────────────────────────────────────────────────────────────

export type PoolForaDaCapacidade = { chave: string; nome: string; planejadoMin: number };

export type ResumoCarga = {
  /** Preenchido = sem calendário confiável: capacidade, planejado, saldo e ocupação são `null` (nunca zero). */
  capacidadeIndisponivel: string | null;
  capacidadeMin: number | null;
  planejadoMin: number | null;
  saldoMin: number | null;
  ocupacaoPercentual: number | null;
  tom: TomOcupacao;
  /** Pools de departamento SEM pessoas: têm trabalho, mas nenhuma capacidade no denominador. Ficam fora do resumo. */
  poolsSemCapacidade: PoolForaDaCapacidade[];
  /** Pool sem departamento (quando há etapas): nunca diluído na capacidade das pessoas. */
  poolSemDepartamento: PoolSemDepartamentoCarga | null;
};

/**
 * Resumo global SEM dupla contagem.
 *  · capacidade = soma das pessoas elegíveis;
 *  · planejado  = soma do planejado das PESSOAS + `planejadoPoolMin` dos departamentos que têm pessoas (o pool consome a capacidade delas).
 *    NUNCA se soma `departamentos[].planejadoMin` por cima: ele já inclui as pessoas do departamento.
 *  · pool de departamento sem pessoas e pool sem departamento não têm denominador confiável → listados à parte.
 */
export function resumoDaCarga(dados: CargaSemanal): ResumoCarga {
  const indisponivel = dados.capacidade.capacidadeIndisponivel;
  const poolsSemCapacidade = dados.departamentos
    .filter((d) => d.pessoasCount === 0 && (d.planejadoPoolMin ?? 0) > 0)
    .map((d) => ({ chave: d.departamentoId, nome: d.nome || "Departamento", planejadoMin: d.planejadoPoolMin ?? 0 }));
  const poolSemDepartamento = dados.poolSemDepartamento && dados.poolSemDepartamento.etapasCount > 0 ? dados.poolSemDepartamento : null;

  if (indisponivel !== null) {
    return { capacidadeIndisponivel: indisponivel, capacidadeMin: null, planejadoMin: null, saldoMin: null, ocupacaoPercentual: null, tom: "neutro", poolsSemCapacidade, poolSemDepartamento };
  }

  const capacidadeMin = dados.pessoas.reduce((soma, p) => soma + (p.capacidadeAlocavelMin ?? 0), 0);
  const dasPessoas = dados.pessoas.reduce((soma, p) => soma + (p.planejadoMin ?? 0), 0);
  const dosPools = dados.departamentos.filter((d) => d.pessoasCount > 0).reduce((soma, d) => soma + (d.planejadoPoolMin ?? 0), 0);
  const planejadoMin = dasPessoas + dosPools;
  const ocupacaoPercentual = capacidadeMin > 0 ? Math.round((planejadoMin / capacidadeMin) * 1000) / 10 : null;
  return {
    capacidadeIndisponivel: null,
    capacidadeMin,
    planejadoMin,
    saldoMin: capacidadeMin - planejadoMin,
    ocupacaoPercentual,
    tom: tomDaOcupacao(ocupacaoPercentual, planejadoMin, capacidadeMin),
    poolsSemCapacidade,
    poolSemDepartamento,
  };
}

export const TEXTO_CAPACIDADE_INDISPONIVEL = "Capacidade indisponível";
export const TEXTO_EXPEDIENTE_DESATIVADO = "O controle de expediente está desativado, então não há calendário confiável para calcular a capacidade da semana.";

export function explicacaoCapacidadeIndisponivel(motivo: string | null): string | null {
  if (motivo === null) return null;
  return motivo === "expediente_desligado" ? TEXTO_EXPEDIENTE_DESATIVADO : "Não há calendário confiável para calcular a capacidade desta semana.";
}

/** "Ocupação conhecida" quando há pendências que podem esconder carga; "Ocupação" quando o planejamento está completo. */
export function rotuloDaOcupacao(q: QualidadePlanejamento): string {
  return q.incompleto ? "Ocupação conhecida" : "Ocupação";
}

export type IndicadorResumo = { id: "capacidade" | "planejado" | "disponivel" | "ocupacao"; rotulo: string; valor: string; ajuda: string; tom: TomOcupacao };

/** Os quatro indicadores compactos. Com planejamento incompleto, o texto de apoio deixa claro que o valor é só o que está estimado e com janela. */
export function indicadoresDoResumo(resumo: ResumoCarga, q: QualidadePlanejamento): IndicadorResumo[] {
  const indisponivel = resumo.capacidadeIndisponivel !== null;
  return [
    { id: "capacidade", rotulo: "Capacidade alocável", valor: indisponivel ? "Indisponível" : formatarMinutos(resumo.capacidadeMin), ajuda: indisponivel ? "sem calendário confiável" : "soma das pessoas elegíveis", tom: "neutro" },
    {
      id: "planejado",
      rotulo: "Planejado",
      valor: indisponivel ? "—" : formatarMinutos(resumo.planejadoMin),
      ajuda: indisponivel ? "indisponível" : q.incompleto ? "só etapas estimadas e com janela" : "etapas estimadas e com janela",
      tom: "neutro",
    },
    {
      id: "disponivel",
      rotulo: "Disponível",
      valor: indisponivel ? "—" : formatarMinutos(resumo.saldoMin),
      ajuda: indisponivel ? "indisponível" : q.incompleto ? "pode ser menor com o planejamento completo" : "capacidade menos planejado",
      tom: resumo.saldoMin !== null && resumo.saldoMin < 0 ? "sobrecarga" : "neutro",
    },
    {
      id: "ocupacao",
      rotulo: rotuloDaOcupacao(q),
      valor: indisponivel ? "—" : formatarPercentual(resumo.ocupacaoPercentual),
      ajuda: indisponivel ? "indisponível" : q.incompleto ? "do que já está estimado e planejado" : "planejado ÷ capacidade alocável",
      tom: resumo.tom,
    },
  ];
}

// ── Linhas das tabelas ────────────────────────────────────────────────────────────────────────────────────────

export type LinhaOcupacao = { texto: string; percentual: number | null; preenchimento: number; tom: TomOcupacao; semCapacidade: boolean };

function ocupacaoDaLinha(percentual: number | null, planejadoMin: number | null, capacidadeMin: number | null): LinhaOcupacao {
  const tom = tomDaOcupacao(percentual, planejadoMin, capacidadeMin);
  const semCapacidade = percentual === null && planejadoMin !== null && planejadoMin > 0 && capacidadeMin === 0;
  return { texto: semCapacidade ? "Sem capacidade" : formatarPercentual(percentual), percentual, preenchimento: semCapacidade ? 100 : preenchimentoDaBarra(percentual), tom, semCapacidade };
}

export type LinhaPessoa = {
  usuarioId: string;
  nome: string;
  departamento: string | null;
  capacidade: string;
  planejado: string;
  disponivel: string;
  /** `saldoMin < 0` — sobrecarga: o disponível negativo é exibido como é ("-3h"). */
  disponivelNegativo: boolean;
  ocupacao: LinhaOcupacao;
  /** Minutos já conhecidos de etapas fora da ocupação (sem janela/incompletas) + pendências; `null` quando não há. */
  aPlanejar: string | null;
  semEstimativa: number;
};

export function linhaDaPessoa(pessoa: PessoaCarga, nomeDoDepartamento: string | null): LinhaPessoa {
  const conhecidoFora = pessoa.naoPlanejadoMin + pessoa.pendenciasPlanejamentoMin;
  return {
    usuarioId: pessoa.usuarioId,
    nome: pessoa.nome,
    departamento: nomeDoDepartamento,
    capacidade: formatarMinutos(pessoa.capacidadeAlocavelMin),
    planejado: formatarMinutos(pessoa.planejadoMin),
    disponivel: formatarMinutos(pessoa.saldoMin),
    disponivelNegativo: pessoa.saldoMin !== null && pessoa.saldoMin < 0,
    ocupacao: ocupacaoDaLinha(pessoa.ocupacaoPercentual, pessoa.planejadoMin, pessoa.capacidadeAlocavelMin),
    aPlanejar: conhecidoFora > 0 ? formatarMinutos(conhecidoFora) : null,
    semEstimativa: pessoa.semEstimativaCount,
  };
}

export type LinhaDepartamento = {
  departamentoId: string;
  nome: string;
  pessoas: number;
  capacidade: string;
  /** Total do departamento: pessoas + pool (o pool já está incluído aqui). */
  planejado: string;
  /** Trabalho do departamento ainda sem pessoa atribuída — SUBCONJUNTO do planejado, nunca somado de novo. `null` = sem pool. */
  pool: string | null;
  disponivel: string;
  disponivelNegativo: boolean;
  ocupacao: LinhaOcupacao;
  aPlanejar: string | null;
  semEstimativa: number;
};

export function linhaDoDepartamento(departamento: DepartamentoCarga): LinhaDepartamento {
  const conhecidoFora = departamento.naoPlanejadoMin + departamento.pendenciasPlanejamentoMin;
  return {
    departamentoId: departamento.departamentoId,
    nome: departamento.nome || "Departamento",
    pessoas: departamento.pessoasCount,
    capacidade: formatarMinutos(departamento.capacidadeAlocavelMin),
    planejado: formatarMinutos(departamento.planejadoMin),
    pool: departamento.planejadoPoolMin !== null && departamento.planejadoPoolMin > 0 ? formatarMinutos(departamento.planejadoPoolMin) : null,
    disponivel: formatarMinutos(departamento.saldoMin),
    disponivelNegativo: departamento.saldoMin !== null && departamento.saldoMin < 0,
    ocupacao: ocupacaoDaLinha(departamento.ocupacaoPercentual, departamento.planejadoMin, departamento.capacidadeAlocavelMin),
    aPlanejar: conhecidoFora > 0 ? formatarMinutos(conhecidoFora) : null,
    semEstimativa: departamento.semEstimativaCount,
  };
}

export type EstadoVazioCarga = { titulo: string; descricao: string };

/** Sem pessoas nem departamentos para mostrar. Mensagem factual — nunca "sem dados" quando há capacidade. */
export function estadoVazioDaCarga(dados: CargaSemanal, filtros: FiltrosCarga): EstadoVazioCarga | null {
  if (dados.pessoas.length > 0 || dados.departamentos.length > 0) return null;
  const comFiltro = Boolean(filtros.departamentoId || filtros.usuarioId);
  return {
    titulo: comFiltro ? "Não há pessoas elegíveis para capacidade neste filtro." : "Não há pessoas elegíveis para capacidade.",
    descricao: "Entram na capacidade usuários ativos, com acesso ao sistema, que não sejam contas de sistema.",
  };
}

// ── Itens de etapa (pendências e drill-down) ──────────────────────────────────────────────────────────────────

export const ROTULO_ORIGEM: Record<string, string> = {
  responsavel: "Responsável",
  pool_departamento: "Pool do departamento",
  pool_sem_departamento: "Pool sem departamento",
};

/** Origem em linguagem de gestão — nunca o enum cru. */
export function rotuloDaOrigem(origem: string): string {
  return ROTULO_ORIGEM[origem] ?? "Outra origem";
}

/** "20/10 – 23/10" · "A partir de 20/10" (planejamento incompleto: não é prazo) · "Sem janela". */
export function rotuloDaJanela(janela: Pick<JanelaCarga, "planejadoInicio" | "planejadoFim">): string {
  const { planejadoInicio: inicio, planejadoFim: fim } = janela;
  if (inicio && fim) return `${rotuloDia(inicio)} – ${rotuloDia(fim)}`;
  if (inicio) return `A partir de ${rotuloDia(inicio)}`;
  return "Sem janela";
}

export type SeloItem = { id: string; texto: string; tom: "neutro" | "ambar" | "vermelho" };

/** Selos de estado de um item, em linguagem de gestão. Uma etapa pode ter mais de um (ex.: sem janela E sem estimativa). */
export function selosDoItem(item: ItemEtapaCarga): SeloItem[] {
  const selos: SeloItem[] = [];
  if (item.alocacaoEstado === "janela_vencida") selos.push({ id: "janela_vencida", texto: "Precisa replanejar", tom: "vermelho" });
  else if (item.alocacaoEstado === "sem_dia_util") selos.push({ id: "sem_dia_util", texto: "Janela sem capacidade disponível", tom: "ambar" });
  else if (item.motivoNaoPlanejado === "sem_janela") selos.push({ id: "sem_janela", texto: "Sem janela", tom: "ambar" });
  else if (item.motivoNaoPlanejado === "janela_incompleta") selos.push({ id: "janela_incompleta", texto: "Planejamento incompleto", tom: "ambar" });
  else if (item.alocacaoEstado === "alocada") {
    selos.push({ id: "alocada", texto: (item.planejadoNaSemanaMin ?? 0) > 0 ? "Planejada" : "Planejada em outras semanas", tom: "neutro" });
  }
  if (item.estimativaMin === null) selos.push({ id: "sem_estimativa", texto: "Sem estimativa", tom: "ambar" });
  return selos;
}

/** Itens que o gestor precisa planejar/estimar: ganham a ação discreta "Planejar". */
export function itemPrecisaDePlanejamento(item: ItemEtapaCarga): boolean {
  return (
    item.estimativaMin === null ||
    item.motivoNaoPlanejado !== null ||
    item.alocacaoEstado === "janela_vencida" ||
    item.alocacaoEstado === "sem_dia_util"
  );
}

export type LinhaItem = {
  /** Chave de lista: demanda + etapa (único por item; nunca exibida). */
  chave: string;
  demandaId: string;
  demanda: string;
  cliente: string | null;
  projeto: string | null;
  etapa: string;
  estimativa: string;
  /** Parte do alvo consultado nesta semana; `null` = não há distribuição (pendência, sem janela, sem estimativa). */
  naSemana: string | null;
  /** Quando a etapa é dividida: o total da etapa na semana, para explicar a parte. */
  totalDaEtapaNaSemana: string | null;
  janela: string;
  selos: SeloItem[];
  origem: string;
  dividido: string | null;
  precisaPlanejar: boolean;
};

export function linhaDoItem(item: ItemEtapaCarga): LinhaItem {
  const dividido = item.divididoEntre > 1;
  return {
    chave: `${item.demandaId}:${item.etapaId}`,
    demandaId: item.demandaId,
    demanda: `${item.identificador} — ${item.titulo}`,
    cliente: item.cliente?.nome ?? null,
    projeto: item.projeto?.nome ?? null,
    etapa: item.etapaNome,
    // Sem estimativa: o selo "Sem estimativa" já diz; a célula fica "—" (nunca "0h").
    estimativa: item.estimativaMin === null ? "—" : formatarMinutos(item.estimativaMin),
    naSemana: item.parteMin === null ? null : formatarMinutos(item.parteMin),
    totalDaEtapaNaSemana: dividido && item.planejadoNaSemanaMin !== null ? formatarMinutos(item.planejadoNaSemanaMin) : null,
    janela: rotuloDaJanela(item.janela),
    selos: selosDoItem(item),
    origem: rotuloDaOrigem(item.origem),
    dividido: dividido ? `Dividido entre ${item.divididoEntre}` : null,
    precisaPlanejar: itemPrecisaDePlanejamento(item),
  };
}

/** Aba da Demanda onde a estimativa e a janela da etapa são editadas. */
export const ABA_PLANEJAMENTO_DA_DEMANDA = "workflow";

// ── Seções de planejamento (resumo por balde) ─────────────────────────────────────────────────────────────────

export type LinhaBalde = { id: string; titulo: string; ajuda: string; etapas: number; minutos: string; semEstimativa: number };

/** "Precisa de planejamento": etapas FORA da ocupação (sem janela / janela incompleta). Os minutos são só os conhecidos. */
export function baldesDeNaoPlanejado(dados: Pick<CargaSemanal, "naoPlanejado">): LinhaBalde[] {
  const { semJanela, janelaIncompleta } = dados.naoPlanejado;
  return [
    { id: "sem_janela", titulo: "Sem janela", ajuda: "Nenhuma data de início ou fim planejada.", etapas: semJanela.etapasCount, minutos: formatarMinutos(semJanela.minutosConhecidos), semEstimativa: semJanela.semEstimativaCount },
    {
      id: "janela_incompleta",
      titulo: "Planejamento incompleto",
      ajuda: "Tem data de início, mas falta o fim da janela.",
      etapas: janelaIncompleta.etapasCount,
      minutos: formatarMinutos(janelaIncompleta.minutosConhecidos),
      semEstimativa: janelaIncompleta.semEstimativaCount,
    },
  ];
}

export function algumNaoPlanejado(dados: Pick<CargaSemanal, "naoPlanejado">): boolean {
  return dados.naoPlanejado.semJanela.etapasCount > 0 || dados.naoPlanejado.janelaIncompleta.etapasCount > 0;
}

export function algumaPendencia(dados: Pick<CargaSemanal, "pendenciasPlanejamento">): boolean {
  return dados.pendenciasPlanejamento.janelaVencida.etapasCount > 0 || dados.pendenciasPlanejamento.semDiaUtil.etapasCount > 0;
}

/** Quantidade de itens de um balde de pendência que ficou de fora da lista (limite da API). */
export function itensOcultos(etapasCount: number, itens: readonly unknown[]): number {
  return Math.max(0, etapasCount - itens.length);
}

// ── Texto auditável ───────────────────────────────────────────────────────────────────────────────────────────

/** Expressões que NUNCA podem aparecer na Carga (leitura de "equipe livre" ou de tempo trabalhado). */
export const TEXTOS_PROIBIDOS_NA_CARGA: readonly RegExp[] = [
  /equipe livre/i,
  /toda a? ?capacidade dispon[ií]vel/i,
  /sem sobrecarga/i,
  /sem problemas de capacidade/i,
  /100% dispon[ií]vel/i,
  /horas trabalhadas/i,
  /trabalhou/i,
];

// ── Erros ─────────────────────────────────────────────────────────────────────────────────────────────────────

/** Erro LOCAL da Carga (o Shell nunca é desmontado). 401 é do handler global de sessão expirada; aqui só o que a tela explica. */
export function mensagemDeErroCarga(erro: unknown): string {
  const status = erro instanceof TrafegoOperacionalErro ? erro.status : 0;
  if (status === 403) return "Você não tem acesso à Carga semanal. Ela é restrita à gestão autorizada.";
  if (status === 404) return "O filtro escolhido não existe mais. Atualize a tela e escolha novamente.";
  if (status === 422) return "Esta semana não está disponível. A Carga mostra a semana atual e as futuras.";
  return "Não foi possível carregar a Carga semanal.";
}
