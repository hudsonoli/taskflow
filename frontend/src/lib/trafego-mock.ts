import type {
  TrafegoAgoraItem,
  TrafegoCargaItem,
  TrafegoFiltersState,
  TrafegoResumo,
  TrafegoSessaoStatus,
} from "@/types/trafego";

export const EMPRESA_TRAFEGO_PADRAO_ID = "empresa-principal";

export const trafegoEmpresasMock = [
  { id: "empresa-principal", nome: "TaskFloww Agência" },
];

export const trafegoUsuariosMock = [
  {
    id: "user-1",
    nome: "Hudson Cunha",
    departamentoId: "departamento-atendimento",
  },
  {
    id: "user-2",
    nome: "Marina Lopes",
    departamentoId: "departamento-criacao",
  },
  {
    id: "user-3",
    nome: "Rafael Nunes",
    departamentoId: "departamento-midia",
  },
  {
    id: "user-4",
    nome: "Bianca Prado",
    departamentoId: "departamento-revisao",
  },
];

export const trafegoDepartamentosMock = [
  { id: "departamento-atendimento", nome: "Atendimento" },
  { id: "departamento-criacao", nome: "Criação" },
  { id: "departamento-redacao", nome: "Redação" },
  { id: "departamento-midia", nome: "Mídia" },
  { id: "departamento-revisao", nome: "Revisão" },
];

export const trafegoDemandasMock = [
  { id: "demanda-1", nome: "Landing page campanha verão" },
  { id: "demanda-2", nome: "Sequência de e-mails B2B" },
  { id: "demanda-3", nome: "Anúncios Google Ads" },
  { id: "demanda-4", nome: "Revisão de peças sociais" },
  { id: "demanda-5", nome: "Plano de conteúdo mensal" },
];

export const trafegoEtapasMock = [
  { id: "etapa-atendimento", nome: "Atendimento" },
  { id: "etapa-redacao", nome: "Redação" },
  { id: "etapa-direcao-arte", nome: "Direção de Arte" },
  { id: "etapa-midia", nome: "Mídia" },
  { id: "etapa-revisao", nome: "Revisão" },
];

export const trafegoAgoraMock: TrafegoAgoraItem[] = [
  {
    sessaoId: "sessao-1",
    empresaId: "empresa-principal",
    agenciaId: "agencia-principal",
    demandaId: "demanda-1",
    workflowEtapaId: "etapa-redacao",
    usuarioId: "user-2",
    departamentoId: "departamento-redacao",
    inicioEm: "2026-07-12T10:05:00.000Z",
    tempoDecorridoSegundos: 5100,
    status: "ativa",
    eventoInicioId: "evento-101",
  },
  {
    sessaoId: "sessao-2",
    empresaId: "empresa-principal",
    agenciaId: "agencia-principal",
    demandaId: "demanda-3",
    workflowEtapaId: "etapa-midia",
    usuarioId: "user-3",
    departamentoId: "departamento-midia",
    inicioEm: "2026-07-12T10:42:00.000Z",
    tempoDecorridoSegundos: 2880,
    status: "ativa",
    eventoInicioId: "evento-102",
  },
  {
    sessaoId: "sessao-3",
    empresaId: "empresa-principal",
    agenciaId: "agencia-principal",
    demandaId: "demanda-4",
    workflowEtapaId: "etapa-revisao",
    usuarioId: "user-4",
    departamentoId: "departamento-revisao",
    inicioEm: "2026-07-12T11:18:00.000Z",
    tempoDecorridoSegundos: 1260,
    status: "ativa",
    eventoInicioId: "evento-103",
  },
  {
    sessaoId: "sessao-4",
    empresaId: "empresa-principal",
    agenciaId: null,
    demandaId: "demanda-5",
    workflowEtapaId: "etapa-atendimento",
    usuarioId: null,
    departamentoId: "departamento-atendimento",
    inicioEm: "2026-07-12T11:34:00.000Z",
    tempoDecorridoSegundos: 900,
    status: "ativa",
    eventoInicioId: "evento-104",
  },
];

