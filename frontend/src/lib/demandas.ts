/**
 * Rótulos e helpers de Demanda.
 *
 * Substitui `demandas-mock.ts`, removido na Fase 2E.1: Demanda passou a vir da API, e o
 * arquivo antigo misturava dados falsos com funções de apresentação legítimas. Aqui ficou só
 * o que é apresentação — não há dado de demanda neste módulo.
 *
 * Projeto/Cliente/Departamento/Usuário resolvem todos pelo diretório real
 * (`lib/referencias.ts`) desde a Fase 2E.5 — nada aqui importa mais `legacy-referencias-mock`.
 */

import { AGENCIA_PADRAO_ID, EMPRESA_PADRAO_ID, generateCodigoInterno, generateId } from "@/lib/ids";
import { parseDataLocal } from "@/lib/data-local";
import type {
  Demanda,
  DemandaPrioridade,
  DemandaStatus,
  DemandaWorkflowEtapaStatus,
} from "@/types/demanda";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import { correspondeUsuario, resolverUsuarioPorReferencia } from "@/lib/referencias";

export { AGENCIA_PADRAO_ID, EMPRESA_PADRAO_ID, generateCodigoInterno, generateId };

export const statusDemandaLabels: Record<DemandaStatus, string> = {
  rascunho: "Rascunho",
  planejada: "Planejada",
  em_execucao: "Em execução",
  pausada: "Pausada",
  bloqueada: "Bloqueada",
  aguardando_cliente: "Aguardando cliente",
  concluida: "Concluída",
  cancelada: "Cancelada",
  arquivada: "Arquivada",
};

// Status oferecidos no formulário e no Kanban. `arquivada` fica de fora de propósito: entra
// pela rota de arquivamento, com motivo obrigatório, e um PATCH com ela devolve 422.
export const statusDemandaEditaveis = [
  "rascunho",
  "planejada",
  "em_execucao",
  "pausada",
  "bloqueada",
  "aguardando_cliente",
  "concluida",
  "cancelada",
] as const;

export const prioridadeDemandaLabels: Record<DemandaPrioridade, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

// Cor associada a cada status — centralizado para não ser redefinido em cada tela/lista.
export const statusDemandaTone: Record<DemandaStatus, "neutral" | "blue" | "green" | "amber" | "red"> = {
  rascunho: "neutral",
  planejada: "blue",
  em_execucao: "green",
  pausada: "amber",
  bloqueada: "red",
  aguardando_cliente: "amber",
  concluida: "green",
  cancelada: "neutral",
  arquivada: "neutral",
};

export const workflowEtapaStatusLabels: Record<DemandaWorkflowEtapaStatus, string> = {
  pendente: "Pendente",
  em_execucao: "Em execução",
  pausada: "Pausada",
  concluida: "Concluída",
};

// Compatibilidade entre a lista mock legada de responsáveis (ids "user-N") e o cadastro real de
// usuários (ids "usuario-N") — normaliza até os dois cadastros serem unificados.
export function normalizarUsuarioId(id: string): string {
  return id.replace(/^user-/, "usuario-");
}

/**
 * `usuarioId` pode ser UUID real ou codigoInterno — o registro guardado em
 * `usuarioResponsavelIds` é resolvido no diretório e comparado nos dois formatos (ver
 * lib/referencias.ts). Precisa do diretório porque `usuarioAtual.id` (sessão real) é
 * sempre UUID, mas relações antigas podem ter sido gravadas como codigoInterno.
 */
export function demandaTemResponsavel(demanda: Demanda, usuarioId: string, diretorio: UsuarioDiretorioItem[]): boolean {
  return demanda.usuarioResponsavelIds.some((id) => {
    const normalizado = normalizarUsuarioId(id);
    if (normalizado === usuarioId) return true;
    const resolvido = resolverUsuarioPorReferencia(normalizado, diretorio);
    return resolvido ? correspondeUsuario(usuarioId, resolvido) : false;
  });
}

export function resolveResponsaveisDemandaNomes(ids: string[], usuarios: UsuarioDiretorioItem[]): string {
  if (ids.length === 0) return "-";
  return ids
    .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios)?.nome ?? id)
    .join(", ");
}

/**
 * `value` pode ser data pura (`dataFimPrevista`/`dataInicio`, sem "T") ou timestamp real
 * (`prazoEtapaAtual` etc., com "T"). Data pura passa por `parseDataLocal` — nunca por
 * `new Date(string)` direto, que interpretaria como UTC e pode deslocar pro dia anterior no
 * fuso local (ver lib/data-local.ts). Timestamp real já carrega instante e fuso, então segue
 * com `new Date(string)` normal.
 */
export function formatPrazo(value: string | null | undefined): string {
  if (!value) return "Sem prazo";
  const hasTime = value.includes("T");
  const date = hasTime ? new Date(value) : parseDataLocal(value);
  if (!date || Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    ...(hasTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

/**
 * Ordena por `prazoEtapaAtual` (campo MANUAL, não derivado das etapas — ver types/demanda.ts).
 * Tarefas sem prazo ficam por último. Usado pela Pauta para agrupar por dia e ordenar dentro
 * do dia na mesma ordem vista pela equipe.
 */
export function compararPorAgenda(a: Demanda, b: Demanda): number {
  const prazoA = a.prazoEtapaAtual ? new Date(a.prazoEtapaAtual).getTime() : Number.NaN;
  const prazoB = b.prazoEtapaAtual ? new Date(b.prazoEtapaAtual).getTime() : Number.NaN;
  const validoA = !Number.isNaN(prazoA);
  const validoB = !Number.isNaN(prazoB);

  if (!validoA && !validoB) return 0;
  if (!validoA) return 1;
  if (!validoB) return -1;
  return prazoA - prazoB;
}
