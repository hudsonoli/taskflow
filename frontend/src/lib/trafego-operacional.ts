// Tráfego V2 — peças PURAS da UI de métricas operacionais (AGORA e GARGALOS). `npm run test:trafego-operacional` (node --test, sem DOM).
//
// TEMPO OPERACIONAL ≠ TEMPO PESSOAL. Tudo aqui descreve o tempo DECORRIDO de uma tarefa/etapa num ESTADO — nunca "horas trabalhadas" por alguém, e `responsaveis` é ATRIBUIÇÃO
// (não executor). Por isso nenhum texto desta camada usa "trabalhou", "trabalhado", "executando" ou "horas trabalhadas".
import type {
  AgoraDemanda,
  AgoraKpis,
  FilaEtapa,
  GargaloEtapa,
  RefNome,
  TrafegoOperacionalAgora,
  TrafegoOperacionalGargalos,
} from "../types/trafego-operacional.ts";

// ── Visões ────────────────────────────────────────────────────────────────────────────────────────────────────

export type VisaoTrafego = "agora" | "gargalos" | "carga" | "pessoal";
export const VISAO_PADRAO: VisaoTrafego = "agora";
export const VISOES_TRAFEGO: ReadonlyArray<{ id: VisaoTrafego; label: string }> = [
  { id: "agora", label: "Agora" },
  { id: "gargalos", label: "Gargalos" },
  // Carga semanal (11B.2B-C): capacidade do expediente × carga planejada das etapas. Planejamento, não tempo trabalhado.
  { id: "carga", label: "Carga" },
  // Legado: sessões de trabalho abertas manualmente (tempo PESSOAL). Fica numa área secundária e não alimenta nenhuma métrica operacional.
  { id: "pessoal", label: "Tempo pessoal" },
];

/** Visão vinda da URL (`?visao=`): só os valores conhecidos; qualquer outro volta ao padrão (AGORA) — nunca confia no parâmetro. */
export function visaoDaUrl(valor: string | null): VisaoTrafego {
  return VISOES_TRAFEGO.find((visao) => visao.id === valor)?.id ?? VISAO_PADRAO;
}

// ── Período dos gargalos (coerente com o backend: padrão 30 dias, máximo 90) ──────────────────────────────────

export const PERIODO_MAXIMO_DIAS = 90;
export const PERIODOS_GARGALOS = [
  { id: "7d", dias: 7, label: "Últimos 7 dias" },
  { id: "14d", dias: 14, label: "Últimos 14 dias" },
  { id: "30d", dias: 30, label: "Últimos 30 dias" },
  { id: "60d", dias: 60, label: "Últimos 60 dias" },
  { id: "90d", dias: 90, label: "Últimos 90 dias" },
] as const;
export type PeriodoGargalosId = (typeof PERIODOS_GARGALOS)[number]["id"];
export const PERIODO_GARGALOS_PADRAO: PeriodoGargalosId = "30d";

export function periodoGargalosDaUrl(valor: string | null): PeriodoGargalosId {
  return PERIODOS_GARGALOS.find((periodo) => periodo.id === valor)?.id ?? PERIODO_GARGALOS_PADRAO;
}

/** [início, fim] ISO (UTC, com timezone) de "os últimos N dias" terminando em `agora`. Nunca passa de 90 dias. */
export function intervaloDoPeriodo(id: PeriodoGargalosId, agora: Date): { inicio: string; fim: string } {
  const dias = Math.min(PERIODOS_GARGALOS.find((periodo) => periodo.id === id)?.dias ?? 30, PERIODO_MAXIMO_DIAS);
  return { inicio: new Date(agora.getTime() - dias * 86_400_000).toISOString(), fim: agora.toISOString() };
}

// ── Duração ───────────────────────────────────────────────────────────────────────────────────────────────────

/**
 * Formatador ÚNICO de durações operacionais. Sem segundos e sem casas decimais; sempre PISO (59,9 min são "59 min").
 *   < 1 min → "<1 min" · 1–59 min → "34 min" · 1–23 h → "2h 15min" (hora cheia: "2h") · ≥ 24 h → "2d 3h" (dia cheio: "2d")
 * `null`/`undefined` (sem amostra) → "—".
 */