const trafegoResumoBase: TrafegoResumo = {
  sessoesAtivas: 4,
  sessoesEncerradas: 18,
  demandasDistintas: 11,
  usuariosDistintos: 4,
  departamentosDistintos: 5,
  tempoOperacionalEstimadoSegundos: 73440,
  tempoMedioSessaoSegundos: 3340,
  maiorSessaoSegundos: 11160,
  inicioPeriodo: "2026-07-11T12:00:00.000Z",
  fimPeriodo: "2026-07-12T12:00:00.000Z",
};

export const statusTrafegoLabels: Record<TrafegoSessaoStatus, string> = {
  ativa: "Em execução",
  pausada: "Pausada",
  bloqueada: "Bloqueada",
  aguardando_cliente: "Aguardando cliente",
};

export function formatTempoOperacional(seconds: number) {
  const safeSeconds = Math.max(0, seconds);
  const totalMinutes = Math.floor(safeSeconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) return `${minutes} min`;

  return `${hours}h ${String(minutes).padStart(2, "0")}min`;
}

export function resolveTrafegoUsuarioNome(usuarioId: string | null) {
  if (!usuarioId) return "Sem usuário";
  return (
    trafegoUsuariosMock.find((usuario) => usuario.id === usuarioId)?.nome ??
    usuarioId
  );
}

export function resolveTrafegoDepartamentoNome(departamentoId: string | null) {
  if (!departamentoId) return "Sem departamento";
  return (
    trafegoDepartamentosMock.find(
      (departamento) => departamento.id === departamentoId
    )?.nome ?? departamentoId
  );
}

export function resolveTrafegoDemandaNome(demandaId: string) {
  return (
    trafegoDemandasMock.find((demanda) => demanda.id === demandaId)?.nome ??
    demandaId
  );
}

export function resolveTrafegoEtapaNome(workflowEtapaId: string | null) {
  if (!workflowEtapaId) return "Sem etapa";
  return (
    trafegoEtapasMock.find((etapa) => etapa.id === workflowEtapaId)?.nome ??
    workflowEtapaId
  );
}

function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

function sessionMatchesFilters(
  session: TrafegoAgoraItem,
  filters: TrafegoFiltersState
) {
  const demandaNome = resolveTrafegoDemandaNome(session.demandaId);
  const demandaMatches = filters.demandaQuery.trim()
    ? normalize(`${session.demandaId} ${demandaNome}`).includes(
        normalize(filters.demandaQuery)
      )
    : true;

  return (
    session.empresaId === filters.empresaId &&
    (filters.usuarioIds.length === 0 ||
      (session.usuarioId !== null &&
        filters.usuarioIds.includes(session.usuarioId))) &&
    (filters.departamentoIds.length === 0 ||
      (session.departamentoId !== null &&
        filters.departamentoIds.includes(session.departamentoId))) &&
    (filters.status === "todos" || session.status === filters.status) &&
    demandaMatches
  );
}

export function getTrafegoAgora(filters: TrafegoFiltersState) {
  return trafegoAgoraMock
    .filter((session) => sessionMatchesFilters(session, filters))
    .sort(
      (first, second) =>
        new Date(first.inicioEm).getTime() - new Date(second.inicioEm).getTime()
    );
}

