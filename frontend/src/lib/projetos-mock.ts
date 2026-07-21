import {
  EMPRESA_PADRAO_ID,
  generateCodigoInterno,
  generateId,
} from "@/lib/equipe-mock";
import type {
  Projeto,
  ProjetoAprovacao,
  ProjetoArquivo,
  ProjetoChecklistItem,
  ProjetoComentario,
  ProjetoEquipeMembro,
  ProjetoHistoricoEvento,
  ProjetoModeloCampanhaItem,
  ProjetoPrioridade,
  ProjetoStatus,
} from "@/types/projeto";

export { EMPRESA_PADRAO_ID, generateCodigoInterno, generateId };

export const AGENCIA_PADRAO_ID = "agencia-principal";

export const clientesProjetoDisponiveis = [
  { id: "cliente-1", nome: "Cliente Exemplo" },
  { id: "cliente-2", nome: "Clínica Clare" },
  { id: "cliente-3", nome: "Loja Boxx" },
];

export const responsaveisProjetoDisponiveis = [
  { id: "user-1", nome: "Hudson Cunha" },
  { id: "user-2", nome: "Ana Costa" },
  { id: "user-3", nome: "Carlos Lima" },
  { id: "user-4", nome: "João Silva" },
  { id: "user-5", nome: "Maria Souza" },
];

export const departamentosProjetoDisponiveis = [
  { id: "dep-atendimento", nome: "Atendimento" },
  { id: "dep-criacao", nome: "Criação" },
  { id: "dep-midia", nome: "Mídia" },
  { id: "dep-trafego", nome: "Tráfego" },
  { id: "dep-conteudo", nome: "Conteúdo" },
];

export const tiposTarefaProjetoDisponiveis = [
  { id: "tipo-post", nome: "Post social" },
  { id: "tipo-landing-page", nome: "Landing page" },
  { id: "tipo-email", nome: "E-mail marketing" },
  { id: "tipo-anuncio", nome: "Anúncio" },
  { id: "tipo-relatorio", nome: "Relatório" },
];

export const workflowsProjetoDisponiveis = [
  { id: "workflow-criacao", nome: "Criação padrão" },
  { id: "workflow-midia", nome: "Mídia paga" },
  { id: "workflow-conteudo", nome: "Conteúdo e revisão" },
];

export const statusProjetoLabels: Record<ProjetoStatus, string> = {
  planejamento: "Planejamento",
  ativo: "Ativo",
  pausado: "Pausado",
  concluido: "Concluído",
  cancelado: "Cancelado",
};

export const prioridadeProjetoLabels: Record<ProjetoPrioridade, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

function createHistorico(acao: string): ProjetoHistoricoEvento[] {
  return [
    {
      id: generateId("hist-projeto"),
      usuarioId: "user-1",
      usuario: "Hudson Cunha",
      acao,
      dataHora: "2026-07-10 09:32",
      ip: "192.168.0.10",
      dispositivo: "Chrome / macOS",
    },
    {
      id: generateId("hist-projeto"),
      usuarioId: "user-2",
      usuario: "Ana Costa",
      acao: "Resumo do projeto atualizado",
      dataHora: "2026-07-10 11:18",
      ip: "192.168.0.24",
      dispositivo: "Chrome / Windows",
    },
  ];
}

function createEquipe(): ProjetoEquipeMembro[] {
  return [
    {
      id: generateId("membro-projeto"),
      usuarioId: "user-2",
      nome: "Ana Costa",
      funcao: "Atendimento",
      departamentoId: "dep-atendimento",
      departamentoNome: "Atendimento",
    },
    {
      id: generateId("membro-projeto"),
      usuarioId: "user-3",
      nome: "Carlos Lima",
      funcao: "Direção de arte",
      departamentoId: "dep-criacao",
      departamentoNome: "Criação",
    },
  ];
}

