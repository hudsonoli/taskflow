import { normalizarUsuarioId } from "@/lib/demandas";
import type { DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import type { DemandaDiretorio } from "@/types/demanda";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";
import type { TrafegoCargaItem, TrafegoFiltersState, TrafegoResumo } from "@/types/trafego";

// `EMPRESA_TRAFEGO_PADRAO_ID` saiu: era a string mock "empresa-principal", enviada como
// `empresaId` para a API real. Agora a empresa vem do token, no servidor.
//
// `trafegoUsuariosDisponiveis`/`trafegoDepartamentosDisponiveis` também saíram: eram as
// listas mock (`user-1`…`user-5`) que `resolveTrafegoUsuarioNome`/`resolveTrafegoDepartamentoNome`
// resolviam por baixo. Desde que `sessoes_trabalho.usuario_id`/`departamento_id` passaram a
// carregar UUID real (ver docstring de `app/models/sessao_trabalho.py` no backend), essas
// funções recebem o diretório real como argumento — mesmo padrão já usado por
// `resolveTrafegoDemandaNome` abaixo. Uma constante de módulo não tem como refletir dado que
// vem da API.

export function resolveTrafegoUsuarioNome(usuarioId: string | null, diretorio: UsuarioDiretorioItem[]): string {
  if (!usuarioId) return "Sem usuário";
  return diretorio.find((usuario) => usuario.id === usuarioId)?.nome ?? usuarioId;
}

export function resolveTrafegoDepartamentoNome(
  departamentoId: string | null,
  diretorio: DepartamentoDiretorioItem[],
): string {
  if (!departamentoId) return "Sem departamento";
  return diretorio.find((departamento) => departamento.id === departamentoId)?.nome ?? departamentoId;
}

/**
 * Nome da demanda para a tabela de sessões, no formato operacional `#2063 — Nome`.
 *
 * Recebe o diretório em vez de consultá-lo: quem o carregou já respeitou o escopo do usuário.
 * Demanda ausente do diretório cai no id — não inventa nome nem esconde a sessão.
 */
export function resolveTrafegoDemandaNome(demandaId: string, diretorio: DemandaDiretorio[]): string {
  const demanda = diretorio.find((item) => item.id === demandaId);
  return demanda ? `#${demanda.numeroOperacional} — ${demanda.nome}` : demandaId;
}

export function formatTempoOperacional(seconds: number): string {
  const safeSeconds = Math.max(0, Math.round(seconds));
  const totalMinutes = Math.floor(safeSeconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) return `${minutes}min`;
  return `${hours}h ${String(minutes).padStart(2, "0")}min`;
}

export function classifyCarga(seconds: number): { label: string; color: string } {
  if (seconds === 0) return { label: "Livre", color: "bg-zinc-300 dark:bg-zinc-600" };
  if (seconds < 1800) return { label: "Leve", color: "bg-sky-400" };
  if (seconds < 4200) return { label: "Moderada", color: "bg-indigo-500" };
  return { label: "Alta", color: "bg-amber-500" };
}

export function elapsedSeconds(sessao: SessaoTrabalho, now: Date): number {
  if (sessao.duracaoSegundos !== null) return sessao.duracaoSegundos;
  const inicio = new Date(sessao.inicioEm).getTime();
  return Math.max(0, Math.floor((now.getTime() - inicio) / 1000));
}

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

export function filterSessoes(
  sessoes: SessaoTrabalho[],
  filters: TrafegoFiltersState,
  diretorioDemandas: DemandaDiretorio[] = [],
): SessaoTrabalho[] {
  return sessoes.filter((sessao) => {
    const usuarioMatches = filters.usuarioIds.length === 0 || (sessao.usuarioId !== null && filters.usuarioIds.includes(sessao.usuarioId));
    const departamentoMatches =
      filters.departamentoIds.length === 0 || (sessao.departamentoId !== null && filters.departamentoIds.includes(sessao.departamentoId));
    const demandaNome = resolveTrafegoDemandaNome(sessao.demandaId, diretorioDemandas);
    const demandaMatches = filters.demandaQuery.trim()
      ? normalize(`${sessao.demandaId} ${demandaNome}`).includes(normalize(filters.demandaQuery))
      : true;

    return usuarioMatches && departamentoMatches && demandaMatches;
  });
}

export function buildCarga(sessoesAtivas: SessaoTrabalho[], tipoAgrupamento: "usuario" | "departamento", now: Date): TrafegoCargaItem[] {
  const groups = new Map<string, SessaoTrabalho[]>();

  sessoesAtivas.forEach((sessao) => {
    const agrupamentoId = tipoAgrupamento === "usuario" ? sessao.usuarioId : sessao.departamentoId;
    if (!agrupamentoId) return;
    groups.set(agrupamentoId, [...(groups.get(agrupamentoId) ?? []), sessao]);
  });

  return Array.from(groups.entries())
    .map(([agrupamentoId, groupSessions]) => {
      const demandIds = new Set(groupSessions.map((sessao) => sessao.demandaId));
      const oldestStart = groupSessions.reduce((oldest, sessao) =>
        new Date(sessao.inicioEm).getTime() < new Date(oldest.inicioEm).getTime() ? sessao : oldest,
      );

      return {
        agrupamentoId,
        tipoAgrupamento,
        sessoesAtivas: groupSessions.length,
        demandasDistintas: demandIds.size,
        tempoAtivoTotalSegundos: groupSessions.reduce((sum, sessao) => sum + elapsedSeconds(sessao, now), 0),
        inicioMaisAntigo: oldestStart.inicioEm,
      };
    })
    .sort((first, second) => second.tempoAtivoTotalSegundos - first.tempoAtivoTotalSegundos);
}

/**
 * Carga agrupada por equipe — não existe `equipeId` na sessão, então o vínculo é inferido a
 * partir de `Equipe.membroIds` (normalizando o id do usuário, mesma ponte usada no restante
 * do app entre as famílias históricas de id `user-N` / `usuario-N`).
 */
export function buildCargaEquipe(
  sessoesAtivas: SessaoTrabalho[],
  equipes: { id: string; membroIds: string[] }[],
  now: Date,
): TrafegoCargaItem[] {
  const groups = new Map<string, SessaoTrabalho[]>();

  sessoesAtivas.forEach((sessao) => {
    if (!sessao.usuarioId) return;
    const usuarioIdNormalizado = normalizarUsuarioId(sessao.usuarioId);
    const equipe = equipes.find((item) => item.membroIds.includes(usuarioIdNormalizado));
    if (!equipe) return;
    groups.set(equipe.id, [...(groups.get(equipe.id) ?? []), sessao]);
  });

  return Array.from(groups.entries())
    .map(([agrupamentoId, groupSessions]) => {
      const demandIds = new Set(groupSessions.map((sessao) => sessao.demandaId));
      const oldestStart = groupSessions.reduce((oldest, sessao) =>
        new Date(sessao.inicioEm).getTime() < new Date(oldest.inicioEm).getTime() ? sessao : oldest,
      );

      return {
        agrupamentoId,
        tipoAgrupamento: "equipe" as const,
        sessoesAtivas: groupSessions.length,
        demandasDistintas: demandIds.size,
        tempoAtivoTotalSegundos: groupSessions.reduce((sum, sessao) => sum + elapsedSeconds(sessao, now), 0),
        inicioMaisAntigo: oldestStart.inicioEm,
      };
    })
    .sort((first, second) => second.tempoAtivoTotalSegundos - first.tempoAtivoTotalSegundos);
}

export function buildResumo(sessoesAtivas: SessaoTrabalho[], sessoesEncerradas: SessaoTrabalho[], now: Date): TrafegoResumo {
  const todasSessoes = [...sessoesAtivas, ...sessoesEncerradas];
  const usuarioIds = new Set(todasSessoes.map((sessao) => sessao.usuarioId).filter((id): id is string => id !== null));
  const departamentoIds = new Set(todasSessoes.map((sessao) => sessao.departamentoId).filter((id): id is string => id !== null));
  const demandaIds = new Set(todasSessoes.map((sessao) => sessao.demandaId));
  const duracoes = todasSessoes.map((sessao) => elapsedSeconds(sessao, now));
  const tempoTotal = duracoes.reduce((sum, value) => sum + value, 0);

  return {
    sessoesAtivas: sessoesAtivas.length,
    sessoesEncerradas: sessoesEncerradas.length,
    demandasDistintas: demandaIds.size,
    usuariosDistintos: usuarioIds.size,
    departamentosDistintos: departamentoIds.size,
    tempoOperacionalEstimadoSegundos: tempoTotal,
    tempoMedioSessaoSegundos: duracoes.length > 0 ? Math.round(tempoTotal / duracoes.length) : 0,
    maiorSessaoSegundos: duracoes.length > 0 ? Math.max(...duracoes) : 0,
  };
}

export const periodoParaDataInicio: Record<TrafegoFiltersState["periodo"], () => string> = {
  hoje: () => new Date(new Date().setHours(0, 0, 0, 0)).toISOString(),
  "24h": () => new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  "7d": () => new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  "30d": () => new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
};
