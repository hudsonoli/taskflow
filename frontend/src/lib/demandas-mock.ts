import {
  AGENCIA_PADRAO_ID,
  EMPRESA_PADRAO_ID,
  departamentosProjetoDisponiveis,
  generateCodigoInterno,
  generateId,
  projetosMock,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  responsaveisProjetoDisponiveis,
} from "@/lib/projetos-mock";
import type {
  Demanda,
  DemandaHistoricoEvento,
  DemandaPrioridade,
  DemandaStatus,
  DemandaWorkflowEtapa,
  DemandaWorkflowEtapaStatus,
} from "@/types/demanda";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import { correspondeUsuario, resolverUsuarioPorReferencia } from "@/lib/referencias";

export {
  AGENCIA_PADRAO_ID,
  EMPRESA_PADRAO_ID,
  departamentosProjetoDisponiveis,
  generateCodigoInterno,
  generateId,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  responsaveisProjetoDisponiveis,
};

export const projetosDemandaDisponiveis = projetosMock.map((projeto) => ({
  id: projeto.id,
  nome: projeto.nome,
  clienteId: projeto.clienteId,
}));

export const statusDemandaLabels: Record<DemandaStatus, string> = {
  rascunho: "Rascunho",
  planejada: "Planejada",
  em_execucao: "Em execução",
  pausada: "Pausada",
  bloqueada: "Bloqueada",
  aguardando_cliente: "Aguardando cliente",
  concluida: "Concluída",
  cancelada: "Cancelada",
};

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
};

export const workflowEtapaStatusLabels: Record<DemandaWorkflowEtapaStatus, string> = {
  pendente: "Pendente",
  em_execucao: "Em execução",
  pausada: "Pausada",
  concluida: "Concluída",
};

// IDs fixos (não gerados em tempo de import): gerar via generateId() no escopo do módulo
// roda uma vez no servidor e de novo no cliente, com valores diferentes, quebrando a hidratação do React.
function createHistorico(seed: string, acao: string): DemandaHistoricoEvento[] {
  return [
    {
      id: `hist-demanda-${seed}-1`,
      usuarioId: "user-2",
      usuario: "Ana Costa",
      acao,
      dataHora: "2026-07-11 09:12",
      ip: "192.168.0.32",
      dispositivo: "Chrome / macOS",
    },
    {
      id: `hist-demanda-${seed}-2`,
      usuarioId: "user-3",
      usuario: "Carlos Lima",
      acao: "Workflow mock ajustado",
      dataHora: "2026-07-11 10:44",
      ip: "192.168.0.41",
      dispositivo: "Chrome / Windows",
    },
  ];
}

function createWorkflowEtapas(seed: string): DemandaWorkflowEtapa[] {
  return [
    {
      id: `etapa-demanda-${seed}-1`,
      nome: "Atendimento",
      ordem: 1,
      usuarioResponsavelIds: ["user-2"],
      departamentoResponsavelIds: ["dep-atendimento"],
      prazoHoras: 8,
      status: "concluida",
    },
    {
      id: `etapa-demanda-${seed}-2`,
      nome: "Criação",
      ordem: 2,
      usuarioResponsavelIds: ["user-3"],
      departamentoResponsavelIds: ["dep-criacao"],
      prazoHoras: 24,
      status: "em_execucao",
    },
    {
      id: `etapa-demanda-${seed}-3`,
      nome: "Revisão",
      ordem: 3,
      usuarioResponsavelIds: ["user-5"],
      departamentoResponsavelIds: ["dep-conteudo"],
      prazoHoras: 12,
      status: "pendente",
    },
  ];
}

const workflowA = createWorkflowEtapas("a");
const workflowB = createWorkflowEtapas("b");
const workflowC = createWorkflowEtapas("c");