export function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos === null || segundos === undefined || Number.isNaN(segundos)) return "—";
  const total = Math.max(0, Math.floor(segundos));
  const minutosTotais = Math.floor(total / 60);
  if (minutosTotais < 1) return "<1 min";
  if (minutosTotais < 60) return `${minutosTotais} min`;
  const horasTotais = Math.floor(minutosTotais / 60);
  if (horasTotais < 24) {
    const minutos = minutosTotais % 60;
    return minutos === 0 ? `${horasTotais}h` : `${horasTotais}h ${minutos}min`;
  }
  const dias = Math.floor(horasTotais / 24);
  const horas = horasTotais % 24;
  return horas === 0 ? `${dias}d` : `${dias}d ${horas}h`;
}

/**
 * "Há quanto tempo" no estado atual: a idade que o servidor mediu na resposta + o que passou desde que ela CHEGOU (deltas do relógio local — o relógio do navegador nunca é a
 * autoridade inicial, só avança o que o servidor já informou). Sem idade do servidor (Demanda sem intervalo aberto) → `null`: não se inventa.
 */
export function idadeAtualSegundos(idadeBaseSegundos: number | null, recebidoEmMs: number, agoraMs: number): number | null {
  if (idadeBaseSegundos === null) return null;
  return idadeBaseSegundos + Math.max(0, Math.floor((agoraMs - recebidoEmMs) / 1000));
}

/** "1h 24min · 12 itens" — a média NUNCA aparece sem o denominador. `media === null` (sem amostra) → "—". */
export function mediaComAmostra(mediaSegundos: number | null, n: number): { valor: string; amostra: string } {
  return { valor: formatarDuracao(mediaSegundos), amostra: n === 1 ? "1 item" : `${n} itens` };
}

// ── Textos ────────────────────────────────────────────────────────────────────────────────────────────────────

export const ROTULO_TEMPO = {
  execucao: "Tempo em execução",
  pausado: "Tempo pausado",
  bloqueado: "Tempo bloqueado",
  aguardandoCliente: "Aguardando cliente",
} as const;

export const TEXTO_TEMPO_NO_ESTADO = "Tempo no estado atual";
export const TEXTO_AJUDA_TEMPO_OPERACIONAL =
  "Tempos operacionais: quanto tempo as tarefas passam em cada estado (execução, pausa, bloqueio, aguardando cliente). Não são horas trabalhadas por pessoas.";
export const TEXTO_INFO_TRAFEGO_V2 =
  "Gestão operacional: o que precisa de atenção agora e onde o fluxo trava. Os tempos são do estado das tarefas, não horas trabalhadas por pessoas.";
export const TEXTO_ESCOPO_AGORA = "Escopo: planejada, em execução, pausada, bloqueada e aguardando cliente. Rascunho e tarefas finalizadas ficam de fora.";
export const TEXTO_RESPONSAVEIS = "Responsáveis atuais (atribuição) — não indica quem está trabalhando.";
export const TEXTO_TRUNCADA = "Esta atividade já estava nesta etapa quando a medição começou; a idade real pode ser maior.";
export const TEXTO_VAZIO_AGORA = "Nenhuma tarefa em execução agora.";
export const TEXTO_VAZIO_GARGALOS = "Nenhum intervalo encontrado no período.";
export const TEXTO_SEM_DADOS_SUFICIENTES = "Ainda não há dados suficientes para este filtro.";
export const TEXTO_VAZIO_FILA = "Nenhuma tarefa aberta nesta seleção.";

export function rotuloDepartamentos(departamentos: readonly RefNome[]): string {
  return departamentos.length === 0 ? "Sem departamento" : departamentos.map((departamento) => departamento.nome).join(" + ");
}

/** Cliente em primeiro plano; projeto, quando existe, em texto secundário. Sem placeholder feio quando falta. */
export function clienteEProjeto(demanda: Pick<AgoraDemanda, "cliente" | "projeto">): { principal: string | null; secundario: string | null } {
  const cliente = demanda.cliente?.nome ?? null;
  const projeto = demanda.projeto?.nome ?? null;
  if (cliente) return { principal: cliente, secundario: projeto };
  return { principal: projeto, secundario: null };
}

/** Aviso de cobertura parcial. Nunca é erro; nunca esconde as métricas. */
export function avisoCobertura(g: Pick<TrafegoOperacionalGargalos, "coberturaParcial" | "medicaoDesde">, formatarData: (iso: string) => string): string | null {
  if (!g.coberturaParcial) return null;
  if (g.medicaoDesde === null) return "Ainda não há medição operacional registrada.";
  return `Dados operacionais disponíveis a partir de ${formatarData(g.medicaoDesde)}.`;
}