function buildCarga(
  sessions: TrafegoAgoraItem[],
  tipoAgrupamento: "usuario" | "departamento"
): TrafegoCargaItem[] {
  const groups = new Map<string, TrafegoAgoraItem[]>();

  sessions.forEach((session) => {
    const agrupamentoId =
      tipoAgrupamento === "usuario" ? session.usuarioId : session.departamentoId;

    if (!agrupamentoId) return;

    groups.set(agrupamentoId, [...(groups.get(agrupamentoId) ?? []), session]);
  });

  return Array.from(groups.entries())
    .map(([agrupamentoId, groupSessions]) => {
      const demandIds = new Set(
        groupSessions.map((session) => session.demandaId)
      );
      const oldestStart = groupSessions.reduce((oldest, session) =>
        new Date(session.inicioEm).getTime() <
        new Date(oldest.inicioEm).getTime()
          ? session
          : oldest
      );

      return {
        agrupamentoId,
        tipoAgrupamento,
        sessoesAtivas: groupSessions.length,
        demandasDistintas: demandIds.size,
        tempoAtivoTotalSegundos: groupSessions.reduce(
          (sum, session) => sum + session.tempoDecorridoSegundos,
          0
        ),
        inicioMaisAntigo: oldestStart.inicioEm,
        ultimaAtualizacao: "2026-07-12T12:00:00.000Z",
      };
    })
    .sort(
      (first, second) =>
        second.tempoAtivoTotalSegundos - first.tempoAtivoTotalSegundos
    );
}

export function getTrafegoCargaUsuarios(filters: TrafegoFiltersState) {
  return buildCarga(getTrafegoAgora(filters), "usuario");
}

export function getTrafegoCargaDepartamentos(filters: TrafegoFiltersState) {
  return buildCarga(getTrafegoAgora(filters), "departamento");
}

export function getTrafegoResumo(filters: TrafegoFiltersState): TrafegoResumo {
  const sessions = getTrafegoAgora(filters);
  const userIds = new Set(
    sessions
      .map((session) => session.usuarioId)
      .filter((usuarioId): usuarioId is string => usuarioId !== null)
  );
  const departamentoIds = new Set(
    sessions
      .map((session) => session.departamentoId)
      .filter(
        (departamentoId): departamentoId is string => departamentoId !== null
      )
  );
  const demandaIds = new Set(sessions.map((session) => session.demandaId));
  const activeSeconds = sessions.reduce(
    (sum, session) => sum + session.tempoDecorridoSegundos,
    0
  );
  const periodMultiplier: Record<TrafegoFiltersState["periodo"], number> = {
    hoje: 0.65,
    "24h": 1,
    "7d": 4.8,
    "30d": 17.5,
  };
  const multiplier = periodMultiplier[filters.periodo];
  const consideredSessions = sessions.length + Math.round(18 * multiplier);
  const operationalSeconds = Math.round(
    trafegoResumoBase.tempoOperacionalEstimadoSegundos * multiplier +
      activeSeconds
  );

  return {
    ...trafegoResumoBase,
    sessoesAtivas: sessions.length,
    sessoesEncerradas: Math.round(
      trafegoResumoBase.sessoesEncerradas * multiplier
    ),
    demandasDistintas: Math.max(demandaIds.size, Math.round(11 * multiplier)),
    usuariosDistintos: userIds.size,
    departamentosDistintos: departamentoIds.size,
    tempoOperacionalEstimadoSegundos: operationalSeconds,
    tempoMedioSessaoSegundos:
      consideredSessions > 0
        ? Math.round(operationalSeconds / consideredSessions)
        : 0,
    maiorSessaoSegundos:
      sessions.length > 0
        ? Math.max(
            trafegoResumoBase.maiorSessaoSegundos,
            ...sessions.map((session) => session.tempoDecorridoSegundos)
          )
        : trafegoResumoBase.maiorSessaoSegundos,
  };
}

export function classifyCarga(seconds: number) {
  if (seconds === 0) {
    return { label: "Livre", percent: 0, color: "bg-zinc-300" };
  }

  if (seconds < 1800) {
    return { label: "Leve", percent: 32, color: "bg-sky-300" };
  }

  if (seconds < 4200) {
    return { label: "Moderada", percent: 62, color: "bg-blue-400" };
  }

  return { label: "Alta", percent: 88, color: "bg-blue-700" };
}