function createModeloCampanha(): ProjetoModeloCampanhaItem[] {
  return [
    {
      id: generateId("modelo-item"),
      nomeDemanda: "Posts de lançamento",
      tipoTarefaId: "tipo-post",
      tipoTarefaNome: "Post social",
      briefingBase: "Criar peças para divulgação da campanha nas redes sociais.",
      prioridadePadrao: "media",
      workflowSugeridoId: "workflow-criacao",
      workflowSugeridoNome: "Criação padrão",
      responsavelOuSetorSugeridoId: "dep-criacao",
      responsavelOuSetorSugeridoNome: "Criação",
    },
    {
      id: generateId("modelo-item"),
      nomeDemanda: "Plano de mídia",
      tipoTarefaId: "tipo-anuncio",
      tipoTarefaNome: "Anúncio",
      briefingBase: "Definir segmentação, verba e canais de mídia paga.",
      prioridadePadrao: "alta",
      workflowSugeridoId: "workflow-midia",
      workflowSugeridoNome: "Mídia paga",
      responsavelOuSetorSugeridoId: "dep-midia",
      responsavelOuSetorSugeridoNome: "Mídia",
    },
  ];
}

function createArquivos(): ProjetoArquivo[] {
  return [
    {
      id: generateId("arquivo-projeto"),
      nome: "Briefing-geral.pdf",
      tipo: "PDF",
      tamanho: "1.2 MB",
      criadoEm: "2026-07-08",
      usuarioId: "user-2",
      usuarioNome: "Ana Costa",
    },
  ];
}

function createChecklist(): ProjetoChecklistItem[] {
  return [
    {
      id: generateId("checklist-projeto"),
      descricao: "Aprovar posicionamento com o cliente",
      concluido: true,
      concluidoEm: "2026-07-08 10:00",
      concluidoPor: "Ana Costa",
    },
    {
      id: generateId("checklist-projeto"),
      descricao: "Definir cronograma de entregas",
      concluido: true,
      concluidoEm: "2026-07-09 14:20",
      concluidoPor: "Carlos Lima",
    },
    {
      id: generateId("checklist-projeto"),
      descricao: "Validar modelo de campanha com a equipe",
      concluido: false,
    },
  ];
}

function createComentarios(): ProjetoComentario[] {
  return [
    {
      id: generateId("comentario-projeto"),
      autorId: "user-2",
      autorNome: "Ana Costa",
      texto: "Cliente aprovou o direcionamento inicial. Podemos seguir para produção.",
      createdAt: "2026-07-09 09:15",
    },
    {
      id: generateId("comentario-projeto"),
      autorId: "user-3",
      autorNome: "Carlos Lima",
      texto: "Vou ajustar o cronograma considerando o novo prazo do cliente.",
      createdAt: "2026-07-10 16:40",
    },
  ];
}

function createAprovacoes(): ProjetoAprovacao[] {
  return [
    {
      id: generateId("aprovacao-projeto"),
      titulo: "Aprovação do resumo do projeto",
      descricao: "Validação do resumo operacional antes da divulgação às demandas vinculadas.",
      status: "aprovado",
      solicitadoPor: "Ana Costa",
      solicitadoEm: "2026-07-08 11:00",
      respondidoPor: "Hudson Cunha",
      respondidoEm: "2026-07-08 15:30",
    },
    {
      id: generateId("aprovacao-projeto"),
      titulo: "Aprovação do modelo de campanha",
      status: "pendente",
      solicitadoPor: "Carlos Lima",
      solicitadoEm: "2026-07-10 10:00",
    },
  ];
}

