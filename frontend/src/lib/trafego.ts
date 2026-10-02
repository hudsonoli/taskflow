import type { DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import type { DemandaDiretorio } from "@/types/demanda";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";
import type { TrafegoCargaAgregada, TrafegoFiltersState, TrafegoIndicadores, TrafegoResumo } from "@/types/trafego";

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

/**
 * D2-D3C2 — a carga vem agrupada e ordenada do servidor. Aqui só se faz o "relógio" das sessões
 * ativas andar entre dois fetches, como `buildCarga(…, now)` fazia a cada segundo: passados
 * `deltaSegundos` desde a resposta, cada sessão ativa ganhou `delta` segundos, então o total do
 * grupo sobe `sessoesAtivas × delta`. Reordena (maior carga primeiro) porque grupos com mais
 * sessões ultrapassam os demais com o tempo; empate mantém a ordem do servidor (sort estável).
 */
export function cargaComRelogio(itens: TrafegoCargaAgregada[], deltaSegundos: number): TrafegoCargaAgregada[] {
  const delta = Math.max(0, Math.floor(deltaSegundos));
  return itens
    .map((item) => ({ ...item, tempoAtivoTotalSegundos: item.tempoAtivoTotalSegundos + item.sessoesAtivas * delta }))
    .sort((primeiro, segundo) => segundo.tempoAtivoTotalSegundos - primeiro.tempoAtivoTotalSegundos);
}

/**
 * D2-D3C1 — o resumo vem do servidor (`GET /sessoes-trabalho/trafego/indicadores`), agregado
 * sobre o universo integral. Aqui só se faz o "relógio" das sessões ATIVAS andar entre dois
 * fetches, como o antigo `buildResumo(…, now)` fazia a cada segundo: passados `deltaSegundos`
 * desde a resposta, cada ativa ganhou `delta` segundos — soma = servidor + ativas × delta;
 * maior = máx(maior do servidor, maior ativa + delta); média = soma / (ativas + encerradas),
 * arredondada. Contagens e distintos não dependem do relógio.
 */
export function resumoDeIndicadores(indicadores: TrafegoIndicadores, deltaSegundos: number): TrafegoResumo {
  const delta = Math.max(0, Math.floor(deltaSegundos));
  const tempoTotal = indicadores.tempoOperacionalEstimadoSegundos + indicadores.sessoesAtivas * delta;
  const quantidade = indicadores.sessoesAtivas + indicadores.sessoesEncerradas;

  return {
    sessoesAtivas: indicadores.sessoesAtivas,
    sessoesEncerradas: indicadores.sessoesEncerradas,
    demandasDistintas: indicadores.demandasDistintas,
    usuariosDistintos: indicadores.usuariosDistintos,
    departamentosDistintos: indicadores.departamentosDistintos,
    tempoOperacionalEstimadoSegundos: tempoTotal,
    tempoMedioSessaoSegundos: quantidade > 0 ? Math.round(tempoTotal / quantidade) : 0,
    maiorSessaoSegundos:
      indicadores.sessoesAtivas > 0
        ? Math.max(indicadores.maiorSessaoSegundos, indicadores.maiorSessaoAtivaSegundos + delta)
        : indicadores.maiorSessaoSegundos,
  };
}

export const periodoParaDataInicio: Record<TrafegoFiltersState["periodo"], () => string> = {
  hoje: () => new Date(new Date().setHours(0, 0, 0, 0)).toISOString(),
  "24h": () => new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  "7d": () => new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  "30d": () => new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
};