export const demandasMock: Demanda[] = [
  {
    id: "demanda-1",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: "projeto-1",
    clienteId: "cliente-1",
    codigoInterno: "#260001",
    nome: "Landing page institucional",
    pit: "C3A-0008/26",
    briefing:
      "Criar landing page para apresentar o novo posicionamento institucional e capturar contatos qualificados.",
    status: "em_execucao",
    prioridade: "alta",
    usuarioResponsavelIds: ["user-2", "user-3"],
    departamentoResponsavelIds: ["dep-atendimento", "dep-criacao"],
    workflowEtapas: workflowA,
    etapaAtualId: workflowA[1].id,
    prazoEtapaAtual: "2026-07-15T18:00",
    dataCriacao: "2026-07-11",
    dataInicio: "2026-07-11",
    dataFimPrevista: "2026-07-20T17:00",
    emailConclusaoEnviado: false,
    sinalizada: true,
    checklist: [],
    arquivos: [],
    comentarios: [],
    createdAt: "2026-07-11T09:00:00-03:00",
    updatedAt: "2026-07-11T10:44:00-03:00",
    historico: createHistorico("d1", "Demanda criada"),
  },
  {
    id: "demanda-2",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: "projeto-2",
    clienteId: "cliente-2",
    codigoInterno: "#260002",
    nome: "Sequência de e-mails de nutrição",
    briefing: "Planejar e redigir sequência de e-mails para leads captados na campanha Clare Leads Q3.",
    status: "aguardando_cliente",
    prioridade: "media",
    usuarioResponsavelIds: ["user-5"],
    departamentoResponsavelIds: ["dep-conteudo"],
    workflowEtapas: workflowB,
    etapaAtualId: workflowB[2].id,
    prazoEtapaAtual: "2026-07-18T12:00",
    dataCriacao: "2026-07-10",
    dataInicio: "2026-07-12",
    dataFimPrevista: "2026-07-24T12:00",
    emailConclusaoEnviado: false,
    sinalizada: false,
    checklist: [],
    arquivos: [],
    comentarios: [],
    createdAt: "2026-07-10T14:20:00-03:00",
    updatedAt: "2026-07-11T11:10:00-03:00",
    historico: createHistorico("d2", "Demanda enviada ao cliente"),
  },
  {
    id: "demanda-3",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: "projeto-3",
    clienteId: "cliente-3",
    codigoInterno: "#260003",
    nome: "Posts promocionais de agosto",
    briefing: "Desdobrar peças promocionais para calendário mensal de varejo com foco em ofertas de agosto.",
    status: "concluida",
    prioridade: "baixa",
    usuarioResponsavelIds: ["user-4"],
    departamentoResponsavelIds: ["dep-criacao"],
    workflowEtapas: workflowC.map((etapa) => ({ ...etapa, status: "concluida" })),
    etapaAtualId: workflowC[2].id,
    prazoEtapaAtual: "2026-07-08T16:30",
    dataCriacao: "2026-07-01",
    dataInicio: "2026-07-02",
    dataFimPrevista: "2026-07-08T16:30",
    emailConclusaoEnviado: false,
    sinalizada: false,
    checklist: [],
    arquivos: [],
    comentarios: [],
    createdAt: "2026-07-01T08:30:00-03:00",
    updatedAt: "2026-07-08T17:40:00-03:00",
    historico: createHistorico("d3", "Demanda concluída"),
  },
];

export function resolveProjetoDemandaNome(projetoId: string): string {
  if (!projetoId) return "Sem projeto";
  return projetosDemandaDisponiveis.find((projeto) => projeto.id === projetoId)?.nome ?? projetoId;
}

export function resolveClienteIdByProjetoId(projetoId: string): string {
  return projetosDemandaDisponiveis.find((projeto) => projeto.id === projetoId)?.clienteId ?? "";
}

// Compatibilidade entre a lista mock legada de responsáveis (ids "user-N") e o cadastro real de
// usuários (ids "usuario-N") — normaliza até os dois cadastros serem unificados.
export function normalizarUsuarioId(id: string): string {
  return id.replace(/^user-/, "usuario-");
}

/**
 * `usuarioId` pode ser UUID real ou codigoInterno — o registro guardado em
 * `usuarioResponsavelIds` é resolvido no diretório e comparado nos dois formatos (ver
 * lib/referencias.ts). Precisa do diretório porque `usuarioAtual.id` (sessão real) é
 * sempre UUID, mas a relação em si pode ter sido gravada como codigoInterno enquanto
 * Demanda continuar mock.
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

export function resolveProjetoResumo(projetoId: string): string {
  return projetosMock.find((projeto) => projeto.id === projetoId)?.resumo ?? "";
}

export function resolveModeloCampanhaPorProjeto(projetoId: string) {
  return projetosMock.find((projeto) => projeto.id === projetoId)?.modeloCampanha ?? [];
}

export function formatPrazo(value: string): string {
  if (!value) return "Sem prazo";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const hasTime = value.includes("T");
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    ...(hasTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

/**
 * Ordena por `prazoEtapaAtual` (data e horário da etapa em execução — mesmo campo usado por
 * `classificarTarefa` para "prevista hoje/semana"). Tarefas sem prazo válido ficam por último.
 * Usado pela Pauta para agrupar por dia e ordenar dentro do dia na mesma ordem vista pela equipe.
 */
export function compararPorAgenda(a: Demanda, b: Demanda): number {
  const prazoA = new Date(a.prazoEtapaAtual).getTime();
  const prazoB = new Date(b.prazoEtapaAtual).getTime();
  const validoA = !Number.isNaN(prazoA);
  const validoB = !Number.isNaN(prazoB);

  if (!validoA && !validoB) return 0;
  if (!validoA) return 1;
  if (!validoB) return -1;
  return prazoA - prazoB;
}
