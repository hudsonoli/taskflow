import { clientesProjetoDisponiveis, responsaveisProjetoDisponiveis } from "@/lib/projetos-mock";
import type { Demanda } from "@/types/demanda";
import type { Projeto } from "@/types/projeto";

const STATUS_ABERTOS = new Set(["rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"]);

export function isDemandaAberta(demanda: Demanda): boolean {
  return STATUS_ABERTOS.has(demanda.status);
}

export interface FatiaPizza {
  id: string;
  label: string;
  value: number;
}

export function demandasAbertasPorProjeto(clienteId: string, demandas: Demanda[], projetos: Projeto[]): FatiaPizza[] {
  const projetosDoCliente = projetos.filter((projeto) => projeto.clienteId === clienteId);
  return projetosDoCliente
    .map((projeto) => ({
      id: projeto.id,
      label: projeto.nome,
      value: demandas.filter((demanda) => demanda.projetoId === projeto.id && isDemandaAberta(demanda)).length,
    }))
    .filter((fatia) => fatia.value > 0);
}

export interface SerieBarraEmpilhada {
  categoria: string;
  categoriaId: string;
  segmentos: { seriesId: string; label: string; value: number }[];
}

export function volumePorProjetoEColaborador(demandas: Demanda[], projetos: Projeto[]): SerieBarraEmpilhada[] {
  return projetos.map((projeto) => {
    const demandasDoProjeto = demandas.filter((demanda) => demanda.projetoId === projeto.id);
    const segmentos = responsaveisProjetoDisponiveis
      .map((usuario) => ({
        seriesId: usuario.id,
        label: usuario.nome,
        value: demandasDoProjeto.filter((demanda) => demanda.usuarioResponsavelIds.includes(usuario.id)).length,
      }))
      .filter((segmento) => segmento.value > 0);

    return { categoria: projeto.nome, categoriaId: projeto.id, segmentos };
  });
}

export interface PontoLinha {
  semanaLabel: string;
  inicioSemana: string;
  value: number;
}

function startOfWeek(date: Date): Date {
  const result = new Date(date);
  const day = result.getDay();
  const diff = (day + 6) % 7; // semana começa na segunda
  result.setDate(result.getDate() - diff);
  result.setHours(0, 0, 0, 0);
  return result;
}

export function volumeSemanal(referenceDate: Date, demandas: Demanda[], semanas = 12): PontoLinha[] {
  const semanaAtualInicio = startOfWeek(referenceDate);
  const buckets: PontoLinha[] = [];

  for (let index = semanas - 1; index >= 0; index -= 1) {
    const inicio = new Date(semanaAtualInicio);
    inicio.setDate(inicio.getDate() - index * 7);
    const fim = new Date(inicio);
    fim.setDate(fim.getDate() + 7);

    const count = demandas.filter((demanda) => {
      const criada = new Date(demanda.dataCriacao);
      return criada >= inicio && criada < fim;
    }).length;

    buckets.push({
      semanaLabel: new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit" }).format(inicio),
      inicioSemana: inicio.toISOString(),
      value: count,
    });
  }

  return buckets;
}

export function resolveClientesComProjeto(projetos: Projeto[]) {
  return clientesProjetoDisponiveis.filter((cliente) => projetos.some((projeto) => projeto.clienteId === cliente.id));
}

function diffEmDias(inicioIso: string, fimIso: string): number {
  const ms = new Date(fimIso).getTime() - new Date(inicioIso).getTime();
  return ms / (1000 * 60 * 60 * 24);
}

function media(valores: number[]): number {
  if (valores.length === 0) return 0;
  return valores.reduce((sum, value) => sum + value, 0) / valores.length;
}

function contarHistoricoPorTipo(demandas: Demanda[]) {
  let ajustesInternos = 0;
  let ajustesCliente = 0;
  let refacoes = 0;
  demandas.forEach((demanda) => {
    demanda.historico.forEach((evento) => {
      if (evento.tipo === "ajuste_interno") ajustesInternos += 1;
      if (evento.tipo === "ajuste_cliente") ajustesCliente += 1;
      if (evento.tipo === "refacao") refacoes += 1;
    });
  });
  return { ajustesInternos, ajustesCliente, refacoes };
}

export interface AnaliseProjeto {
  projetoId: string;
  projetoNome: string;
  totalDemandas: number;
  prioridade: { baixa: number; media: number; alta: number };
  tempoMedioAberturaAteInicioDias: number;
  tempoMedioRetornoClienteDias: number | null;
  ajustesInternos: number;
  ajustesCliente: number;
  refacoes: number;
  colaboradores: { id: string; nome: string; demandas: number }[];
}

