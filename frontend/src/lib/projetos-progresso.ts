// Visão "Progresso" de Projetos — regras PURAS (sem DOM, sem alias de import em runtime): o que conta no percentual do projeto, a composição por situação, o fluxo de etapas
// de cada tarefa, quem responde e quem está trabalhando agora, filtros e ordem. `npm run test:projetos-progresso` (node --test). A tela só desenha o que sai daqui.
import type { Demanda, DemandaStatus, DemandaWorkflowEtapa } from "../types/demanda.ts";
import type { Projeto } from "../types/projeto.ts";

// ── projeto: percentual e composição ─────────────────────────────────────────────────────────────────────────

/**
 * DENOMINADOR do percentual do projeto (única regra): as tarefas do projeto que o usuário enxerga, EXCETO `cancelada` (nunca será entregue; o próprio domínio a trata
 * como finalizada/fora da operação em `classificarTarefa` e na Pauta) e `arquivada` (a listagem do servidor já a omite). Numerador: tarefas `concluida`.
 * Não usa horas, prazo, sessões, `updated_at` nem a contagem de etapas (workflows diferentes não são comparáveis).
 */
export const STATUS_FORA_DO_PROGRESSO: readonly DemandaStatus[] = ["cancelada", "arquivada"];

export function contaNoProgresso(demanda: Pick<Demanda, "status">): boolean {
  return !STATUS_FORA_DO_PROGRESSO.includes(demanda.status);
}

export type SegmentoId = "concluida" | "em_execucao" | "aguardando_cliente" | "bloqueada" | "pausada" | "planejada";

/** Composição da barra do projeto, só com status REAIS da Demanda. `planejada` agrupa `planejada` e `rascunho` (ainda não iniciadas). */
export const SEGMENTOS: ReadonlyArray<{ id: SegmentoId; rotulo: string; status: readonly DemandaStatus[] }> = [
  { id: "concluida", rotulo: "Concluída", status: ["concluida"] },
  { id: "em_execucao", rotulo: "Em execução", status: ["em_execucao"] },
  { id: "aguardando_cliente", rotulo: "Aguardando cliente", status: ["aguardando_cliente"] },
  { id: "bloqueada", rotulo: "Bloqueada", status: ["bloqueada"] },
  { id: "pausada", rotulo: "Pausada", status: ["pausada"] },
  { id: "planejada", rotulo: "Planejada", status: ["planejada", "rascunho"] },
];

export type ResumoProjeto = {
  total: number;
  concluidas: number;
  /** 0–100 inteiro; `null` = projeto sem tarefas consideradas (nunca "0%"). */
  percentual: number | null;
  bloqueadas: number;
  atrasadas: number;
  aguardandoCliente: number;
  segmentos: Array<{ id: SegmentoId; rotulo: string; quantidade: number }>;
};

export function resumoDoProjeto(demandas: readonly Demanda[], estaAtrasada: (demanda: Demanda) => boolean): ResumoProjeto {
  const consideradas = demandas.filter(contaNoProgresso);
  const concluidas = consideradas.filter((demanda) => demanda.status === "concluida").length;
  const segmentos = SEGMENTOS.map((segmento) => ({
    id: segmento.id,
    rotulo: segmento.rotulo,
    quantidade: consideradas.filter((demanda) => segmento.status.includes(demanda.status)).length,
  }));
  return {
    total: consideradas.length,
    concluidas,
    percentual: consideradas.length === 0 ? null : Math.round((concluidas / consideradas.length) * 100),
    bloqueadas: consideradas.filter((demanda) => demanda.status === "bloqueada").length,
    atrasadas: consideradas.filter((demanda) => estaAtrasada(demanda)).length,
    aguardandoCliente: consideradas.filter((demanda) => demanda.status === "aguardando_cliente").length,
    segmentos,
  };
}

// ── tarefa: fluxo, etapa atual e responsáveis ────────────────────────────────────────────────────────────────

export type PassoFluxo = "concluida" | "atual" | "atual_pausada" | "pendente";

