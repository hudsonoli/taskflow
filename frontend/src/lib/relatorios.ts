import type { ClienteDiretorioItem, ProjetoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import { fimDaDataLocal } from "@/lib/data-local";
import type { Demanda } from "@/types/demanda";

// Todos os helpers deste módulo recebem o diretório real como argumento (Cliente/Usuário/
// Projeto) — nenhum importa mock nem hook React, mesmo padrão de `resolverProjetoNome` em
// lib/referencias.ts. `clientesProjetoDisponiveis`/`responsaveisProjetoDisponiveis` saíram
// na Fase 2E.5D (o segundo já não tinha mais consumidor aqui desde a 2E.5C).


const STATUS_ABERTOS = new Set(["rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"]);

export function isDemandaAberta(demanda: Demanda): boolean {
  return STATUS_ABERTOS.has(demanda.status);
}

export interface FatiaPizza {
  id: string;
  label: string;
  value: number;
}

export function demandasAbertasPorProjeto(clienteId: string, demandas: Demanda[], projetos: ProjetoDiretorioItem[]): FatiaPizza[] {
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

export function volumePorProjetoEColaborador(
  demandas: Demanda[],
  projetos: ProjetoDiretorioItem[],
  usuarios: UsuarioDiretorioItem[],
): SerieBarraEmpilhada[] {
  return projetos.map((projeto) => {
    const demandasDoProjeto = demandas.filter((demanda) => demanda.projetoId === projeto.id);
    const segmentos = usuarios
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
      const criada = new Date(demanda.createdAt);
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

/**
 * Consulta histórica, não seleção de vínculo novo — não filtra `status`. O diretório de
 * Cliente já inclui arquivado por padrão (`ClienteRepository.list_diretorio`), então um
 * cliente descontinuado com Demandas antigas continua aparecendo aqui em vez de sumir do
 * relatório.
 */
export function resolveClientesComProjeto(projetos: ProjetoDiretorioItem[], clientes: ClienteDiretorioItem[]) {
  return clientes.filter((cliente) => projetos.some((projeto) => projeto.clienteId === cliente.id));
}

export interface PerformanceColaborador {
  colaboradorId: string;
  colaboradorNome: string;
  demandasEntregues: number;
  entreguesNoPrazo: number;
  entreguesEmAtraso: number;
  participacaoPorEtapa: FatiaPizza[];
}

/**
 * `usuarioResponsavelIds` é `list[UUID]` no schema do backend (ver `schemas/demanda.py`) —
 * Demanda nasceu com seed vazio na Fase 2E.1, então não existe (e não pode existir) demanda
 * carregando o formato antigo `user-N`. Comparação direta por UUID, sem `normalizarUsuarioId`.
 */
export function analisarPerformanceColaborador(
  colaboradorId: string,
  demandasTodas: Demanda[],
  usuarios: UsuarioDiretorioItem[],
): PerformanceColaborador {
  const colaborador = usuarios.find((usuario) => usuario.id === colaboradorId);
  const demandasDoColaborador = demandasTodas.filter((demanda) => demanda.usuarioResponsavelIds.includes(colaboradorId));
  const entregues = demandasDoColaborador.filter((demanda) => demanda.status === "concluida");

  // `dataFimPrevista` é data pura (sem hora) — o prazo dela só se esgota ao FIM do dia
  // previsto, não à meia-noite que abre esse dia. Comparar `updatedAt` (timestamp real)
  // contra `parseDataLocal` classificaria como atrasada uma entrega feita de manhã no
  // próprio dia previsto — por isso a comparação é contra `fimDaDataLocal` (23:59:59.999
  // local do dia previsto), não contra o início dele. Sem `dataFimPrevista`, não há prazo
  // para comparar: a demanda cai no bucket de atraso, mesmo comportamento de antes desta
  // correção (a comparação anterior com `new Date("")` também nunca contava como "no prazo").
  const entreguesNoPrazo = entregues.filter((demanda) => {
    const fimPrazo = fimDaDataLocal(demanda.dataFimPrevista);
    return fimPrazo !== null && new Date(demanda.updatedAt) <= fimPrazo;
  }).length;
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