export function analisarProjeto(projetoId: string, demandasTodas: Demanda[], projetos: Projeto[]): AnaliseProjeto {
  const projeto = projetos.find((item) => item.id === projetoId);
  const demandas = demandasTodas.filter((demanda) => demanda.projetoId === projetoId);

  const tempoAbertura = demandas.map((demanda) => diffEmDias(demanda.dataCriacao, demanda.dataInicio));
  const temposRetorno = demandas
    .filter((demanda) => demanda.enviadoClienteEm && demanda.retornoRecebidoEm)
    .map((demanda) => diffEmDias(demanda.enviadoClienteEm as string, demanda.retornoRecebidoEm as string));

  const { ajustesInternos, ajustesCliente, refacoes } = contarHistoricoPorTipo(demandas);

  const colaboradores = responsaveisProjetoDisponiveis
    .map((usuario) => ({
      id: usuario.id,
      nome: usuario.nome,
      demandas: demandas.filter((demanda) => demanda.usuarioResponsavelIds.includes(usuario.id)).length,
    }))
    .filter((colaborador) => colaborador.demandas > 0);

  return {
    projetoId,
    projetoNome: projeto?.nome ?? projetoId,
    totalDemandas: demandas.length,
    prioridade: {
      baixa: demandas.filter((demanda) => demanda.prioridade === "baixa").length,
      media: demandas.filter((demanda) => demanda.prioridade === "media").length,
      alta: demandas.filter((demanda) => demanda.prioridade === "alta").length,
    },
    tempoMedioAberturaAteInicioDias: media(tempoAbertura),
    tempoMedioRetornoClienteDias: temposRetorno.length > 0 ? media(temposRetorno) : null,
    ajustesInternos,
    ajustesCliente,
    refacoes,
    colaboradores,
  };
}

export interface AnalisePeca {
  demandaId: string;
  nome: string;
  codigoInterno: string;
  redator: string;
  tempoEmPautaDias: number | null;
  emAndamento: boolean;
  ajustesInternos: number;
  ajustesCliente: number;
  refacoes: number;
}

export function analisarPecasPorProjeto(projetoId: string, demandasTodas: Demanda[]): AnalisePeca[] {
  const demandas = demandasTodas.filter((demanda) => demanda.projetoId === projetoId);

  return demandas.map((demanda) => {
    const redatorId = demanda.usuarioResponsavelIds[0];
    const redator = responsaveisProjetoDisponiveis.find((usuario) => usuario.id === redatorId)?.nome ?? "Sem responsável";
    const emAndamento = demanda.status !== "concluida" && demanda.status !== "cancelada";
    const { ajustesInternos, ajustesCliente, refacoes } = contarHistoricoPorTipo([demanda]);

    return {
      demandaId: demanda.id,
      nome: demanda.nome,
      codigoInterno: demanda.codigoInterno,
      redator,
      tempoEmPautaDias: emAndamento ? null : diffEmDias(demanda.dataCriacao, demanda.updatedAt),
      emAndamento,
      ajustesInternos,
      ajustesCliente,
      refacoes,
    };
  });
}

export interface PerformanceColaborador {
  colaboradorId: string;
  colaboradorNome: string;
  demandasEntregues: number;
  entreguesNoPrazo: number;
  entreguesEmAtraso: number;
  participacaoPorEtapa: FatiaPizza[];
}

export function analisarPerformanceColaborador(colaboradorId: string, demandasTodas: Demanda[]): PerformanceColaborador {
  const colaborador = responsaveisProjetoDisponiveis.find((usuario) => usuario.id === colaboradorId);
  const demandasDoColaborador = demandasTodas.filter((demanda) => demanda.usuarioResponsavelIds.includes(colaboradorId));
  const entregues = demandasDoColaborador.filter((demanda) => demanda.status === "concluida");

  const entreguesNoPrazo = entregues.filter((demanda) => new Date(demanda.updatedAt) <= new Date(demanda.dataFimPrevista)).length;
  const entreguesEmAtraso = entregues.length - entreguesNoPrazo;

  const etapaContagem = new Map<string, number>();
  demandasDoColaborador.forEach((demanda) => {
    demanda.workflowEtapas
      .filter((etapa) => etapa.usuarioResponsavelIds.includes(colaboradorId))
      .forEach((etapa) => {
        etapaContagem.set(etapa.nome, (etapaContagem.get(etapa.nome) ?? 0) + 1);
      });
  });

  return {
    colaboradorId,
    colaboradorNome: colaborador?.nome ?? colaboradorId,
    demandasEntregues: entregues.length,
    entreguesNoPrazo,
    entreguesEmAtraso,
    participacaoPorEtapa: Array.from(etapaContagem.entries()).map(([nome, value]) => ({ id: nome, label: nome, value })),
  };
}