export type FluxoDaTarefa =
  | { tipo: "sem_workflow" }
  | {
      tipo: "workflow";
      total: number;
      concluidas: number;
      passos: Array<{ id: string; nome: string; estado: PassoFluxo }>;
      /** Etapa atual ÚNICA do domínio (`etapaAtualId`, derivada no servidor: menor `ordem` não concluída). `null` = todas concluídas. */
      atual: DemandaWorkflowEtapa | null;
      todasConcluidas: boolean;
    };

/** NÃO é percentual de trabalho: etapas têm esforços diferentes. Só "N/M etapas". */
export function fluxoDaTarefa(demanda: Pick<Demanda, "workflowEtapas" | "etapaAtualId">): FluxoDaTarefa {
  const etapas = [...(demanda.workflowEtapas ?? [])].sort((a, b) => a.ordem - b.ordem);
  if (etapas.length === 0) return { tipo: "sem_workflow" };
  const concluidas = etapas.filter((etapa) => etapa.status === "concluida").length;
  const atual = etapas.find((etapa) => etapa.id === demanda.etapaAtualId && etapa.status !== "concluida") ?? null;
  return {
    tipo: "workflow",
    total: etapas.length,
    concluidas,
    passos: etapas.map((etapa) => ({
      id: etapa.id,
      nome: etapa.nome,
      estado: etapa.status === "concluida" ? "concluida" : atual && etapa.id === atual.id ? (etapa.status === "pausada" ? "atual_pausada" : "atual") : "pendente",
    })),
    atual,
    todasConcluidas: concluidas === etapas.length,
  };
}

export type ResponsaveisDaTarefa = {
  usuarioIds: string[];
  departamentoIds: string[];
  /** de onde vieram: a etapa atual do workflow, a própria tarefa quando não há workflow, ou nenhuma (workflow com todas as etapas concluídas: não há quem responda) */
  origem: "etapa_atual" | "tarefa" | "workflow_concluido";
  /** nenhum usuário nem departamento (NÃO vale para `workflow_concluido`: ali não falta responsável, acabou o fluxo) */
  semResponsavel: boolean;
};

/**
 * RESPONSÁVEIS = usuários atribuídos à ETAPA ATUAL (workflow); se não houver usuário, o(s) departamento(s). Tarefa sem workflow: os responsáveis da própria tarefa.
 * Nunca mistura com "trabalhando agora" (sessão ativa), que é outro conceito.
 */
export function responsaveisDaTarefa(demanda: Pick<Demanda, "workflowEtapas" | "etapaAtualId" | "usuarioResponsavelIds" | "departamentoResponsavelIds">): ResponsaveisDaTarefa {
  const fluxo = fluxoDaTarefa(demanda);
  if (fluxo.tipo === "workflow" && !fluxo.atual) return { usuarioIds: [], departamentoIds: [], origem: "workflow_concluido", semResponsavel: false };
  const [usuarioIds, departamentoIds, origem] =
    fluxo.tipo === "workflow"
      ? [fluxo.atual?.usuarioResponsavelIds ?? [], fluxo.atual?.departamentoResponsavelIds ?? [], "etapa_atual" as const]
      : [demanda.usuarioResponsavelIds ?? [], demanda.departamentoResponsavelIds ?? [], "tarefa" as const];
  // departamento só aparece quando NÃO há usuário
  const departamentosVisiveis = usuarioIds.length > 0 ? [] : departamentoIds;
  return { usuarioIds: [...usuarioIds], departamentoIds: [...departamentosVisiveis], origem, semResponsavel: usuarioIds.length === 0 && departamentoIds.length === 0 };
}

// ── trabalhando agora (sessão ativa) ─────────────────────────────────────────────────────────────────────────

/**
 * O que a sessão do usuário deixa saber, conforme a autoridade dele: `pessoas` (demandaId -> usuarioIds) para quem vê a Central de Tráfego (admin/gestor);
 * `demandaIds` (só quais tarefas têm alguém trabalhando) para Atendimento/Heads/Gestão da Pauta; `nenhum` para os demais — a tela nunca inventa o que o servidor não entrega.
 */