export function formatarDataCurta(iso: string, fuso?: string): string {
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", ...(fuso ? { timeZone: fuso } : {}) }).format(new Date(iso));
}

export function formatarPrazo(iso: string | null, fuso: string): string {
  if (iso === null) return "Sem prazo";
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: fuso }).format(new Date(iso));
}

// ── AGORA ─────────────────────────────────────────────────────────────────────────────────────────────────────

export type TomKpi = "neutral" | "blue" | "amber" | "red";
export type KpiAgora = { id: keyof Omit<AgoraKpis, "semEtapaAtual">; label: string; valor: number; ajuda: string; tom: TomKpi };

/** Os 5 indicadores do AGORA. Cor semântica só quando há o que olhar (zero é neutro); `semEtapaAtual` NÃO é KPI principal. */
export function kpisDoAgora(k: AgoraKpis): KpiAgora[] {
  return [
    { id: "emExecucao", label: "Em execução", valor: k.emExecucao, ajuda: "tarefas neste estado", tom: "blue" },
    { id: "atrasadas", label: "Atrasadas", valor: k.atrasadas, ajuda: "prazo vencido", tom: k.atrasadas > 0 ? "red" : "neutral" },
    { id: "vencemHoje", label: "Vencem hoje", valor: k.vencemHoje, ajuda: "prazo no dia de hoje", tom: k.vencemHoje > 0 ? "amber" : "neutral" },
    { id: "semResponsavel", label: "Sem responsável", valor: k.semResponsavel, ajuda: "ninguém atribuído", tom: k.semResponsavel > 0 ? "amber" : "neutral" },
    { id: "semPrazo", label: "Sem prazo", valor: k.semPrazo, ajuda: "sem data de prazo", tom: "neutral" },
  ];
}

/** Aviso discreto (pendência conhecida do workflow final): só quando há casos. */
export function avisoSemEtapaAtual(n: number): string | null {
  if (n <= 0) return null;
  return `${n === 1 ? "1 tarefa aberta" : `${n} tarefas abertas`} com o workflow concluído e sem etapa atual.`;
}

export type LinhaAgora = {
  demandaId: string;
  identificador: string;
  titulo: string;
  cliente: string | null;
  projeto: string | null;
  etapa: { id: string; nome: string; departamentos: string } | null;
  responsaveis: Array<{ id: string; nome: string }>;
  /** "Tempo no estado atual" (formatado) ou "—". É o tempo da TAREFA no estado, não horas de alguém. */
  tempoNoEstado: string;
  prazo: string;
  atrasada: boolean;
};

export function linhaDoAgora(demanda: AgoraDemanda, contexto: { fuso: string; recebidoEmMs: number; agoraMs: number }): LinhaAgora {
  const { principal, secundario } = clienteEProjeto(demanda);
  return {
    demandaId: demanda.demandaId,
    identificador: demanda.identificador,
    titulo: demanda.titulo,
    cliente: principal,
    projeto: secundario,
    etapa: demanda.etapaAtual ? { id: demanda.etapaAtual.id, nome: demanda.etapaAtual.nome, departamentos: rotuloDepartamentos(demanda.etapaAtual.departamentos) } : null,
    responsaveis: demanda.responsaveis.map((responsavel) => ({ id: responsavel.usuarioId, nome: responsavel.nome })),
    tempoNoEstado: formatarDuracao(idadeAtualSegundos(demanda.idadeEstadoSegundos, contexto.recebidoEmMs, contexto.agoraMs)),
    prazo: formatarPrazo(demanda.prazo, contexto.fuso),
    atrasada: demanda.atrasada,
  };
}

/** Todo texto visível de uma linha do AGORA (para auditar a semântica: nada de "trabalhou"/"executando"). */
export function textosDaLinha(linha: LinhaAgora): string[] {
  return [
    linha.identificador,
    linha.titulo,
    linha.cliente ?? "",
    linha.projeto ?? "",
    linha.etapa?.nome ?? "Sem etapa atual",
    linha.etapa?.departamentos ?? "",
    ...linha.responsaveis.map((responsavel) => responsavel.nome),
    `${TEXTO_TEMPO_NO_ESTADO}: ${linha.tempoNoEstado}`,
    linha.prazo,
  ];
}

// ── GARGALOS ──────────────────────────────────────────────────────────────────────────────────────────────────