export const projetosMock: Projeto[] = [
  {
    id: "projeto-1",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    clienteId: "cliente-1",
    codigoInterno: "#2401",
    nome: "Reposicionamento institucional",
    campanha: "Marca 2026",
    descricao: "Projeto de comunicação para atualização de posicionamento e presença digital.",
    status: "ativo",
    prioridade: "alta",
    responsavelIds: ["user-2", "user-3"],
    departamentoResponsavelIds: ["dep-atendimento", "dep-criacao"],
    dataInicio: "2026-07-01",
    dataFimPrevista: "2026-08-16",
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-10T11:18:00-03:00",
    resumo:
      "Campanha focada em consolidar mensagens-chave, revisar materiais institucionais e organizar entregas recorrentes para redes sociais.",
    modeloCampanhaId: "modelo-campanha-1",
    modeloCampanha: createModeloCampanha(),
    equipe: createEquipe(),
    arquivos: createArquivos(),
    historico: createHistorico("Projeto criado"),
    checklist: createChecklist(),
    comentarios: createComentarios(),
    aprovacoes: createAprovacoes(),
  },
  {
    id: "projeto-2",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    clienteId: "cliente-2",
    codigoInterno: "#2402",
    nome: "Campanha de captação",
    campanha: "Clare Leads Q3",
    descricao: "Campanha recorrente para aquisição de leads qualificados.",
    status: "planejamento",
    prioridade: "media",
    responsavelIds: ["user-5"],
    departamentoResponsavelIds: ["dep-midia"],
    dataInicio: "2026-07-15",
    dataFimPrevista: "2026-09-05",
    createdAt: "2026-07-05T10:00:00-03:00",
    updatedAt: "2026-07-09T15:20:00-03:00",
    resumo: "Planejamento inicial de peças, mídia paga e cadência de conteúdo.",
    modeloCampanhaId: "modelo-campanha-2",
    modeloCampanha: createModeloCampanha().slice(0, 1),
    equipe: createEquipe().slice(0, 1),
    arquivos: [],
    historico: createHistorico("Projeto em planejamento"),
    checklist: createChecklist().slice(0, 1),
    comentarios: [],
    aprovacoes: [],
  },
  {
    id: "projeto-3",
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    clienteId: "cliente-3",
    codigoInterno: "#2403",
    nome: "Calendário promocional",
    campanha: "Varejo Agosto",
    descricao: "Projeto de calendário mensal para campanhas comerciais e datas promocionais.",
    status: "concluido",
    prioridade: "baixa",
    responsavelIds: ["user-4"],
    departamentoResponsavelIds: ["dep-criacao", "dep-conteudo"],
    dataInicio: "2026-06-01",
    dataFimPrevista: "2026-06-30",
    createdAt: "2026-06-01T08:45:00-03:00",
    updatedAt: "2026-06-30T17:40:00-03:00",
    resumo: "Projeto concluído com entregas de calendário, peças base e ajustes finais aprovados.",
    modeloCampanhaId: "modelo-campanha-3",
    modeloCampanha: [],
    equipe: createEquipe(),
    arquivos: [],
    historico: createHistorico("Projeto concluído"),
    checklist: createChecklist().map((item) => ({ ...item, concluido: true })),
    comentarios: createComentarios().slice(0, 1),
    aprovacoes: createAprovacoes().map((item) => ({ ...item, status: "aprovado" as const })),
  },
];

export function resolveClienteProjetoNome(clienteId: string): string {
  return (
    clientesProjetoDisponiveis.find((cliente) => cliente.id === clienteId)
      ?.nome ?? clienteId
  );
}

export function resolveResponsaveisProjetoNomes(ids: string[]): string {
  if (ids.length === 0) return "-";

  return ids
    .map(
      (id) =>
        responsaveisProjetoDisponiveis.find(
          (responsavel) => responsavel.id === id
        )?.nome ?? id
    )
    .join(", ");
}

export function resolveDepartamentosProjetoNomes(ids: string[]): string {
  if (ids.length === 0) return "-";

  return ids
    .map(
      (id) =>
        departamentosProjetoDisponiveis.find(
          (departamento) => departamento.id === id
        )?.nome ?? id
    )
    .join(", ");
}