export type TrabalhandoAgora =
  | { fonte: "pessoas"; porDemanda: Record<string, string[]> }
  | { fonte: "demandas"; demandaIds: ReadonlySet<string> }
  | { fonte: "nenhuma" };

export const SEM_TRABALHO_AGORA: TrabalhandoAgora = { fonte: "nenhuma" };

export function trabalhandoAgoraNaTarefa(demandaId: string, agora: TrabalhandoAgora, responsaveis: ResponsaveisDaTarefa): {
  /** responsáveis da etapa atual que TÊM sessão ativa nesta tarefa ("Agora") */
  responsaveisAgora: string[];
  /** quem tem sessão ativa mas NÃO está entre os responsáveis exibidos — não é afirmado como responsável */
  outrosAgora: string[];
  /** só sabemos que há alguém (fonte por demanda) */
  alguemAgora: boolean;
} {
  if (agora.fonte === "pessoas") {
    const ativos = agora.porDemanda[demandaId] ?? [];
    return {
      responsaveisAgora: responsaveis.usuarioIds.filter((id) => ativos.includes(id)),
      outrosAgora: ativos.filter((id) => !responsaveis.usuarioIds.includes(id)),
      alguemAgora: ativos.length > 0,
    };
  }
  if (agora.fonte === "demandas") return { responsaveisAgora: [], outrosAgora: [], alguemAgora: agora.demandaIds.has(demandaId) };
  return { responsaveisAgora: [], outrosAgora: [], alguemAgora: false };
}

// ── ordem ────────────────────────────────────────────────────────────────────────────────────────────────────

/** Grupos de relevância dentro do projeto (não existe ordem oficial para tarefas de projeto): bloqueadas, atrasadas, em execução, aguardando cliente, pausadas, planejadas, concluídas. */
export function grupoDeOrdem(demanda: Demanda, estaAtrasada: boolean): number {
  if (demanda.status === "concluida") return 6;
  if (demanda.status === "bloqueada") return 0;
  if (estaAtrasada) return 1;
  if (demanda.status === "em_execucao") return 2;
  if (demanda.status === "aguardando_cliente") return 3;
  if (demanda.status === "pausada") return 4;
  return 5; // planejada / rascunho
}

export function ordenarTarefas(demandas: readonly Demanda[], estaAtrasada: (demanda: Demanda) => boolean): Demanda[] {
  return demandas
    .filter(contaNoProgresso)
    .map((demanda) => ({ demanda, grupo: grupoDeOrdem(demanda, estaAtrasada(demanda)) }))
    .sort((a, b) => a.grupo - b.grupo || (a.demanda.prazoEtapaAtual ?? "9999").localeCompare(b.demanda.prazoEtapaAtual ?? "9999") || b.demanda.numeroOperacional - a.demanda.numeroOperacional)
    .map((item) => item.demanda);
}

// ── projetos com tarefas ─────────────────────────────────────────────────────────────────────────────────────

export type ProjetoComTarefas = {
  projeto: Projeto;
  /** calculado sobre TODAS as tarefas do projeto no escopo do usuário (filtros nunca alteram o cabeçalho) */
  resumo: ResumoProjeto;
  tarefas: Demanda[];
};

export function montarProjetos(projetos: readonly Projeto[], demandas: readonly Demanda[], estaAtrasada: (demanda: Demanda) => boolean): ProjetoComTarefas[] {
  const porProjeto = new Map<string, Demanda[]>();
  for (const demanda of demandas) {
    if (!demanda.projetoId) continue;
    porProjeto.set(demanda.projetoId, [...(porProjeto.get(demanda.projetoId) ?? []), demanda]);
  }
  return projetos
    .map((projeto) => {
      const doProjeto = porProjeto.get(projeto.id) ?? [];
      return { projeto, resumo: resumoDoProjeto(doProjeto, estaAtrasada), tarefas: ordenarTarefas(doProjeto, estaAtrasada) };
    })
    .sort(compararProjetos);
}