export type CelulaTempo = { valor: string; amostra: string; total: string; maior: string };

function celula(media: number | null, n: number, total: number, maior: number | null): CelulaTempo {
  const { valor, amostra } = mediaComAmostra(media, n);
  return { valor, amostra, total: formatarDuracao(total), maior: formatarDuracao(maior) };
}

export type LinhaGargalo = {
  chave: string;
  etapa: string;
  tipo: string;
  departamentos: string;
  n: number;
  wip: number;
  execucao: CelulaTempo;
  pausado: CelulaTempo;
  bloqueado: CelulaTempo;
  aguardandoCliente: CelulaTempo;
};

/** Junta o tempo por definição de etapa (período) com o WIP ATUAL da mesma definição (por `chave`). Sem WIP na fila = 0. */
export function linhasDeGargalo(etapas: readonly GargaloEtapa[], fila: readonly FilaEtapa[]): LinhaGargalo[] {
  const wipPorChave = new Map(fila.map((f) => [f.definicaoEtapa.chave, f.wip]));
  return etapas.map((e) => ({
    chave: e.definicaoEtapa.chave,
    etapa: e.definicaoEtapa.nome,
    tipo: e.definicaoEtapa.tipo,
    departamentos: rotuloDepartamentos(e.definicaoEtapa.departamentos),
    n: e.n,
    wip: wipPorChave.get(e.definicaoEtapa.chave) ?? 0,
    execucao: celula(e.tempoExecucaoMedioSegundos, e.nExecucao, e.tempoExecucaoTotalSegundos, e.tempoExecucaoMaiorSegundos),
    pausado: celula(e.tempoPausadoMedioSegundos, e.nPausado, e.tempoPausadoTotalSegundos, e.tempoPausadoMaiorSegundos),
    bloqueado: celula(e.tempoBloqueadoMedioSegundos, e.nBloqueado, e.tempoBloqueadoTotalSegundos, e.tempoBloqueadoMaiorSegundos),
    aguardandoCliente: celula(e.tempoAguardandoClienteMedioSegundos, e.nAguardandoCliente, e.tempoAguardandoClienteTotalSegundos, e.tempoAguardandoClienteMaiorSegundos),
  }));
}

export type LinhaFila = {
  chave: string;
  etapa: string;
  departamentos: string;
  wip: number;
  maisAntigaHa: string;
  /** A sequência começa no intervalo inicial da migração: a idade real pode ser maior (tooltip `TEXTO_TRUNCADA`). */
  truncada: boolean;
  idadeEstadoMaisAntigo: string;
  estados: Array<{ id: "emExecucao" | "pausadas" | "bloqueadas" | "aguardandoCliente" | "planejadas"; rotulo: string; n: number }>;
};

export function linhasDaFila(fila: readonly FilaEtapa[]): LinhaFila[] {
  return fila.map((f) => ({
    chave: f.definicaoEtapa.chave,
    etapa: f.definicaoEtapa.nome,
    departamentos: rotuloDepartamentos(f.definicaoEtapa.departamentos),
    wip: f.wip,
    maisAntigaHa: formatarDuracao(f.maisAntigaSegundos),
    truncada: f.maisAntigaTruncadaPelaMedicao,
    idadeEstadoMaisAntigo: formatarDuracao(f.idadeEstadoMaisAntigoSegundos),
    estados: (
      [
        { id: "emExecucao", rotulo: "em execução", n: f.emExecucao },
        { id: "pausadas", rotulo: f.pausadas === 1 ? "pausada" : "pausadas", n: f.pausadas },
        { id: "bloqueadas", rotulo: f.bloqueadas === 1 ? "bloqueada" : "bloqueadas", n: f.bloqueadas },
        { id: "aguardandoCliente", rotulo: "aguardando cliente", n: f.aguardandoCliente },
        { id: "planejadas", rotulo: f.planejadas === 1 ? "planejada" : "planejadas", n: f.planejadas },
      ] as const
    ).filter((estado) => estado.n > 0),
  }));
}

export function avisoFilaSemEtapa(f: { workflowConcluido: number; semWorkflow: number }): string | null {
  const partes: string[] = [];
  if (f.workflowConcluido > 0) partes.push(`${f.workflowConcluido} com o workflow concluído e sem etapa atual`);
  if (f.semWorkflow > 0) partes.push(`${f.semWorkflow} sem workflow`);
  return partes.length === 0 ? null : `Também abertas, fora das etapas: ${partes.join(" · ")}.`;
}

