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
import {
  createWorkflowInstanceFromTemplate,
  workflowTemplatesMock,
} from "@/lib/workflows-mock";
import type {
  Demanda,
  DemandaHistoricoEvento,
  DemandaPrioridade,
  DemandaStatus,
} from "@/types/demanda";

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

function createHistorico(acao: string): DemandaHistoricoEvento[] {
  return [
    {
      id: generateId("hist-demanda"),
      usuarioId: "user-2",
      usuario: "Ana Costa",
      acao,
      dataHora: "2026-07-11 09:12",
      ip: "192.168.0.32",
      dispositivo: "Chrome / macOS",
    },
    {
      id: generateId("hist-demanda"),
      usuarioId: "user-3",
      usuario: "Carlos Lima",
      acao: "Workflow mock ajustado",
      dataHora: "2026-07-11 10:44",
      ip: "192.168.0.41",
      dispositivo: "Chrome / Windows",
    },
  ];
}

const workflowA = createWorkflowInstanceFromTemplate(
  workflowTemplatesMock[0],
  "demanda-1"
);
const workflowB = createWorkflowInstanceFromTemplate(
  workflowTemplatesMock[1],
  "demanda-2"
);
const workflowC = createWorkflowInstanceFromTemplate(
  workflowTemplatesMock[2],
  "demanda-3"
);
const workflowCConcluido = {
  ...workflowC,
  etapas: workflowC.etapas.map((etapa) => ({ ...etapa, status: "concluida" as const })),
};

export const demandasMock: Demanda[] = [
  {
    id: "demanda-1",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: "projeto-1",
    clienteId: "cliente-1",
    codigoInterno: "#D2401",
    nome: "Landing page institucional",
    briefing:
      "Criar landing page para apresentar o novo posicionamento institucional e capturar contatos qualificados.",
    status: "em_execucao",
    prioridade: "alta",
    usuarioResponsavelIds: ["user-2", "user-3"],
    departamentoResponsavelIds: ["dep-atendimento", "dep-criacao"],
    workflow: workflowA,
    workflowHistorico: [],
    prazoEtapaAtual: "2026-07-15",
    dataCriacao: "2026-07-11",
    dataInicio: "2026-07-11",
    dataFimPrevista: "2026-07-20",
    createdAt: "2026-07-11T09:00:00-03:00",
    updatedAt: "2026-07-11T10:44:00-03:00",
    historico: createHistorico("Demanda criada"),
  },
  {
    id: "demanda-2",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: "projeto-2",
    clienteId: "cliente-2",
    codigoInterno: "#D2402",
    nome: "Sequência de e-mails de nutrição",
    briefing:
      "Planejar e redigir sequência de e-mails para leads captados na campanha Clare Leads Q3.",
    status: "aguardando_cliente",
    prioridade: "media",
    usuarioResponsavelIds: ["user-5"],
    departamentoResponsavelIds: ["dep-conteudo"],
    workflow: workflowB,
    workflowHistorico: [],
    prazoEtapaAtual: "2026-07-18",
    dataCriacao: "2026-07-10",
    dataInicio: "2026-07-12",
    dataFimPrevista: "2026-07-24",
    createdAt: "2026-07-10T14:20:00-03:00",
    updatedAt: "2026-07-11T11:10:00-03:00",
    historico: createHistorico("Demanda enviada ao cliente"),
  },
  {
    id: "demanda-3",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    projetoId: "projeto-3",
    clienteId: "cliente-3",
    codigoInterno: "#D2403",
    nome: "Posts promocionais de agosto",
    briefing:
      "Desdobrar peças promocionais para calendário mensal de varejo com foco em ofertas de agosto.",
    status: "concluida",
    prioridade: "baixa",
    usuarioResponsavelIds: ["user-4"],
    departamentoResponsavelIds: ["dep-criacao"],
    workflow: workflowCConcluido,
    workflowHistorico: [],
    prazoEtapaAtual: "2026-07-08",
    dataCriacao: "2026-07-01",
    dataInicio: "2026-07-02",
    dataFimPrevista: "2026-07-08",
    createdAt: "2026-07-01T08:30:00-03:00",
    updatedAt: "2026-07-08T17:40:00-03:00",
    historico: createHistorico("Demanda concluída"),
  },
];

export function resolveProjetoDemandaNome(projetoId: string): string {
  return (
    projetosDemandaDisponiveis.find((projeto) => projeto.id === projetoId)
      ?.nome ?? projetoId
  );
}

export function resolveClienteIdByProjetoId(projetoId: string): string {
  return (
    projetosDemandaDisponiveis.find((projeto) => projeto.id === projetoId)
      ?.clienteId ?? ""
  );
}