/** Projetos com trabalho em aberto primeiro; depois mais bloqueadas+atrasadas; depois nome. (Projetos 100% concluídos ou vazios ficam por último.) */
export function compararProjetos(a: ProjetoComTarefas, b: ProjetoComTarefas): number {
  const abertoA = a.resumo.total - a.resumo.concluidas > 0 ? 0 : 1;
  const abertoB = b.resumo.total - b.resumo.concluidas > 0 ? 0 : 1;
  return (
    abertoA - abertoB ||
    b.resumo.bloqueadas + b.resumo.atrasadas - (a.resumo.bloqueadas + a.resumo.atrasadas) ||
    a.projeto.nome.localeCompare(b.projeto.nome, "pt-BR")
  );
}

// ── filtros (sobre o que já foi carregado) ───────────────────────────────────────────────────────────────────

export type FiltrosProgresso = {
  busca: string;
  clienteId: string;
  responsavelId: string;
  departamentoId: string;
  status: DemandaStatus | "";
};

export const FILTROS_PROGRESSO_VAZIOS: FiltrosProgresso = { busca: "", clienteId: "", responsavelId: "", departamentoId: "", status: "" };

const semAcento = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

export function filtroDeTarefaAtivo(filtros: FiltrosProgresso): boolean {
  return Boolean(filtros.busca.trim() || filtros.responsavelId || filtros.departamentoId || filtros.status);
}

/**
 * Filtra LINHAS (tarefas) e projetos; o `resumo` do cabeçalho nunca muda. Busca: nome/campanha/código do projeto OU nome/identificador da tarefa (projeto que casa mostra todas as suas tarefas).
 * Responsável/departamento: casam com a tarefa (responsáveis da tarefa) OU com a etapa atual — o que a linha mostra. Cliente: do projeto. Projeto sem linha visível some quando há filtro de tarefa.
 */
export function aplicarFiltros(grupos: readonly ProjetoComTarefas[], filtros: FiltrosProgresso): ProjetoComTarefas[] {
  const busca = semAcento(filtros.busca);
  const ativo = filtroDeTarefaAtivo(filtros);
  return grupos
    .filter((grupo) => !filtros.clienteId || grupo.projeto.clienteId === filtros.clienteId)
    .map((grupo) => {
      const projetoCasa = busca ? [grupo.projeto.nome, grupo.projeto.campanha, grupo.projeto.codigoReferencia].some((campo) => semAcento(campo ?? "").includes(busca)) : false;
      const tarefas = grupo.tarefas.filter((demanda) => {
        if (busca && !projetoCasa && ![demanda.nome, demanda.identificador].some((campo) => semAcento(campo ?? "").includes(busca))) return false;
        if (filtros.status && demanda.status !== filtros.status) return false;
        if (filtros.responsavelId || filtros.departamentoId) {
          const usuarios = new Set([...demanda.usuarioResponsavelIds, ...fluxoUsuarios(demanda)]);
          const departamentos = new Set([...demanda.departamentoResponsavelIds, ...fluxoDepartamentos(demanda)]);
          if (filtros.responsavelId && !usuarios.has(filtros.responsavelId)) return false;
          if (filtros.departamentoId && !departamentos.has(filtros.departamentoId)) return false;
        }
        return true;
      });
      return { ...grupo, tarefas };
    })
    .filter((grupo) => !ativo || grupo.tarefas.length > 0 || (busca !== "" && semAcento(grupo.projeto.nome).includes(busca)));
}

function fluxoUsuarios(demanda: Demanda): string[] {
  const fluxo = fluxoDaTarefa(demanda);
  return fluxo.tipo === "workflow" ? (fluxo.atual?.usuarioResponsavelIds ?? []) : [];
}

function fluxoDepartamentos(demanda: Demanda): string[] {
  const fluxo = fluxoDaTarefa(demanda);
  return fluxo.tipo === "workflow" ? (fluxo.atual?.departamentoResponsavelIds ?? []) : [];
}