/** Nenhuma amostra no período para os filtros atuais (nem por etapa, nem sem etapa). */
export function gargalosVazio(g: Pick<TrafegoOperacionalGargalos, "etapas" | "semEtapa">): boolean {
  return g.etapas.length === 0 && g.semEtapa.n === 0;
}

// ── Estado remoto (carregamento sem piscar) ───────────────────────────────────────────────────────────────────

export class TrafegoOperacionalErro extends Error {
  readonly status: number;
  constructor(mensagem: string, status: number) {
    super(mensagem);
    this.name = "TrafegoOperacionalErro";
    this.status = status;
  }
}

export function mensagemDeErro(erro: unknown): string {
  const status = erro instanceof TrafegoOperacionalErro ? erro.status : 0;
  if (status === 403) return "Você não tem acesso às métricas operacionais do Tráfego.";
  if (status === 422) return "Os filtros escolhidos não são válidos para esta consulta.";
  return "Não foi possível carregar as métricas operacionais.";
}

export type EstadoRemoto<T> = {
  dados: T | null;
  recebidoEmMs: number | null;
  /** Só a PRIMEIRA carga (ainda sem dados) mostra skeleton; as seguintes mantêm o conteúdo. */
  carregando: boolean;
  /** Há uma requisição em voo (indicador discreto — nunca troca o conteúdo). */
  atualizando: boolean;
  erro: string | null;
};

export type EventoRemoto<T> = { tipo: "buscar" } | { tipo: "sucesso"; dados: T; emMs: number } | { tipo: "falha"; mensagem: string };

export function estadoRemotoInicial<T>(): EstadoRemoto<T> {
  return { dados: null, recebidoEmMs: null, carregando: true, atualizando: false, erro: null };
}

export function reduzirRemoto<T>(estado: EstadoRemoto<T>, evento: EventoRemoto<T>): EstadoRemoto<T> {
  switch (evento.tipo) {
    case "buscar":
      // Com dados na tela (poll, refresh manual, troca de filtro) o conteúdo é MANTIDO — só `atualizando` liga. Sem dados, é o skeleton.
      return { ...estado, carregando: estado.dados === null, atualizando: true };
    case "sucesso":
      return { dados: evento.dados, recebidoEmMs: evento.emMs, carregando: false, atualizando: false, erro: null };
    case "falha":
      return { ...estado, carregando: false, atualizando: false, erro: evento.mensagem };
  }
}

// ── Polling do AGORA ──────────────────────────────────────────────────────────────────────────────────────────

export const INTERVALO_POLLING_AGORA_MS = 30_000;

export type PollerAgora = { iniciar: () => void; parar: () => void; atualizar: () => void; aoMudarVisibilidade: () => void };

/**
 * Polling silencioso: uma busca imediata ao iniciar e depois a cada `intervaloMs`, mas só com a aba visível e nunca sobrepondo requisições (se uma está em voo, o tick é descartado).
 * Voltar à aba dispara uma atualização. Sem websocket. Os temporizadores e a visibilidade são injetáveis (testável sem DOM).
 */
export function criarPoller({
  buscar,
  intervaloMs = INTERVALO_POLLING_AGORA_MS,
  visivel = () => true,
  setIntervalo = (acao, ms) => setInterval(acao, ms),
  limparIntervalo = (id) => clearInterval(id as ReturnType<typeof setInterval>),
}: {
  buscar: () => Promise<void>;
  intervaloMs?: number;
  visivel?: () => boolean;
  setIntervalo?: (acao: () => void, ms: number) => unknown;
  limparIntervalo?: (id: unknown) => void;
}): PollerAgora {
  let timer: unknown = null;
  let emVoo = false;

  const rodar = () => {
    if (emVoo) return;
    emVoo = true;
    buscar()
      .catch(() => {})
      .finally(() => {
        emVoo = false;
      });
  };

  return {
    iniciar() {
      if (timer !== null) return;
      rodar();
      timer = setIntervalo(() => {
        if (visivel()) rodar();
      }, intervaloMs);
    },
    parar() {
      if (timer !== null) limparIntervalo(timer);
      timer = null;
    },
    atualizar: rodar,
    aoMudarVisibilidade() {
      if (visivel()) rodar();
    },
  };
}

export type { TrafegoOperacionalAgora };
