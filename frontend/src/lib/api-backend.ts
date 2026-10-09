import { PERFIL_PARA_PERFIL_BASE, type Usuario, type UsuarioFormDraft, type UsuarioPerfilBaseApi } from "@/types/usuario";

// Reexportados: o mapeamento mora em types/usuario (puro, testável sem alias); quem já importava daqui segue funcionando.
export { PERFIL_PARA_PERFIL_BASE };
export type { UsuarioPerfilBaseApi };
import { inputLocalParaIso } from "@/lib/prazo-operacional";
import type { ArquivoCentral, ArquivosCentralFiltros } from "@/types/arquivo";
import type {
  FatiaPizza,
  RelatorioAnaliseProjeto,
  RelatorioColaboradorOpcao,
  RelatorioPecasPagina,
  RelatorioPerformanceColaborador,
  RelatorioPontoSemanal,
  SerieBarraEmpilhada,
} from "@/types/relatorios";
import type { PermissaoAdminItem, PermissaoOverride } from "@/types/permissao";
import type { GrupoCliente, GrupoClienteStatus } from "@/types/grupo-cliente";
import type { Departamento, DepartamentoFormDraft, DepartamentoStatus } from "@/types/departamento";
import type { Equipe, EquipeFormDraft, EquipeStatus } from "@/types/equipe";
import type {
  Cliente,
  ClienteContato,
  ClienteFormDraft,
  ClienteStatus,
  DocumentoTipo,
  PossivelDuplicidadeCliente,
} from "@/types/cliente";
import type {
  Fornecedor,
  FornecedorFormDraft,
  FornecedorStatus,
  PossivelDuplicidadeFornecedor,
} from "@/types/fornecedor";
import type { Projeto, ProjetoFormDraft, ProjetoPrioridade, ProjetoStatus } from "@/types/projeto";
import type {
  ProjetoModeloCampanhaSnapshot,
  ProjetoModeloCampanhaUpdateDraft,
} from "@/types/projeto-modelo-campanha";
import type {
  Demanda,
  DemandaArquivo,
  DemandaChecklistItem,
  DemandaComentario,
  DemandaDiretorio,
  DemandaEstatisticas,
  DemandaFormDraft,
  DemandaHistoricoEvento,
  DemandaPrioridade,
  DemandaStatus,
  DemandaStatusEditavel,
  DemandaWorkflowEtapa,
  DemandaWorkflowEtapaStatus,
} from "@/types/demanda";
import type {
  WorkflowModelo,
  WorkflowModeloDiretorioItem,
  WorkflowModeloEtapa,
  WorkflowModeloFormDraft,
  WorkflowModeloStatus,
} from "@/types/workflow-modelo";
import type { TipoTarefa, TipoTarefaDiretorioItem, TipoTarefaFormDraft, TipoTarefaStatus } from "@/types/tipo-tarefa";
import type { EstadoExpediente, RegraExpediente, RegraExpedienteUpdateDraft } from "@/types/regra-expediente";
import type { CategoriaPeca, CategoriaPecaDiretorioItem, CategoriaPecaFormDraft } from "@/types/categoria-peca";
import type { Peca, PecaDiretorioItem, PecaFormDraft } from "@/types/peca";
import type { ModeloCampanha, ModeloCampanhaDiretorioItem, ModeloCampanhaFormDraft } from "@/types/modelo-campanha";
import { itemModeloCampanhaDraftParaPayload } from "@/lib/modeloCampanhaItens";
import type { SlaRegra, SlaRegraFormDraft, SlaRegraStatus } from "@/types/sla";
import { normalizarBranding } from "@/lib/branding";
import type { Branding, PersonalizacaoUpdatePayload } from "@/types/personalizacao";
import type { CategoriaNotificacao, GrupoPrazo, NotificacoesPagina, NotificacoesResumo } from "@/types/notificacoes";
import type {
  ConfiguracaoEmailFormDraft,
  ConfiguracaoEmailRead,
  ConfiguracaoEmailTesteResultado,
} from "@/types/configuracao-email";
import type { ConfiguracaoNumeracaoTarefaRead } from "@/types/configuracao-numeracao-tarefa";

// Conflito de criação contra um registro arquivado (soft-delete permanente — ver
// docs/padrao-arquivamento.md). Distinto de um Error genérico pra a UI poder oferecer
// "Restaurar" em vez de só mostrar a mensagem de erro.
export class UsuarioArquivadoConflictError extends Error {
  usuarioArquivadoId: string;

  constructor(message: string, usuarioArquivadoId: string) {
    super(message);
    this.name = "UsuarioArquivadoConflictError";
    this.usuarioArquivadoId = usuarioArquivadoId;
  }
}

export class GrupoClienteArquivadoConflictError extends Error {
  grupoClienteArquivadoId: string;

  constructor(message: string, grupoClienteArquivadoId: string) {
    super(message);
    this.name = "GrupoClienteArquivadoConflictError";
    this.grupoClienteArquivadoId = grupoClienteArquivadoId;
  }
}

export class DepartamentoArquivadoConflictError extends Error {
  departamentoArquivadoId: string;

  constructor(message: string, departamentoArquivadoId: string) {
    super(message);
    this.name = "DepartamentoArquivadoConflictError";
    this.departamentoArquivadoId = departamentoArquivadoId;
  }
}

export class WorkflowModeloArquivadoConflictError extends Error {
  workflowModeloArquivadoId: string;

  constructor(message: string, workflowModeloArquivadoId: string) {
    super(message);
    this.name = "WorkflowModeloArquivadoConflictError";
    this.workflowModeloArquivadoId = workflowModeloArquivadoId;
  }
}

export class CategoriaPecaArquivadaConflictError extends Error {
  categoriaPecaArquivadaId: string;

  constructor(message: string, categoriaPecaArquivadaId: string) {
    super(message);
    this.name = "CategoriaPecaArquivadaConflictError";
    this.categoriaPecaArquivadaId = categoriaPecaArquivadaId;
  }
}

export class ProjetoArquivadoConflictError extends Error {
  projetoArquivadoId: string;

  constructor(message: string, projetoArquivadoId: string) {
    super(message);
    this.name = "ProjetoArquivadoConflictError";
    this.projetoArquivadoId = projetoArquivadoId;
  }
}

export class ModeloCampanhaArquivadoConflictError extends Error {
  modeloCampanhaArquivadoId: string;

  constructor(message: string, modeloCampanhaArquivadoId: string) {
    super(message);
    this.name = "ModeloCampanhaArquivadoConflictError";
    this.modeloCampanhaArquivadoId = modeloCampanhaArquivadoId;
  }
}

export class SlaRegraArquivadaConflictError extends Error {
  slaRegraArquivadaId: string;

  constructor(message: string, slaRegraArquivadaId: string) {
    super(message);
    this.name = "SlaRegraArquivadaConflictError";
    this.slaRegraArquivadaId = slaRegraArquivadaId;
  }
}

export class TipoTarefaArquivadoConflictError extends Error {
  tipoTarefaArquivadoId: string;

  constructor(message: string, tipoTarefaArquivadoId: string) {
    super(message);
    this.name = "TipoTarefaArquivadoConflictError";
    this.tipoTarefaArquivadoId = tipoTarefaArquivadoId;
  }
}

// Janela de HOJE (não a regra inteira, que agora é por dia da semana — Fase 2G.3). `null` nos
// quatro horários quando hoje não é dia útil (ver DemandaForaDeExpedienteError no backend).
export type JanelaExpediente = {
  manhaInicio: string | null;
  manhaFim: string | null;
  tardeInicio: string | null;
  tardeFim: string | null;
  toleranciaRetomadaMinutos: number;
};

/**
 * Iniciar execução fora do expediente. A **regra vive no servidor** — até a Fase 2E ela só
 * existia no Kanban, e qualquer `curl` a contornava.
 *
 * A janela vem junto do erro para a interface conseguir dizer *quando* poderá, sem repetir a
 * regra no cliente e criar uma segunda fonte da mesma verdade.
 */
export class ForaDeExpedienteError extends Error {
  expediente: JanelaExpediente;

  constructor(message: string, expediente: JanelaExpediente) {
    super(message);
    this.name = "ForaDeExpedienteError";
    this.expediente = expediente;
  }
}

// Cliente genérico pro proxy autenticado (/api/backend/**) — nunca fala direto com o
// FastAPI, nunca vê o token (fica no cookie HttpOnly, ver lib/server/backend.ts).
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    cache: "no-store",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : (detail?.message ?? data?.message);
    if (detail && typeof detail === "object" && detail.code === "USUARIO_ARQUIVADO_EXISTENTE") {
      throw new UsuarioArquivadoConflictError(message ?? "Usuário arquivado já existe", detail.usuarioArquivadoId);
    }
    if (detail && typeof detail === "object" && detail.code === "GRUPO_CLIENTE_ARQUIVADO_EXISTENTE") {
      throw new GrupoClienteArquivadoConflictError(
        message ?? "Grupo de cliente arquivado já existe",
        detail.grupoClienteArquivadoId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "DEPARTAMENTO_ARQUIVADO_EXISTENTE") {
      throw new DepartamentoArquivadoConflictError(
        message ?? "Departamento arquivado já existe",
        detail.departamentoArquivadoId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "PROJETO_ARQUIVADO_EXISTENTE") {
      throw new ProjetoArquivadoConflictError(
        message ?? "Projeto arquivado já existe",
        detail.projetoArquivadoId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "WORKFLOW_MODELO_ARQUIVADO_EXISTENTE") {
      throw new WorkflowModeloArquivadoConflictError(
        message ?? "Modelo de workflow arquivado já existe",
        detail.workflowModeloArquivadoId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "CATEGORIA_PECA_ARQUIVADA_EXISTENTE") {
      throw new CategoriaPecaArquivadaConflictError(
        message ?? "Categoria de peça arquivada já existe",
        detail.categoriaPecaArquivadaId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "MODELO_CAMPANHA_ARQUIVADO_EXISTENTE") {
      throw new ModeloCampanhaArquivadoConflictError(
        message ?? "Modelo de campanha arquivado já existe",
        detail.modeloCampanhaArquivadoId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "SLA_REGRA_ARQUIVADA_EXISTENTE") {
      throw new SlaRegraArquivadaConflictError(
        message ?? "Regra de SLA arquivada já existe",
        detail.slaRegraArquivadaId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "TIPO_TAREFA_ARQUIVADO_EXISTENTE") {
      throw new TipoTarefaArquivadoConflictError(
        message ?? "Tipo de tarefa arquivado já existe",
        detail.tipoTarefaArquivadoId,
      );
    }
    if (detail && typeof detail === "object" && detail.code === "FORA_DE_EXPEDIENTE") {
      throw new ForaDeExpedienteError(
        message ?? "Fora do expediente",
        detail.expediente as JanelaExpediente,
      );
    }
    throw new Error(message ?? `Erro ${response.status}`);
  }

  if (response.status === 204) return null as T;
  return response.json();
}

export type UsuarioReadApi = {
  id: string;
  empresaId: string;
  nome: string;
  email: string;
  perfilBase: UsuarioPerfilBaseApi;
  status: "ativo" | "inativo" | "bloqueado" | "arquivado";
  telefone: string | null;
  cpf: string | null;
  dataNascimento: string | null;
  cep: string | null;
  bairro: string | null;
  enderecoCompleto: string | null;
  cidade: string | null;
  uf: string | null;
  contatos: { id: string; nome: string; email: string; telefone: string; relacao: string }[] | null;
  departamentoId: string | null;
  cargo: string | null;
  fotoUrl: string | null;
  liderDepartamento: boolean;
  valorRecebidoMensalCentavos: number | null;
  horasTrabalhoAproximadas: number | null;
  observacoes: string | null;
  corIdentificacao: string | null;
  createdAt: string;
  updatedAt: string;
  // Só vem preenchido em GET /usuarios/me — ver docstring de UsuarioRead.permissoes no backend.
  permissoes?: string[] | null;
  // Só em GET /usuarios/me: último login bem-sucedido do próprio usuário.
  ultimoAcesso?: { em: string; ip: string | null } | null;
};

export function mapUsuarioReadToUsuario(data: UsuarioReadApi): Usuario {
  return {
    id: data.id,
    empresaId: data.empresaId,
    nome: data.nome,
    email: data.email,
    telefone: data.telefone ?? "",
    cpf: data.cpf ?? "",
    dataNascimento: data.dataNascimento ?? "",
    cep: data.cep ?? "",
    bairro: data.bairro ?? "",
    enderecoCompleto: data.enderecoCompleto ?? "",
    cidade: data.cidade ?? "",
    uf: data.uf ?? "",
    contatos: data.contatos ?? [],
    departamentoId: data.departamentoId ?? "",
    perfil: data.perfilBase,
    cargo: data.cargo ?? undefined,
    fotoUrl: data.fotoUrl ?? undefined,
    liderDepartamento: data.liderDepartamento,
    valorRecebidoMensal: data.valorRecebidoMensalCentavos != null ? data.valorRecebidoMensalCentavos / 100 : null,
    horasTrabalhoAproximadas: data.horasTrabalhoAproximadas,
    ativo: data.status === "ativo",
    observacoes: data.observacoes ?? "",
    corIdentificacao: data.corIdentificacao ?? "zinc",
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
    permissoes: data.permissoes ?? undefined,
    ultimoAcesso: data.ultimoAcesso ?? undefined,
  };
}

function draftParaPayload(draft: UsuarioFormDraft) {
  return {
    nome: draft.nome,
    email: draft.email,
    perfilBase: PERFIL_PARA_PERFIL_BASE[draft.perfil],
    telefone: draft.telefone || null,
    cpf: draft.cpf || null,
    dataNascimento: draft.dataNascimento || null,
    cep: draft.cep || null,
    bairro: draft.bairro || null,
    enderecoCompleto: draft.enderecoCompleto || null,
    cidade: draft.cidade || null,
    uf: draft.uf || null,
    contatos: draft.contatos,
    departamentoId: draft.departamentoId || null,
    cargo: draft.cargo || null,
    fotoUrl: draft.fotoUrl || null,
    liderDepartamento: draft.liderDepartamento,
    valorRecebidoMensalCentavos: draft.valorRecebidoMensal != null ? Math.round(draft.valorRecebidoMensal * 100) : null,
    horasTrabalhoAproximadas: draft.horasTrabalhoAproximadas,
    observacoes: draft.observacoes || null,
    corIdentificacao: draft.corIdentificacao || null,
  };
}

/**
 * Uma página da listagem administrativa de usuários (`GET /usuarios`), filtrada NO SERVIDOR.
 * `search` casa nome, e-mail, código e nome do departamento (sem acento, sem diferenciar maiúsculas);
 * `situacao` "ativo" = status ativo, "inativo" = tudo que não é ativo (inativo + bloqueado);
 * `departamentoId` é filtro exato. Ordem do servidor (mais recentes primeiro), `limit` até 200.
 */
export async function listUsuariosPagina(params: {
  empresaId: string;
  search?: string;
  situacao?: "ativo" | "inativo";
  /** Filtro exato de perfil técnico (ex.: "operador" para listar só Usuários). */
  perfilBase?: UsuarioPerfilBaseApi;
  departamentoId?: string;
  limit: number;
  offset: number;
}): Promise<Usuario[]> {
  const query = new URLSearchParams({
    empresaId: params.empresaId,
    limit: String(params.limit),
    offset: String(params.offset),
  });
  if (params.search) query.set("search", params.search);
  if (params.situacao) query.set("situacao", params.situacao);
  if (params.perfilBase) query.set("perfilBase", params.perfilBase);
  if (params.departamentoId) query.set("departamentoId", params.departamentoId);
  const data = await request<UsuarioReadApi[]>(`/usuarios?${query.toString()}`);
  return data.map(mapUsuarioReadToUsuario);
}

/** Agregados dos cards da tela de Usuários — empresa inteira, independentes de filtros e de página. */
export type UsuarioResumo = { total: number; ativos: number; gestao: number; departamentos: number };

export async function getResumoUsuarios(empresaId: string): Promise<UsuarioResumo> {
  return request<UsuarioResumo>(`/usuarios/resumo?empresaId=${encodeURIComponent(empresaId)}`);
}

// Autoedição do PERFIL (página Perfil / Minha Conta): só contato (telefone) e cor de identificação. Nome, e-mail,
// perfil, departamento etc. NÃO são autoeditáveis — o backend recusa com 422. A identidade vem do token.
export async function atualizarMeuPerfil(patch: { telefone?: string | null; corIdentificacao?: string }): Promise<Usuario> {
  const updated = await request<UsuarioReadApi>("/usuarios/me", { method: "PATCH", body: JSON.stringify(patch) });
  return mapUsuarioReadToUsuario(updated);
}

async function erroDaResposta(response: Response, padrao: string): Promise<Error> {
  const data = await response.json().catch(() => null);
  const detail = data?.detail;
  const message = typeof detail === "string" ? detail : (detail?.message ?? data?.message);
  return new Error(message ?? padrao);
}

// Foto de perfil — multipart (não passa por `request()`, que força JSON e destruiria o boundary).
export async function enviarMinhaFoto(arquivo: File): Promise<Usuario> {
  const formData = new FormData();
  formData.append("arquivo", arquivo);
  const response = await fetch("/api/backend/usuarios/me/avatar", { method: "POST", body: formData, cache: "no-store" });
  if (!response.ok) throw await erroDaResposta(response, "Não foi possível enviar a foto.");
  return mapUsuarioReadToUsuario(await response.json());
}

export async function removerMinhaFoto(): Promise<Usuario> {
  return mapUsuarioReadToUsuario(await request<UsuarioReadApi>("/usuarios/me/avatar", { method: "DELETE" }));
}

// Troca de senha do usuário autenticado (a mesma rota real já usada na troca inicial).
export async function alterarMinhaSenha(senhaAtual: string, novaSenha: string, confirmacaoSenha: string): Promise<void> {
  const response = await fetch("/api/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ senhaAtual, novaSenha, confirmacaoSenha }),
    cache: "no-store",
  });
  if (!response.ok) throw await erroDaResposta(response, "Não foi possível alterar a senha.");
}

// ── Central de Notificações ─────────────────────────────────────────────────────────────────────────
export async function obterResumoNotificacoes(): Promise<NotificacoesResumo> {
  return request<NotificacoesResumo>("/notificacoes/resumo");
}

export async function listarNotificacoes(params: {
  categoria?: CategoriaNotificacao;
  apenasNaoLidas?: boolean;
  limit?: number;
  offset?: number;
}): Promise<NotificacoesPagina> {
  const query = new URLSearchParams({ limit: String(params.limit ?? 50), offset: String(params.offset ?? 0) });
  if (params.categoria) query.set("categoria", params.categoria);
  if (params.apenasNaoLidas) query.set("apenasNaoLidas", "true");
  return request<NotificacoesPagina>(`/notificacoes?${query.toString()}`);
}

/** Devolve o resumo já atualizado (uma só ida ao servidor para marcar + reconciliar o badge). */
export async function marcarNotificacaoLida(eventoId: string): Promise<NotificacoesResumo> {
  return request<NotificacoesResumo>(`/notificacoes/${eventoId}/lida`, { method: "POST" });
}

export async function marcarTodasNotificacoesLidas(categoria?: CategoriaNotificacao): Promise<NotificacoesResumo> {
  return request<NotificacoesResumo>("/notificacoes/lidas", {
    method: "POST",
    body: JSON.stringify(categoria ? { categoria } : {}),
  });
}

/** Prazos da equipe: demandas abertas com prazo, no escopo REAL do usuário, paginadas no servidor. */
export async function listarPrazosEquipe(
  grupo: GrupoPrazo,
  params?: { limit?: number; offset?: number },
): Promise<{ itens: Demanda[]; total: number; limit: number; offset: number }> {
  const query = new URLSearchParams({ grupo, limit: String(params?.limit ?? 50), offset: String(params?.offset ?? 0) });
  const data = await request<{ itens: DemandaReadApi[]; total: number; limit: number; offset: number }>(
    `/notificacoes/prazos-equipe?${query.toString()}`,
  );
  return { ...data, itens: data.itens.map(mapDemandaReadToDemanda) };
}

// Projeção mínima pra seletores de responsável/membro (ver docs/padrao-arquivamento.md e
// lib/diretorioUsuarios.ts). Sem status explícito, traz todo mundo exceto arquivado —
// inclusive inativo/bloqueado, pra referências históricas continuarem resolvendo
// nome/avatar; quem monta lista de opções selecionáveis filtra "ativo" no cliente.
export type UsuarioDiretorioItem = {
  id: string;
  codigoInterno: string;
  nome: string;
  status: "ativo" | "inativo" | "bloqueado" | "arquivado";
  cargo?: string;
  departamentoId?: string;
  fotoUrl?: string;
  corIdentificacao?: string;
};

type UsuarioDiretorioApi = {
  id: string;
  codigoInterno: string;
  nome: string;
  status: "ativo" | "inativo" | "bloqueado" | "arquivado";
  cargo: string | null;
  departamentoId: string | null;
  fotoUrl: string | null;
  corIdentificacao: string | null;
};

// Normaliza null -> undefined pros componentes de UI (Avatar/MemberSelector etc.) que
// esperam `string | undefined`, não `string | null` — um só lugar, não em cada consumidor.
function mapUsuarioDiretorio(usuario: UsuarioDiretorioApi): UsuarioDiretorioItem {
  return {
    ...usuario,
    cargo: usuario.cargo ?? undefined,
    departamentoId: usuario.departamentoId ?? undefined,
    fotoUrl: usuario.fotoUrl ?? undefined,
    corIdentificacao: usuario.corIdentificacao ?? undefined,
  };
}

export async function listDiretorioUsuarios(): Promise<UsuarioDiretorioItem[]> {
  const data = await request<UsuarioDiretorioApi[]>("/usuarios/diretorio?limit=200");
  return data.map(mapUsuarioDiretorio);
}

/**
 * Uma página do diretório de usuários, filtrada NO SERVIDOR (`search` casa o nome, sem
 * diferenciar maiúsculas) — para seletores que não podem depender da lista inteira (a de
 * `listDiretorioUsuarios` termina no usuário nº 200, por nome). Mesmo diretório: todos os status,
 * sem conta de sistema, `nome ASC`, empresa do token. `limit` vai até 200 no servidor. `status`
 * (opcional, filtro exato do servidor) restringe a um status — filtrar no cliente quebraria a
 * paginação, porque uma página "cheia" deixaria de parecer cheia.
 */
export async function buscarDiretorioUsuarios(params: {
  search?: string;
  status?: UsuarioDiretorioItem["status"];
  /** Filtro exato do servidor (`departamentoId` do diretório). */
  departamentoId?: string;
  limit: number;
  offset: number;
}): Promise<UsuarioDiretorioItem[]> {
  const query = new URLSearchParams({ limit: String(params.limit), offset: String(params.offset) });
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.departamentoId) query.set("departamentoId", params.departamentoId);
  const data = await request<UsuarioDiretorioApi[]>(`/usuarios/diretorio?${query.toString()}`);
  return data.map(mapUsuarioDiretorio);
}

/**
 * Resolução em lote id -> projeção de diretório (`GET /usuarios/diretorio/por-ids`): mesma
 * autoridade e mesmos campos do diretório, qualquer status, sem conta de sistema, só a empresa
 * do token. Id inexistente/de outra empresa simplesmente não volta. O servidor aceita no máximo
 * 100 ids únicos por chamada (422 acima disso) — quem chama em volume usa `usuariosPorIds.ts`,
 * que agrupa e divide em lotes.
 */
export async function buscarDiretorioUsuariosPorIds(ids: string[]): Promise<UsuarioDiretorioItem[]> {
  const query = new URLSearchParams({ ids: ids.join(",") });
  const data = await request<UsuarioDiretorioApi[]>(`/usuarios/diretorio/por-ids?${query.toString()}`);
  return data.map(mapUsuarioDiretorio);
}

export async function criarUsuarioReal(draft: UsuarioFormDraft, empresaId: string): Promise<Usuario> {
  const created = await request<UsuarioReadApi>("/usuarios", {
    method: "POST",
    body: JSON.stringify({ ...draftParaPayload(draft), empresaId, acessoSistema: true }),
  });
  if (!draft.ativo) {
    await request(`/usuarios/${created.id}/inativar`, { method: "POST", body: JSON.stringify({}) });
    return { ...mapUsuarioReadToUsuario(created), ativo: false };
  }
  return mapUsuarioReadToUsuario(created);
}

// `perfilBaseAnterior`: o PATCH só leva `perfilBase` quando o perfil MUDOU. Reenviar o mesmo valor seria inútil e, para
// quem ainda é `admin` (legado), seria recusado — a API nunca atribui `admin`.
export async function atualizarUsuarioReal(
  usuarioId: string,
  draft: UsuarioFormDraft,
  ativoAnterior: boolean,
  perfilBaseAnterior?: UsuarioPerfilBaseApi,
): Promise<Usuario> {
  const { perfilBase, ...resto } = draftParaPayload(draft);
  const payload = perfilBaseAnterior !== undefined && perfilBaseAnterior === perfilBase ? resto : { perfilBase, ...resto };
  const updated = await request<UsuarioReadApi>(`/usuarios/${usuarioId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

  if (draft.ativo !== ativoAnterior) {
    await request(`/usuarios/${usuarioId}/${draft.ativo ? "reativar" : "inativar"}`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    return { ...mapUsuarioReadToUsuario(updated), ativo: draft.ativo };
  }

  return mapUsuarioReadToUsuario(updated);
}

// "Excluir" = arquivar (soft-delete permanente, nunca apaga a linha nem troca o ID) — ver
// docs/padrao-arquivamento.md. motivoArquivamento é obrigatório no backend.
export async function excluirUsuarioReal(usuarioId: string, motivoArquivamento: string): Promise<void> {
  await request(`/usuarios/${usuarioId}/excluir`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
}

// Restaura sempre como "inativo" — nunca reativa sozinho, mesmo que o status antes do
// arquivamento fosse outro. Reativar é uma ação separada (atualizarUsuarioReal).
export async function restaurarUsuarioReal(usuarioId: string): Promise<Usuario> {
  const restored = await request<UsuarioReadApi>(`/usuarios/${usuarioId}/restaurar`, { method: "POST" });
  return mapUsuarioReadToUsuario(restored);
}

// ---------------------------------------------------------------------------------
// Gestão administrativa de overrides — Fase 2G.10C-C1/C2. `permissao` sempre passa por
// encodeURIComponent (é uma chave "<modulo>.<acao>", vai na URL). Backend é a única
// autoridade: aqui só chamamos os 3 endpoints já validados, sem lógica de negócio.
// ---------------------------------------------------------------------------------

export async function listarPermissoesUsuario(usuarioId: string): Promise<PermissaoAdminItem[]> {
  return request<PermissaoAdminItem[]>(`/usuarios/${usuarioId}/permissoes`);
}

export async function definirPermissaoUsuario(
  usuarioId: string,
  permissao: string,
  efeito: PermissaoOverride,
  motivo?: string,
): Promise<PermissaoAdminItem> {
  return request<PermissaoAdminItem>(`/usuarios/${usuarioId}/permissoes/${encodeURIComponent(permissao)}`, {
    method: "PUT",
    body: JSON.stringify({ efeito, motivo }),
  });
}

// "Herdar" = remover a exceção individual — nunca um terceiro valor de efeito (ver
// UsuarioPermissaoService.remover_override no backend). DELETE devolve 204 (sem corpo), por
// isso quem chama refaz o GET para obter herdado/efetivo corretos da linha.
export async function herdarPermissaoUsuario(usuarioId: string, permissao: string): Promise<void> {
  await request<null>(`/usuarios/${usuarioId}/permissoes/${encodeURIComponent(permissao)}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------------------
// Grupo de Cliente
// ---------------------------------------------------------------------------------------

export type GrupoClienteReadApi = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  nome: string;
  corIdentificacao: string;
  status: GrupoClienteStatus;
  createdAt: string;
  updatedAt: string;
};

export function mapGrupoClienteReadToGrupoCliente(data: GrupoClienteReadApi): GrupoCliente {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoInterno: data.codigoInterno,
    nome: data.nome,
    corIdentificacao: data.corIdentificacao,
    status: data.status,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
  };
}

// Projeção mínima pro diretório (GET /grupos-cliente/diretorio) — inclui arquivados de
// propósito, pra vínculos já existentes continuarem resolvendo nome/cor (ver
// lib/diretorioGruposCliente.ts e lib/referencias.ts). Quem monta uma lista de opções
// selecionáveis nova filtra `status === "ativo"` no cliente.
export type GrupoClienteDiretorioItem = {
  id: string;
  codigoInterno: string;
  nome: string;
  corIdentificacao: string;
  status: GrupoClienteStatus;
};

export async function listDiretorioGruposCliente(): Promise<GrupoClienteDiretorioItem[]> {
  return request<GrupoClienteDiretorioItem[]>("/grupos-cliente/diretorio");
}

export async function criarGrupoClienteReal(nome: string, corIdentificacao: string): Promise<GrupoCliente> {
  const created = await request<GrupoClienteReadApi>("/grupos-cliente", {
    method: "POST",
    body: JSON.stringify({ nome, corIdentificacao }),
  });
  return mapGrupoClienteReadToGrupoCliente(created);
}

export async function atualizarGrupoClienteReal(
  grupoId: string,
  patch: { nome?: string; corIdentificacao?: string },
): Promise<GrupoCliente> {
  const updated = await request<GrupoClienteReadApi>(`/grupos-cliente/${grupoId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  return mapGrupoClienteReadToGrupoCliente(updated);
}

// "Excluir" = arquivar (soft-delete permanente, nunca apaga a linha) — ver
// docs/padrao-arquivamento.md. motivoArquivamento é obrigatório no backend.
export async function arquivarGrupoClienteReal(grupoId: string, motivoArquivamento: string): Promise<GrupoCliente> {
  const arquivado = await request<GrupoClienteReadApi>(`/grupos-cliente/${grupoId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapGrupoClienteReadToGrupoCliente(arquivado);
}

export async function restaurarGrupoClienteReal(grupoId: string): Promise<GrupoCliente> {
  const restaurado = await request<GrupoClienteReadApi>(`/grupos-cliente/${grupoId}/restaurar`, { method: "POST" });
  return mapGrupoClienteReadToGrupoCliente(restaurado);
}

// ---------------------------------------------------------------------------------------
// Departamento
// ---------------------------------------------------------------------------------------

type DepartamentoReadApi = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  descricao: string | null;
  responsavelUsuarioId: string | null;
  corIdentificacao: string;
  status: DepartamentoStatus;
  createdAt: string;
  updatedAt: string;
};

function mapDepartamentoReadToDepartamento(data: DepartamentoReadApi): Departamento {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoInterno: data.codigoInterno,
    codigoReferencia: data.codigoReferencia,
    anoReferencia: data.anoReferencia,
    sequencialReferencia: data.sequencialReferencia,
    nome: data.nome,
    descricao: data.descricao ?? "",
    responsavelId: data.responsavelUsuarioId ?? "",
    corIdentificacao: data.corIdentificacao,
    status: data.status,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
  };
}

function departamentoDraftParaPayload(draft: DepartamentoFormDraft) {
  return {
    nome: draft.nome,
    corIdentificacao: draft.corIdentificacao,
    descricao: draft.descricao || null,
    responsavelUsuarioId: draft.responsavelId || null,
  };
}

/** Projeção mínima para seletores — inclui arquivados, para resolver referências antigas. */
export type DepartamentoDiretorioItem = {
  id: string;
  codigoInterno: string;
  codigoReferencia: string;
  sequencialReferencia: number;
  nome: string;
  corIdentificacao: string;
  status: DepartamentoStatus;
  /** Usado por escopo-operacional.ts para resolver "head" do departamento. */
  responsavelUsuarioId: string | null;
};

export async function listDiretorioDepartamentos(): Promise<DepartamentoDiretorioItem[]> {
  return request<DepartamentoDiretorioItem[]>("/departamentos/diretorio");
}

export async function listDepartamentosReais(params?: { status?: string; search?: string }): Promise<Departamento[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  const data = await request<DepartamentoReadApi[]>(`/departamentos?${query.toString()}`);
  return data.map(mapDepartamentoReadToDepartamento);
}

export async function criarDepartamentoReal(draft: DepartamentoFormDraft): Promise<Departamento> {
  const criado = await request<DepartamentoReadApi>("/departamentos", {
    method: "POST",
    body: JSON.stringify(departamentoDraftParaPayload(draft)),
  });
  // status só é aceito no PATCH — criar sempre nasce ativo.
  if (draft.status === "inativo") {
    return atualizarDepartamentoReal(criado.id, draft);
  }
  return mapDepartamentoReadToDepartamento(criado);
}

export async function atualizarDepartamentoReal(
  departamentoId: string,
  draft: DepartamentoFormDraft,
): Promise<Departamento> {
  const atualizado = await request<DepartamentoReadApi>(`/departamentos/${departamentoId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...departamentoDraftParaPayload(draft), status: draft.status }),
  });
  return mapDepartamentoReadToDepartamento(atualizado);
}

// "Excluir" = arquivar (soft-delete permanente) — ver docs/padrao-arquivamento.md.
export async function arquivarDepartamentoReal(
  departamentoId: string,
  motivoArquivamento: string,
): Promise<Departamento> {
  const arquivado = await request<DepartamentoReadApi>(`/departamentos/${departamentoId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapDepartamentoReadToDepartamento(arquivado);
}

export async function restaurarDepartamentoReal(departamentoId: string): Promise<Departamento> {
  const restaurado = await request<DepartamentoReadApi>(`/departamentos/${departamentoId}/restaurar`, {
    method: "POST",
  });
  return mapDepartamentoReadToDepartamento(restaurado);
}

// ---------------------------------------------------------------------------------------
// Equipe
// ---------------------------------------------------------------------------------------

type EquipeReadApi = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  descricao: string | null;
  departamentoId: string | null;
  liderUsuarioId: string | null;
  membroIds: string[];
  corIdentificacao: string;
  status: EquipeStatus;
  createdAt: string;
  updatedAt: string;
};

function mapEquipeReadToEquipe(data: EquipeReadApi): Equipe {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoInterno: data.codigoInterno,
    codigoReferencia: data.codigoReferencia,
    anoReferencia: data.anoReferencia,
    sequencialReferencia: data.sequencialReferencia,
    nome: data.nome,
    descricao: data.descricao ?? "",
    departamentoId: data.departamentoId,
    liderId: data.liderUsuarioId ?? "",
    membroIds: data.membroIds,
    corIdentificacao: data.corIdentificacao,
    status: data.status,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
  };
}

function equipeDraftParaPayload(draft: EquipeFormDraft) {
  return {
    nome: draft.nome,
    corIdentificacao: draft.corIdentificacao,
    descricao: draft.descricao || null,
    departamentoId: draft.departamentoId || null,
    liderUsuarioId: draft.liderId || null,
    membroIds: draft.membroIds,
  };
}

export type EquipeDiretorioItem = {
  id: string;
  codigoInterno: string;
  codigoReferencia: string;
  sequencialReferencia: number;
  nome: string;
  corIdentificacao: string;
  status: EquipeStatus;
  departamentoId: string | null;
  /** Composição atual — usada pelo escopo "minha equipe" nas telas operacionais. */
  membroIds: string[];
};

export async function listDiretorioEquipes(): Promise<EquipeDiretorioItem[]> {
  return request<EquipeDiretorioItem[]>("/equipes/diretorio");
}

export async function listEquipesReais(params?: { status?: string; search?: string }): Promise<Equipe[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  const data = await request<EquipeReadApi[]>(`/equipes?${query.toString()}`);
  return data.map(mapEquipeReadToEquipe);
}

export async function criarEquipeReal(draft: EquipeFormDraft): Promise<Equipe> {
  const criada = await request<EquipeReadApi>("/equipes", {
    method: "POST",
    body: JSON.stringify(equipeDraftParaPayload(draft)),
  });
  if (draft.status === "inativo") {
    return atualizarEquipeReal(criada.id, draft);
  }
  return mapEquipeReadToEquipe(criada);
}

export async function atualizarEquipeReal(equipeId: string, draft: EquipeFormDraft): Promise<Equipe> {
  const atualizada = await request<EquipeReadApi>(`/equipes/${equipeId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...equipeDraftParaPayload(draft), status: draft.status }),
  });
  return mapEquipeReadToEquipe(atualizada);
}

export async function arquivarEquipeReal(equipeId: string, motivoArquivamento: string): Promise<Equipe> {
  const arquivada = await request<EquipeReadApi>(`/equipes/${equipeId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapEquipeReadToEquipe(arquivada);
}

export async function restaurarEquipeReal(equipeId: string): Promise<Equipe> {
  const restaurada = await request<EquipeReadApi>(`/equipes/${equipeId}/restaurar`, { method: "POST" });
  return mapEquipeReadToEquipe(restaurada);
}

// =====================================================================================
// Cliente — primeira entidade comercial real (Fase 2B).
//
// Nome e documento NÃO são identidade: filiais homônimas com CNPJ distinto e
// empreendimentos distintos sob o mesmo CNPJ são cadastros legítimos. Coincidência devolve
// `possiveisDuplicidades` junto do 201/200 — informativo, nunca bloqueio.
// Ver docs/padrao-entidades-externas.md.
// =====================================================================================

type ClienteReadApi = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  razaoSocial: string | null;
  tipoDocumento: DocumentoTipo;
  documento: string | null;
  status: ClienteStatus;
  email: string | null;
  whatsapp: string | null;
  cep: string | null;
  bairro: string | null;
  enderecoCompleto: string | null;
  cidade: string | null;
  uf: string | null;
  segmento: string | null;
  origem: string | null;
  responsavelComercialId: string | null;
  clienteReferencial: boolean;
  avisarConclusaoPorEmail: boolean;
  feeMensalCentavos: number | null;
  horasContratadasMes: number | null;
  observacoes: string | null;
  corIdentificacao: string;
  logoUrl: string | null;
  contatos: ClienteContato[];
  grupoClienteIds: string[];
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  motivoArquivamento: string | null;
  possiveisDuplicidades: PossivelDuplicidadeCliente[];
};

function mapClienteReadToCliente(data: ClienteReadApi): Cliente {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoInterno: data.codigoInterno,
    codigoReferencia: data.codigoReferencia,
    anoReferencia: data.anoReferencia,
    sequencialReferencia: data.sequencialReferencia,
    logoUrl: data.logoUrl ?? undefined,
    tipoDocumento: data.tipoDocumento,
    documento: data.documento ?? "",
    nome: data.nome,
    razaoSocial: data.razaoSocial ?? "",
    email: data.email ?? "",
    whatsapp: data.whatsapp ?? "",
    cep: data.cep ?? "",
    bairro: data.bairro ?? "",
    enderecoCompleto: data.enderecoCompleto ?? "",
    cidade: data.cidade ?? "",
    uf: data.uf ?? "",
    segmento: data.segmento ?? "",
    grupoClienteIds: data.grupoClienteIds ?? [],
    origem: data.origem ?? "",
    status: data.status,
    responsavelComercialId: data.responsavelComercialId ?? "",
    clienteReferencial: data.clienteReferencial,
    contatos: data.contatos ?? [],
    avisarConclusaoPorEmail: data.avisarConclusaoPorEmail,
    feeMensalCentavos: data.feeMensalCentavos,
    horasContratadasMes: data.horasContratadasMes,
    observacoes: data.observacoes ?? "",
    corIdentificacao: data.corIdentificacao,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
    arquivadoAt: data.arquivadoAt,
    motivoArquivamento: data.motivoArquivamento,
    possiveisDuplicidades: data.possiveisDuplicidades ?? [],
  };
}

function clienteDraftParaPayload(draft: ClienteFormDraft) {
  return {
    nome: draft.nome,
    tipoDocumento: draft.tipoDocumento,
    corIdentificacao: draft.corIdentificacao,
    razaoSocial: draft.razaoSocial || null,
    documento: draft.documento || null,
    email: draft.email || null,
    whatsapp: draft.whatsapp || null,
    cep: draft.cep || null,
    bairro: draft.bairro || null,
    enderecoCompleto: draft.enderecoCompleto || null,
    cidade: draft.cidade || null,
    uf: draft.uf || null,
    segmento: draft.segmento || null,
    origem: draft.origem || null,
    responsavelComercialId: draft.responsavelComercialId || null,
    clienteReferencial: draft.clienteReferencial,
    avisarConclusaoPorEmail: draft.avisarConclusaoPorEmail,
    feeMensalCentavos: draft.feeMensalCentavos,
    horasContratadasMes: draft.horasContratadasMes,
    observacoes: draft.observacoes || null,
    logoUrl: draft.logoUrl || null,
    contatos: draft.contatos,
    grupoClienteIds: draft.grupoClienteIds,
  };
}

/**
 * Projeção para seletores — inclui arquivados, para resolver referências antigas.
 *
 * Carrega `email`, `contatos` e `avisarConclusaoPorEmail` porque o aviso de conclusão de
 * demanda (DemandaConclusaoBanner) precisa saber quem recebe a entrega, e ele aparece para
 * qualquer pessoa que conclui uma tarefa — não só para admin/gestor, que são os únicos com
 * acesso a `GET /clientes/{id}`. São os mesmos contatos que o operador já usa ao trabalhar
 * a demanda; dado financeiro (fee, horas contratadas) continua fora daqui.
 */
export type ClienteDiretorioItem = {
  id: string;
  codigoInterno: string;
  codigoReferencia: string;
  sequencialReferencia: number;
  nome: string;
  corIdentificacao: string;
  status: ClienteStatus;
  grupoClienteIds: string[];
  email: string | null;
  contatos: ClienteContato[];
  avisarConclusaoPorEmail: boolean;
  /** Usado por escopo-operacional.ts para o escopo "minhas demandas" do Atendimento. */
  responsavelComercialId: string | null;
};

export async function listDiretorioClientes(): Promise<ClienteDiretorioItem[]> {
  return request<ClienteDiretorioItem[]>("/clientes/diretorio");
}

export async function listClientesReais(params?: {
  status?: string;
  search?: string;
  grupoClienteId?: string;
}): Promise<Cliente[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  if (params?.grupoClienteId) query.set("grupoClienteId", params.grupoClienteId);
  const data = await request<ClienteReadApi[]>(`/clientes?${query.toString()}`);
  return data.map(mapClienteReadToCliente);
}

export async function criarClienteReal(draft: ClienteFormDraft): Promise<Cliente> {
  const criado = await request<ClienteReadApi>("/clientes", {
    method: "POST",
    body: JSON.stringify(clienteDraftParaPayload(draft)),
  });
  // `status` só é aceito no PATCH — criar sempre nasce ativo. O PATCH seguinte preserva os
  // `possiveisDuplicidades` já detectados na criação, que é quando eles importam.
  if (draft.status !== "ativo") {
    const atualizado = await atualizarClienteReal(criado.id, draft);
    return { ...atualizado, possiveisDuplicidades: criado.possiveisDuplicidades ?? [] };
  }
  return mapClienteReadToCliente(criado);
}

export async function atualizarClienteReal(clienteId: string, draft: ClienteFormDraft): Promise<Cliente> {
  const atualizado = await request<ClienteReadApi>(`/clientes/${clienteId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...clienteDraftParaPayload(draft), status: draft.status }),
  });
  return mapClienteReadToCliente(atualizado);
}

// "Excluir" = arquivar (soft-delete permanente) — ver docs/padrao-arquivamento.md.
export async function arquivarClienteReal(clienteId: string, motivoArquivamento: string): Promise<Cliente> {
  const arquivado = await request<ClienteReadApi>(`/clientes/${clienteId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapClienteReadToCliente(arquivado);
}

export async function restaurarClienteReal(clienteId: string): Promise<Cliente> {
  const restaurado = await request<ClienteReadApi>(`/clientes/${clienteId}/restaurar`, {
    method: "POST",
  });
  return mapClienteReadToCliente(restaurado);
}

// =====================================================================================
// Fornecedor — último cadastro comercial a sair do mock (Fase 2C).
//
// Mesmo contrato de Cliente: nome e documento NÃO são identidade, coincidência devolve
// `possiveisDuplicidades` junto do 201/200 — informativo, nunca bloqueio.
// Ver docs/padrao-entidades-externas.md.
//
// Diferença relevante: `/fornecedores/diretorio` NÃO inclui arquivados. Cliente inclui
// porque Demanda e Projeto guardam referências históricas a resolver; nenhum domínio
// referencia fornecedor, então o diretório só serve para montar opções de vínculo novo — e
// arquivado nunca é uma opção nova.
// =====================================================================================

type FornecedorReadApi = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  tipoDocumento: DocumentoTipo;
  documento: string | null;
  status: FornecedorStatus;
  categoria: string | null;
  contatoNome: string | null;
  email: string | null;
  whatsapp: string | null;
  site: string | null;
  cep: string | null;
  bairro: string | null;
  enderecoCompleto: string | null;
  cidade: string | null;
  uf: string | null;
  observacoes: string | null;
  corIdentificacao: string;
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  motivoArquivamento: string | null;
  possiveisDuplicidades: PossivelDuplicidadeFornecedor[];
};

function mapFornecedorReadToFornecedor(data: FornecedorReadApi): Fornecedor {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoInterno: data.codigoInterno,
    codigoReferencia: data.codigoReferencia,
    anoReferencia: data.anoReferencia,
    sequencialReferencia: data.sequencialReferencia,
    tipoDocumento: data.tipoDocumento,
    documento: data.documento ?? "",
    nome: data.nome,
    categoria: data.categoria ?? "",
    contatoNome: data.contatoNome ?? "",
    email: data.email ?? "",
    whatsapp: data.whatsapp ?? "",
    site: data.site ?? "",
    cep: data.cep ?? "",
    bairro: data.bairro ?? "",
    enderecoCompleto: data.enderecoCompleto ?? "",
    cidade: data.cidade ?? "",
    uf: data.uf ?? "",
    status: data.status,
    observacoes: data.observacoes ?? "",
    corIdentificacao: data.corIdentificacao,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
    arquivadoAt: data.arquivadoAt,
    motivoArquivamento: data.motivoArquivamento,
    possiveisDuplicidades: data.possiveisDuplicidades ?? [],
  };
}

function fornecedorDraftParaPayload(draft: FornecedorFormDraft) {
  return {
    nome: draft.nome,
    tipoDocumento: draft.tipoDocumento,
    corIdentificacao: draft.corIdentificacao,
    status: draft.status,
    documento: draft.documento || null,
    categoria: draft.categoria || null,
    contatoNome: draft.contatoNome || null,
    email: draft.email || null,
    whatsapp: draft.whatsapp || null,
    site: draft.site || null,
    cep: draft.cep || null,
    bairro: draft.bairro || null,
    enderecoCompleto: draft.enderecoCompleto || null,
    cidade: draft.cidade || null,
    uf: draft.uf || null,
    observacoes: draft.observacoes || null,
  };
}

/** Projeção para seletores de vínculo. Só ativos e inativos — ver bloco acima. */
export type FornecedorDiretorioItem = {
  id: string;
  codigoInterno: string;
  codigoReferencia: string;
  sequencialReferencia: number;
  nome: string;
  categoria: string | null;
  corIdentificacao: string;
  status: FornecedorStatus;
};

export async function listDiretorioFornecedores(): Promise<FornecedorDiretorioItem[]> {
  return request<FornecedorDiretorioItem[]>("/fornecedores/diretorio");
}

export async function listFornecedoresReais(params?: {
  status?: string;
  search?: string;
}): Promise<Fornecedor[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  const data = await request<FornecedorReadApi[]>(`/fornecedores?${query.toString()}`);
  return data.map(mapFornecedorReadToFornecedor);
}

// Diferente de Cliente, `status` é aceito na criação (o cadastro pode nascer inativo), então
// não há PATCH de acerto logo em seguida.
export async function criarFornecedorReal(draft: FornecedorFormDraft): Promise<Fornecedor> {
  const criado = await request<FornecedorReadApi>("/fornecedores", {
    method: "POST",
    body: JSON.stringify(fornecedorDraftParaPayload(draft)),
  });
  return mapFornecedorReadToFornecedor(criado);
}

export async function atualizarFornecedorReal(
  fornecedorId: string,
  draft: FornecedorFormDraft,
): Promise<Fornecedor> {
  const atualizado = await request<FornecedorReadApi>(`/fornecedores/${fornecedorId}`, {
    method: "PATCH",
    body: JSON.stringify(fornecedorDraftParaPayload(draft)),
  });
  return mapFornecedorReadToFornecedor(atualizado);
}

// "Excluir" = arquivar (soft-delete permanente) — ver docs/padrao-arquivamento.md.
export async function arquivarFornecedorReal(
  fornecedorId: string,
  motivoArquivamento: string,
): Promise<Fornecedor> {
  const arquivado = await request<FornecedorReadApi>(`/fornecedores/${fornecedorId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapFornecedorReadToFornecedor(arquivado);
}

export async function restaurarFornecedorReal(fornecedorId: string): Promise<Fornecedor> {
  const restaurado = await request<FornecedorReadApi>(`/fornecedores/${fornecedorId}/restaurar`, {
    method: "POST",
  });
  return mapFornecedorReadToFornecedor(restaurado);
}

// =====================================================================================
// Projeto — o trabalho contratado, sob o qual as demandas acontecem (Fase 2D).
//
// Unicidade **por cliente**: dois "Campanha de Natal" para clientes diferentes são
// legítimos; dois para o mesmo cliente devolvem 409. Se o conflito for com um projeto
// arquivado, o 409 traz `projetoArquivadoId` para a UI oferecer restaurar
// (ProjetoArquivadoConflictError abaixo) — mesmo contrato de Usuário e Grupo de Cliente.
//
// =====================================================================================

type ProjetoReadApi = {
  id: string;
  empresaId: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  campanha: string | null;
  descricao: string | null;
  resumo: string | null;
  status: ProjetoStatus;
  prioridade: ProjetoPrioridade;
  clienteId: string | null;
  dataInicio: string | null;
  dataFimPrevista: string | null;
  // `modeloCampanhaId`/`modeloCampanha` (JSONB legado) removidos fisicamente do backend na
  // Fase 2G.5D — nunca existiram neste tipo desde a 2G.5C3. A UI lê o snapshot relacional via
  // `getProjetoModeloCampanhaSnapshot`, nunca um campo de Projeto.
  responsavelIds: string[];
  departamentoResponsavelIds: string[];
  equipe: { usuarioId: string; funcao: string | null }[];
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  motivoArquivamento: string | null;
};

function mapProjetoReadToProjeto(data: ProjetoReadApi): Projeto {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoReferencia: data.codigoReferencia,
    anoReferencia: data.anoReferencia,
    sequencialReferencia: data.sequencialReferencia,
    nome: data.nome,
    campanha: data.campanha ?? "",
    descricao: data.descricao ?? "",
    resumo: data.resumo ?? "",
    status: data.status,
    prioridade: data.prioridade,
    clienteId: data.clienteId ?? "",
    dataInicio: data.dataInicio ?? "",
    dataFimPrevista: data.dataFimPrevista ?? "",
    responsavelIds: data.responsavelIds ?? [],
    departamentoResponsavelIds: data.departamentoResponsavelIds ?? [],
    equipe: (data.equipe ?? []).map((m) => ({ usuarioId: m.usuarioId, funcao: m.funcao ?? "" })),
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
    arquivadoAt: data.arquivadoAt,
    motivoArquivamento: data.motivoArquivamento,
  };
}

function projetoDraftParaPayload(draft: ProjetoFormDraft) {
  return {
    nome: draft.nome,
    status: draft.status,
    prioridade: draft.prioridade,
    campanha: draft.campanha || null,
    descricao: draft.descricao || null,
    resumo: draft.resumo || null,
    clienteId: draft.clienteId || null,
    dataInicio: draft.dataInicio || null,
    dataFimPrevista: draft.dataFimPrevista || null,
    // `modeloCampanha`/`modeloCampanhaId` deliberadamente fora do payload novo — ver
    // types/projeto.ts. Nunca mandar `[]`/`null` "pra limpar": o campo simplesmente não existe
    // mais no draft.
    responsavelIds: draft.responsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
    equipe: draft.equipe.map((m) => ({ usuarioId: m.usuarioId, funcao: m.funcao || null })),
  };
}

/** Projeção mínima pra seleção operacional (Nova Tarefa). Inclui todos os status — igual ao
 * diretório de Departamento/Cliente, resolve referência histórica de projetos já concluídos
 * ou arquivados que uma Demanda antiga ainda aponte. */
export type ProjetoDiretorioItem = {
  id: string;
  codigoReferencia: string;
  sequencialReferencia: number;
  nome: string;
  status: ProjetoStatus;
  clienteId: string | null;
};

export async function listDiretorioProjetos(): Promise<ProjetoDiretorioItem[]> {
  return request<ProjetoDiretorioItem[]>("/projetos/diretorio");
}

export async function listProjetosReais(params?: {
  status?: string;
  search?: string;
  clienteId?: string;
  departamentoId?: string;
}): Promise<Projeto[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  if (params?.clienteId) query.set("clienteId", params.clienteId);
  if (params?.departamentoId) query.set("departamentoId", params.departamentoId);
  const data = await request<ProjetoReadApi[]>(`/projetos?${query.toString()}`);
  return data.map(mapProjetoReadToProjeto);
}

export async function criarProjetoReal(draft: ProjetoFormDraft): Promise<Projeto> {
  const criado = await request<ProjetoReadApi>("/projetos", {
    method: "POST",
    body: JSON.stringify(projetoDraftParaPayload(draft)),
  });
  return mapProjetoReadToProjeto(criado);
}

export async function atualizarProjetoReal(projetoId: string, draft: ProjetoFormDraft): Promise<Projeto> {
  const atualizado = await request<ProjetoReadApi>(`/projetos/${projetoId}`, {
    method: "PATCH",
    body: JSON.stringify(projetoDraftParaPayload(draft)),
  });
  return mapProjetoReadToProjeto(atualizado);
}

// "Excluir" = arquivar (soft-delete permanente) — ver docs/padrao-arquivamento.md.
export async function arquivarProjetoReal(projetoId: string, motivoArquivamento: string): Promise<Projeto> {
  const arquivado = await request<ProjetoReadApi>(`/projetos/${projetoId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapProjetoReadToProjeto(arquivado);
}

export async function restaurarProjetoReal(projetoId: string): Promise<Projeto> {
  const restaurado = await request<ProjetoReadApi>(`/projetos/${projetoId}/restaurar`, { method: "POST" });
  return mapProjetoReadToProjeto(restaurado);
}

// =====================================================================================
// Demanda — a unidade de trabalho da operação; a interface chama de Tarefa (Fase 2E.1).
//
// Primeiro domínio OPERACIONAL: ao contrário dos cadastros, é lido por qualquer autenticado,
// e **o que cada um enxerga é decidido no servidor**. `listDemandasReais()` sem parâmetro já
// vem escopado; `escopo` só estreita. Pedir um escopo sem direito devolve 403 — não uma lista
// vazia, que esconderia o erro de permissão.
//
// Acesso direto por UUID também é escopado: `getDemandaReal` de uma demanda fora do escopo
// devolve 404, mesmo sendo da mesma empresa.
//
// **Sem unicidade de nome**: duas tarefas "Ajuste banner" no mesmo dia são rotina, então não
// existe conflito de duplicidade aqui — nenhum `DemandaArquivadaConflictError`.
// =====================================================================================

export type DemandaEscopo = "meus" | "meu-departamento" | "atendimento" | "pauta";

type DemandaWorkflowEtapaReadApi = {
  id: string;
  ordem: number;
  nome: string;
  tipo: DemandaWorkflowEtapa["tipo"];
  quantidadeAntesDeadline: number;
  unidadePrazo: DemandaWorkflowEtapa["unidadePrazo"];
  status: DemandaWorkflowEtapaStatus;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
};

type DemandaReadApi = {
  id: string;
  empresaId: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  numeroOperacional: number;
  nome: string;
  pit: string | null;
  briefing: string | null;
  status: DemandaStatus;
  prioridade: DemandaPrioridade;
  sinalizada: boolean;
  motivoBloqueio: string | null;
  clienteId: string | null;
  projetoId: string | null;
  criadoPorUsuarioId: string | null;
  workflowModeloId: string | null;
  workflowEtapas: DemandaWorkflowEtapaReadApi[];
  etapaAtualId: string | null;
  dataInicio: string | null;
  dataFimPrevista: string | null;
  prazoEtapaAtual: string | null;
  enviadoClienteEm: string | null;
  prazoRetornoCliente: string | null;
  retornoRecebidoEm: string | null;
  emailConclusaoEnviado: boolean;
  emailConclusaoData: string | null;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  arquivadoPorUsuarioId: string | null;
  motivoArquivamento: string | null;
  restauradoAt: string | null;
  restauradoPorUsuarioId: string | null;
  statusAnteriorArquivamento: DemandaStatus | null;
};

// `workflowEtapas`/`etapaAtualId` já são reais (Fase 2E.2) — materializados a partir de um
// WorkflowModelo na criação, `etapaAtualId` derivado no servidor. `checklist`/`arquivos`
// (Fase 2E.3) saíram deste payload — têm endpoint dedicado agora (ver
// listChecklistDemanda/listArquivosDemanda abaixo), buscados sob demanda ao abrir a Demanda.
// `comentarios`/`historico` continuam fixados vazios: não há tabela por trás deles ainda.
function mapDemandaReadToDemanda(data: DemandaReadApi): Demanda {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoReferencia: data.codigoReferencia,
    anoReferencia: data.anoReferencia,
    sequencialReferencia: data.sequencialReferencia,
    numeroOperacional: data.numeroOperacional,
    nome: data.nome,
    pit: data.pit,
    briefing: data.briefing,
    status: data.status,
    prioridade: data.prioridade,
    sinalizada: data.sinalizada,
    motivoBloqueio: data.motivoBloqueio,
    clienteId: data.clienteId,
    projetoId: data.projetoId,
    criadoPorUsuarioId: data.criadoPorUsuarioId,
    workflowModeloId: data.workflowModeloId,
    dataInicio: data.dataInicio,
    dataFimPrevista: data.dataFimPrevista,
    prazoEtapaAtual: data.prazoEtapaAtual,
    enviadoClienteEm: data.enviadoClienteEm,
    prazoRetornoCliente: data.prazoRetornoCliente,
    retornoRecebidoEm: data.retornoRecebidoEm,
    emailConclusaoEnviado: data.emailConclusaoEnviado,
    emailConclusaoData: data.emailConclusaoData,
    usuarioResponsavelIds: data.usuarioResponsavelIds ?? [],
    departamentoResponsavelIds: data.departamentoResponsavelIds ?? [],
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
    arquivadoAt: data.arquivadoAt,
    arquivadoPorUsuarioId: data.arquivadoPorUsuarioId,
    motivoArquivamento: data.motivoArquivamento,
    restauradoAt: data.restauradoAt,
    restauradoPorUsuarioId: data.restauradoPorUsuarioId,
    statusAnteriorArquivamento: data.statusAnteriorArquivamento,
    workflowEtapas: data.workflowEtapas.map((etapa) => ({
      id: etapa.id,
      nome: etapa.nome,
      ordem: etapa.ordem,
      tipo: etapa.tipo,
      quantidadeAntesDeadline: etapa.quantidadeAntesDeadline,
      unidadePrazo: etapa.unidadePrazo,
      status: etapa.status,
      usuarioResponsavelIds: etapa.usuarioResponsavelIds,
      departamentoResponsavelIds: etapa.departamentoResponsavelIds,
    })),
    etapaAtualId: data.etapaAtualId,
  };
}

// `workflowEtapas`/`etapaAtualId` nunca entram no payload — não há endpoint de transição de
// etapa nesta fase, e enviá-los devolveria 422 por `extra="forbid"`. `workflowModeloId` só é
// aceito na CRIAÇÃO (materializa as etapas do template) — ver `criarDemandaReal`, que o
// adiciona por fora deste payload base pra não vazar pro PATCH de edição, que rejeitaria.
function demandaDraftParaPayload(draft: DemandaFormDraft) {
  return {
    nome: draft.nome,
    status: draft.status,
    prioridade: draft.prioridade,
    pit: draft.pit || null,
    briefing: draft.briefing || null,
    clienteId: draft.clienteId || null,
    projetoId: draft.projetoId || null,
    dataFimPrevista: draft.dataFimPrevista || null,
    // Prazo operacional (instante): do `datetime-local` local para ISO com fuso. Ausente (`undefined`) = não mexe no campo.
    ...(draft.prazoEtapaAtual !== undefined ? { prazoEtapaAtual: inputLocalParaIso(draft.prazoEtapaAtual) } : {}),
    usuarioResponsavelIds: draft.usuarioResponsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
  };
}

// "fila_pessoal" (Meu Dia): sessão ativa do próprio usuário, atrasadas, vencem hoje, prazo futuro, sem prazo — exige `agora`,
// `hojeInicio` e `hojeFim` (fuso local do cliente), como o resumo pessoal.
export type DemandaSort = "numero_operacional_desc" | "prazo_asc" | "sinalizada_desc" | "fila_pessoal";

// D2-B5: mesmo par de `OrigemDemanda` (lib/escopo-operacional.ts) — definido aqui de novo
// (não importado de lá) porque escopo-operacional.ts já importa DESTE arquivo; importar na
// direção contrária criaria dependência circular.
export type DemandaOrigemFiltro = "interna" | "cliente";

export async function listDemandasReais(params?: {
  status?: string;
  search?: string;
  clienteId?: string;
  projetoId?: string;
  // Aceita um único id ou uma lista separada por vírgula — o caller monta o CSV, mesma
  // convenção já usada em `status` (D2-B1). Ver PautaView para o caso de múltiplos.
  departamentoId?: string;
  escopo?: DemandaEscopo;
  // Opcionais — quem não passa continua recebendo o comportamento de sempre (limit=200,
  // offset=0). Introduzidos no D2-B1 para DemandasView paginar de verdade no servidor.
  limit?: number;
  offset?: number;
  // D2-B3: filtro de intervalo sobre `prazoEtapaAtual`, ISO com timezone (o backend recusa
  // datetime naive — ver app/api/routes/demandas.py). Usado pela Pauta.
  prazoInicio?: string;
  prazoFim?: string;
  // Default do backend é "numero_operacional_desc" — omitir preserva o comportamento de
  // todo caller existente (DemandasView, ProjetoDemandasSection).
  sort?: DemandaSort;
  // D2-B5 (MeuDepartamentoView): filtros "Colaborador" (é responsável), "Equipe" (algum
  // responsável é membro), "Prioridade" e "Origem" (derivada — cliente vinculado ou não).
  // Fase 6.1 (filtros avançados): `responsavelId`/`equipeId`/`clienteId`/`projetoId`/`prioridade` aceitam VÁRIOS valores em CSV
  // ("é um de", OR) e têm a versão `...Excluir` ("não é um de"). Só refinam: o escopo de segurança é derivado no servidor.
  responsavelId?: string;
  equipeId?: string;
  prioridade?: string;
  origem?: DemandaOrigemFiltro;
  agora?: string;
  hojeInicio?: string;
  hojeFim?: string;
  statusExcluir?: string;
  clienteIdExcluir?: string;
  projetoIdExcluir?: string;
  responsavelIdExcluir?: string;
  equipeIdExcluir?: string;
  prioridadeExcluir?: string;
  // D2-B5: período "Atrasadas" — `!finalizada && prazo IS NOT NULL && prazo < agora`,
  // mesma fórmula do resumo de Atendimento (D2-B4), agora também filtrável na lista.
  atrasada?: boolean;
  // D2-D1 (NotificationBell): `status NOT IN (concluida, cancelada)` — não reabre arquivada
  // (independente da exclusão default de arquivada, que já vale quando `status` não é
  // passado explicitamente).
  naoFinalizada?: boolean;
}): Promise<Demanda[]> {
  const query = new URLSearchParams({ limit: String(params?.limit ?? 200) });
  if (params?.offset) query.set("offset", String(params.offset));
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  if (params?.clienteId) query.set("clienteId", params.clienteId);
  if (params?.projetoId) query.set("projetoId", params.projetoId);
  if (params?.departamentoId) query.set("departamentoId", params.departamentoId);
  if (params?.escopo) query.set("escopo", params.escopo);
  if (params?.prazoInicio) query.set("prazoInicio", params.prazoInicio);
  if (params?.prazoFim) query.set("prazoFim", params.prazoFim);
  if (params?.sort) query.set("sort", params.sort);
  if (params?.responsavelId) query.set("responsavelId", params.responsavelId);
  if (params?.equipeId) query.set("equipeId", params.equipeId);
  if (params?.prioridade) query.set("prioridade", params.prioridade);
  if (params?.origem) query.set("origem", params.origem);
  if (params?.agora) query.set("agora", params.agora);
  if (params?.hojeInicio) query.set("hojeInicio", params.hojeInicio);
  if (params?.hojeFim) query.set("hojeFim", params.hojeFim);
  if (params?.statusExcluir) query.set("statusExcluir", params.statusExcluir);
  if (params?.clienteIdExcluir) query.set("clienteIdExcluir", params.clienteIdExcluir);
  if (params?.projetoIdExcluir) query.set("projetoIdExcluir", params.projetoIdExcluir);
  if (params?.responsavelIdExcluir) query.set("responsavelIdExcluir", params.responsavelIdExcluir);
  if (params?.equipeIdExcluir) query.set("equipeIdExcluir", params.equipeIdExcluir);
  if (params?.prioridadeExcluir) query.set("prioridadeExcluir", params.prioridadeExcluir);
  if (params?.atrasada) query.set("atrasada", "true");
  if (params?.naoFinalizada) query.set("naoFinalizada", "true");
  const data = await request<DemandaReadApi[]>(`/demandas?${query.toString()}`);
  return data.map(mapDemandaReadToDemanda);
}

/**
 * Meu Dia — ids das demandas em que o PRÓPRIO usuário tem uma sessão de trabalho ativa agora. Usuário e empresa vêm do token
 * (sem parâmetro). Só ids: nenhum tempo/duração.
 */
export async function listarMinhasSessoesAtivas(): Promise<string[]> {
  const resposta = await request<{ demandaIds: string[] }>("/sessoes-trabalho/minhas-ativas");
  return resposta.demandaIds;
}

/** Meu Departamento — um colaborador do departamento e o que ele tem em execução AGORA (sessão real; sem horário nem duração). */
export type MembroEquipeAgora = {
  usuarioId: string;
  nome: string;
  corIdentificacao: string | null;
  fotoUrl: string | null;
  emExecucao: Array<{ demandaId: string; numeroOperacional: number | null; nome: string | null }>;
};

/** Quem do departamento está trabalhando agora e em quê. Só o Head DESTE departamento (403 para qualquer outro). */
export async function listarEquipeAgora(departamentoId: string): Promise<MembroEquipeAgora[]> {
  const query = new URLSearchParams({ departamentoId });
  const resposta = await request<{ membros: MembroEquipeAgora[] }>(`/sessoes-trabalho/meu-departamento/agora?${query.toString()}`);
  return resposta.membros;
}

/** Pauta global — ids das demandas da empresa com sessão ativa agora (selo "em execução agora"). Sem pessoa nem tempo. */
export async function listarDemandasEmExecucaoNaPauta(): Promise<string[]> {
  const resposta = await request<{ demandaIds: string[] }>("/sessoes-trabalho/pauta/em-execucao");
  return resposta.demandaIds;
}

/**
 * Fase 7C.1 — escopo de LEITURA do detalhe de uma demanda. `"pauta"` = leitura pela Pauta global (Atendimento, Heads e Gestão veem
 * demandas de toda a empresa); o servidor valida (403 para os demais) e restringe ao tenant do token. SOMENTE LEITURA: só as
 * funções de listagem/leitura abaixo aceitam; nenhuma escrita (PATCH/POST/DELETE) envia este parâmetro.
 */
export type EscopoLeituraDemanda = "pauta";

function sufixoEscopoLeitura(escopo?: EscopoLeituraDemanda): string {
  return escopo ? `?escopo=${escopo}` : "";
}

export async function getDemandaReal(demandaId: string, escopo?: EscopoLeituraDemanda): Promise<Demanda> {
  return mapDemandaReadToDemanda(await request<DemandaReadApi>(`/demandas/${demandaId}${sufixoEscopoLeitura(escopo)}`));
}

export async function listDiretorioDemandas(): Promise<DemandaDiretorio[]> {
  return request<DemandaDiretorio[]>("/demandas/diretorio");
}

/**
 * D2-B4 — os nove indicadores de MinhasDemandasView, agregados no servidor sobre o universo
 * INTEGRAL do escopo Atendimento (nunca uma página). Quem não é Atendimento recebe 403, não
 * zeros — mesma autoridade da listagem (`GET /demandas?escopo=atendimento`).
 */
export type ResumoAtendimento = {
  criadas: number;
  naoIniciadas: number;
  emExecucao: number;
  aguardandoCliente: number;
  aguardandoAtendimento: number;
  pausadas: number;
  atrasadas: number;
  dentroDoPrazo: number;
  concluidas: number;
};

export async function getResumoAtendimento(): Promise<ResumoAtendimento> {
  return request<ResumoAtendimento>("/demandas/minhas/resumo");
}

/**
 * Cards de `DemandasStats` (tela Tarefas), agregados no servidor sobre o universo INTEGRAL do
 * escopo de quem pede — nunca `AppDataContext.demandas` (`GET /demandas?limit=200`). Sem
 * filtros: os cards nunca acompanharam a busca nem o filtro de status da tela.
 */
export async function getDemandasEstatisticas(): Promise<DemandaEstatisticas> {
  return request<DemandaEstatisticas>("/demandas/estatisticas");
}

/**
 * D2-B5 — indicadores de MeuDepartamentoView, agregados no servidor sobre o universo
 * INTEGRAL do departamento (nunca a página filtrada). Não inclui `horasConsumidas`
 * (continua vindo de `getHorasDepartamento`, lib/api.ts) nem `capacidadeDisponivel`
 * (calculável no cliente a partir de headcount + `horasUteisHoje`, sem depender de
 * Demanda). `departamentoId` é o departamento ÚNICO já resolvido por
 * `resolverHeadDepartamento` — este client não decide qual é, só recebe.
 */
export type ResumoDepartamento = {
  novas: number;
  semResponsavel: number;
  emAndamento: number;
  pausadas: number;
  aguardando: number;
  atrasadas: number;
  concluidas: number;
  horasEstimadasTotal: number;
  colaboradoresSobrecarregados: number;
};

export async function getResumoDepartamento(departamentoId: string): Promise<ResumoDepartamento> {
  const query = new URLSearchParams({ departamentoId });
  return request<ResumoDepartamento>(`/demandas/meu-departamento/resumo?${query.toString()}`);
}

/**
 * D2-D2 — os 11 indicadores do Dashboard pessoal (`/meu-dia`), agregados no servidor sobre
 * o universo INTEGRAL permitido do usuário (escopo normal + responsável N:N) — nunca as 200
 * demandas globais de `AppDataContext`. Sem restrição de perfil, ao contrário de
 * `getResumoAtendimento`/`getResumoDepartamento`.
 */
export type ResumoMinhaHome = {
  ativas: number;
  novas: number;
  andamento: number;
  pausadas: number;
  aguardando: number;
  atrasadas: number;
  concluidas: number;
  previstasHoje: number;
  previstasSemana: number;
  concluidasSemana: number;
  concluidasOntem: number;
};

/**
 * Todas as fronteiras temporais são obrigatórias e devem vir da MESMA referência de
 * `new Date()` no caller (ver DashboardView.tsx) — este client não recalcula nada, só
 * repassa.
 */
export async function getResumoMinhaHome(limites: {
  agora: string;
  hojeInicio: string;
  hojeFim: string;
  semanaInicio: string;
  semanaFim: string;
  ontemInicio: string;
  ontemFim: string;
}): Promise<ResumoMinhaHome> {
  const query = new URLSearchParams(limites);
  return request<ResumoMinhaHome>(`/demandas/minha-home/resumo?${query.toString()}`);
}

/**
 * D2-D3A — os 7 indicadores baseados em Demanda da Central de Tráfego
 * (`TrafegoIndicadoresDemandas`), agregados no servidor sobre o universo INTEGRAL permitido
 * — nunca as 200 demandas globais de `AppDataContext`. Autorização própria no backend
 * (admin/gestor, 403 para qualquer outro perfil) — não depende só de `podeAcessarCentralTrafego`
 * no cliente. Sem `horasExecutadas` (SessaoTrabalho, fonte separada — D2-D3B).
 */
export type ResumoOperacional = {
  internas: number;
  clientes: number;
  recebidas: number;
  concluidasNoPeriodo: number;
  horasEstimadas: number;
  totalNaBase: number;
  emAndamento: number;
};

/** `periodoInicio` é "desde quando", sem teto — mesma semântica de `periodoParaDataInicio`. */
export async function getResumoOperacional(periodoInicio: string): Promise<ResumoOperacional> {
  const query = new URLSearchParams({ periodoInicio });
  return request<ResumoOperacional>(`/demandas/operacional/resumo?${query.toString()}`);
}

/**
 * D2-D3A — RegraExpedienteView. Endpoint dedicado (não o resumo acima): `emAndamento` não
 * depende de período, e essa tela nunca teve conceito de período.
 */
export async function getEmAndamentoOperacional(): Promise<{ emAndamento: number }> {
  return request<{ emAndamento: number }>("/demandas/operacional/em-andamento");
}

export async function criarDemandaReal(draft: DemandaFormDraft): Promise<Demanda> {
  const payload = {
    ...demandaDraftParaPayload(draft),
    ...(draft.workflowModeloId ? { workflowModeloId: draft.workflowModeloId } : {}),
  };
  const criada = await request<DemandaReadApi>("/demandas", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapDemandaReadToDemanda(criada);
}

export async function atualizarDemandaReal(demandaId: string, draft: DemandaFormDraft): Promise<Demanda> {
  const atualizada = await request<DemandaReadApi>(`/demandas/${demandaId}`, {
    method: "PATCH",
    body: JSON.stringify(demandaDraftParaPayload(draft)),
  });
  return mapDemandaReadToDemanda(atualizada);
}

/**
 * Alteração parcial e avulsa — status pelo Kanban, bandeira, prazo.
 *
 * `motivoBloqueio` é **obrigatório** ao ir para `bloqueada` (422 sem ele) e é limpo pelo
 * servidor ao sair do bloqueio. Entrar em `em_execucao` fora do expediente levanta
 * `ForaDeExpedienteError`, que carrega a janela vigente.
 */
// Nomeado (não anônimo) para ser reaproveitado por quem monta patch parcial fora deste
// arquivo — ver DemandaFormSections.tsx, que centraliza a edição inline do drawer aqui em
// vez de duplicar a forma do payload (ver instrução da Fase 2E.4 sobre o bug do drawer).
export type DemandaPatchCampos = Partial<{
  nome: string;
  status: DemandaStatusEditavel;
  prioridade: DemandaPrioridade;
  sinalizada: boolean;
  motivoBloqueio: string | null;
  briefing: string | null;
  pit: string | null;
  clienteId: string | null;
  projetoId: string | null;
  dataInicio: string | null;
  dataFimPrevista: string | null;
  prazoEtapaAtual: string | null;
  enviadoClienteEm: string | null;
  prazoRetornoCliente: string | null;
  retornoRecebidoEm: string | null;
  emailConclusaoEnviado: boolean;
  emailConclusaoData: string | null;
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
}>;

export async function patchDemandaReal(demandaId: string, campos: DemandaPatchCampos): Promise<Demanda> {
  const atualizada = await request<DemandaReadApi>(`/demandas/${demandaId}`, {
    method: "PATCH",
    body: JSON.stringify(campos),
  });
  return mapDemandaReadToDemanda(atualizada);
}

// "Excluir" = arquivar (soft-delete permanente) — ver docs/padrao-arquivamento.md.
// Restrito a admin/gestor no servidor; operador recebe 403.
export async function arquivarDemandaReal(demandaId: string, motivoArquivamento: string): Promise<Demanda> {
  const arquivada = await request<DemandaReadApi>(`/demandas/${demandaId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapDemandaReadToDemanda(arquivada);
}

export async function restaurarDemandaReal(demandaId: string): Promise<Demanda> {
  const restaurada = await request<DemandaReadApi>(`/demandas/${demandaId}/restaurar`, { method: "POST" });
  return mapDemandaReadToDemanda(restaurada);
}

// ---------------------------------------------------------------------------------------
// Checklist de Demanda (Fase 2E.3) — endpoint dedicado, fora do payload de Demanda (ver
// mapDemandaReadToDemanda). Buscado sob demanda por DemandaChecklistCard ao abrir a Demanda.
// ---------------------------------------------------------------------------------------

export type DemandaChecklistItemReadApi = {
  id: string;
  demandaId: string;
  texto: string;
  ordem: number;
  concluido: boolean;
  concluidoEm: string | null;
  concluidoPorUsuarioId: string | null;
  criadoPorUsuarioId: string | null;
  createdAt: string;
  updatedAt: string;
};

function mapChecklistItemReadToItem(data: DemandaChecklistItemReadApi): DemandaChecklistItem {
  return { ...data };
}

export async function listChecklistDemanda(demandaId: string, escopo?: EscopoLeituraDemanda): Promise<DemandaChecklistItem[]> {
  const itens = await request<DemandaChecklistItemReadApi[]>(`/demandas/${demandaId}/checklist${sufixoEscopoLeitura(escopo)}`);
  return itens.map(mapChecklistItemReadToItem);
}

export async function criarItemChecklist(demandaId: string, texto: string): Promise<DemandaChecklistItem> {
  const item = await request<DemandaChecklistItemReadApi>(`/demandas/${demandaId}/checklist`, {
    method: "POST",
    body: JSON.stringify({ texto }),
  });
  return mapChecklistItemReadToItem(item);
}

export async function editarTextoItemChecklist(
  demandaId: string,
  itemId: string,
  texto: string,
): Promise<DemandaChecklistItem> {
  const item = await request<DemandaChecklistItemReadApi>(`/demandas/${demandaId}/checklist/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ texto }),
  });
  return mapChecklistItemReadToItem(item);
}

export async function alternarConclusaoItemChecklist(
  demandaId: string,
  itemId: string,
  concluido: boolean,
): Promise<DemandaChecklistItem> {
  const item = await request<DemandaChecklistItemReadApi>(`/demandas/${demandaId}/checklist/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify({ concluido }),
  });
  return mapChecklistItemReadToItem(item);
}

export async function reordenarChecklist(demandaId: string, itemIds: string[]): Promise<DemandaChecklistItem[]> {
  const itens = await request<DemandaChecklistItemReadApi[]>(`/demandas/${demandaId}/checklist/reordenar`, {
    method: "PUT",
    body: JSON.stringify({ itemIds }),
  });
  return itens.map(mapChecklistItemReadToItem);
}

export async function excluirItemChecklist(demandaId: string, itemId: string): Promise<void> {
  await request<null>(`/demandas/${demandaId}/checklist/${itemId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------------------
// Arquivos de Demanda (Fase 2E.3) — metadado por endpoint dedicado; conteúdo só por download
// autenticado, nunca por URL estática (ver docs/pendencias-arquiteturais.md, item 9).
// ---------------------------------------------------------------------------------------

export type DemandaArquivoReadApi = {
  id: string;
  demandaId: string;
  nomeOriginal: string | null;
  contentType: string | null;
  tamanhoBytes: number | null;
  enviadoPorUsuarioId: string | null;
  createdAt: string;
  tipo: DemandaArquivo["tipo"];
  statusLayout: DemandaArquivo["statusLayout"];
  url: string | null;
  titulo: string | null;
  descricao: string | null;
};

function mapArquivoReadToArquivo(data: DemandaArquivoReadApi): DemandaArquivo {
  return { ...data };
}

export async function listArquivosDemanda(demandaId: string, escopo?: EscopoLeituraDemanda): Promise<DemandaArquivo[]> {
  const arquivos = await request<DemandaArquivoReadApi[]>(`/demandas/${demandaId}/arquivos${sufixoEscopoLeitura(escopo)}`);
  return arquivos.map(mapArquivoReadToArquivo);
}

// Upload é multipart — `request()` força `Content-Type: application/json`, o que destruiria
// o boundary do FormData (mesma razão documentada no proxy, ver
// src/app/api/backend/[...path]/route.ts). Por isso fala com `fetch` diretamente.
// `tipo` default "anexo" preserva o contrato de quem já chama sem especificar.
export async function uploadArquivoDemanda(
  demandaId: string,
  file: File,
  tipo: "anexo" | "layout" = "anexo",
): Promise<DemandaArquivo> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("tipo", tipo);
  const response = await fetch(`/api/backend/demandas/${demandaId}/arquivos`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : (detail?.message ?? data?.message);
    throw new Error(message ?? `Erro ${response.status}`);
  }
  return mapArquivoReadToArquivo(await response.json());
}

export async function criarLinkArquivoDemanda(
  demandaId: string,
  payload: { titulo: string; url: string; descricao?: string },
): Promise<DemandaArquivo> {
  const data = await request<DemandaArquivoReadApi>(`/demandas/${demandaId}/arquivos/link`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapArquivoReadToArquivo(data);
}

export async function atualizarStatusLayoutArquivo(
  demandaId: string,
  arquivoId: string,
  statusLayout: NonNullable<DemandaArquivo["statusLayout"]>,
): Promise<DemandaArquivo> {
  const data = await request<DemandaArquivoReadApi>(`/demandas/${demandaId}/arquivos/${arquivoId}`, {
    method: "PATCH",
    body: JSON.stringify({ statusLayout }),
  });
  return mapArquivoReadToArquivo(data);
}

export async function excluirArquivoDemanda(demandaId: string, arquivoId: string): Promise<void> {
  await request<null>(`/demandas/${demandaId}/arquivos/${arquivoId}`, { method: "DELETE" });
}

// Usada direto num `<a href>` — o proxy lê o cookie de sessão, então o navegador autentica
// a navegação normalmente, sem JS extra. Nunca aponta pro FastAPI direto. Nunca para
// `tipo:"link"` — link abre `arquivo.url` direto, não tem conteúdo físico pra baixar.
export function urlDownloadArquivoDemanda(demandaId: string, arquivoId: string, escopo?: EscopoLeituraDemanda): string {
  return `/api/backend/demandas/${demandaId}/arquivos/${arquivoId}/download${sufixoEscopoLeitura(escopo)}`;
}

// ---------------------------------------------------------------------------------------
// Gerenciador central de Arquivos (Fase 2H.1) — visão transversal sobre demanda_arquivos,
// sem duplicação física. Resposta já vem com cliente/projeto/demanda/usuário resolvidos —
// nunca depende de AppDataContext/diretório global (ver docstring do schema no backend).
// ---------------------------------------------------------------------------------------

export async function listArquivosCentral(filtros: ArquivosCentralFiltros = {}): Promise<ArquivoCentral[]> {
  const search = new URLSearchParams();
  if (filtros.search) search.set("search", filtros.search);
  if (filtros.clienteId) search.set("clienteId", filtros.clienteId);
  if (filtros.projetoId) search.set("projetoId", filtros.projetoId);
  if (filtros.demandaId) search.set("demandaId", filtros.demandaId);
  if (filtros.tipo) search.set("tipo", filtros.tipo);
  if (filtros.status) search.set("status", filtros.status);
  if (filtros.usuarioId) search.set("usuarioId", filtros.usuarioId);
  if (filtros.clienteIdExcluir) search.set("clienteIdExcluir", filtros.clienteIdExcluir);
  if (filtros.projetoIdExcluir) search.set("projetoIdExcluir", filtros.projetoIdExcluir);
  if (filtros.demandaIdExcluir) search.set("demandaIdExcluir", filtros.demandaIdExcluir);
  if (filtros.tipoExcluir) search.set("tipoExcluir", filtros.tipoExcluir);
  if (filtros.statusExcluir) search.set("statusExcluir", filtros.statusExcluir);
  if (filtros.usuarioIdExcluir) search.set("usuarioIdExcluir", filtros.usuarioIdExcluir);
  if (filtros.dataInicio) search.set("dataInicio", filtros.dataInicio);
  if (filtros.dataFim) search.set("dataFim", filtros.dataFim);
  search.set("limit", String(filtros.limit ?? 50));
  search.set("offset", String(filtros.offset ?? 0));
  return request<ArquivoCentral[]>(`/arquivos?${search.toString()}`);
}

// ---------------------------------------------------------------------------------------
// Comentários de Demanda (Fase 2E.4) — endpoint dedicado, fora do payload de Demanda.
// Autoria é decidida no backend: editar só o autor; excluir autor OU admin/gestor. O
// frontend só reflete (esconde/desabilita ação) — nunca é a barreira real.
// ---------------------------------------------------------------------------------------

export type DemandaComentarioReadApi = {
  id: string;
  demandaId: string;
  autorUsuarioId: string | null;
  /** Autor é conta de sistema: o backend não envia o id e a UI mostra "Sistema". */
  autorSistema?: boolean;
  texto: string;
  createdAt: string;
  updatedAt: string;
  editadoEm: string | null;
};

function mapComentarioReadToComentario(data: DemandaComentarioReadApi): DemandaComentario {
  return { ...data };
}

export async function listComentariosDemanda(demandaId: string, escopo?: EscopoLeituraDemanda): Promise<DemandaComentario[]> {
  const comentarios = await request<DemandaComentarioReadApi[]>(`/demandas/${demandaId}/comentarios${sufixoEscopoLeitura(escopo)}`);
  return comentarios.map(mapComentarioReadToComentario);
}

export async function criarComentarioDemanda(demandaId: string, texto: string): Promise<DemandaComentario> {
  const comentario = await request<DemandaComentarioReadApi>(`/demandas/${demandaId}/comentarios`, {
    method: "POST",
    body: JSON.stringify({ texto }),
  });
  return mapComentarioReadToComentario(comentario);
}

export async function editarComentarioDemanda(
  demandaId: string,
  comentarioId: string,
  texto: string,
): Promise<DemandaComentario> {
  const comentario = await request<DemandaComentarioReadApi>(
    `/demandas/${demandaId}/comentarios/${comentarioId}`,
    { method: "PATCH", body: JSON.stringify({ texto }) },
  );
  return mapComentarioReadToComentario(comentario);
}

export async function excluirComentarioDemanda(demandaId: string, comentarioId: string): Promise<void> {
  await request<null>(`/demandas/${demandaId}/comentarios/${comentarioId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------------------
// Histórico de Demanda (Fase 2E.4) — leitura de eventos reais, escopada pela Demanda. Nunca
// é `GET /eventos` (auditoria administrativa global, admin/gestor-only).
// ---------------------------------------------------------------------------------------

export type DemandaHistoricoEventoReadApi = {
  id: string;
  tipo: string;
  usuarioId: string | null;
  occurredAt: string;
  dados: Record<string, unknown>;
};

function mapHistoricoEventoReadToEvento(data: DemandaHistoricoEventoReadApi): DemandaHistoricoEvento {
  return { ...data };
}

export async function listHistoricoDemanda(demandaId: string, escopo?: EscopoLeituraDemanda): Promise<DemandaHistoricoEvento[]> {
  const eventos = await request<DemandaHistoricoEventoReadApi[]>(`/demandas/${demandaId}/historico${sufixoEscopoLeitura(escopo)}`);
  return eventos.map(mapHistoricoEventoReadToEvento);
}

// ---------------------------------------------------------------------------------------
// Ajuste e conclusão por e-mail (Fase 2E.4) — ações que só publicam evento de domínio na
// timeline da Demanda (ver DemandaService.registrar_ajuste/registrar_conclusao_email).
// ---------------------------------------------------------------------------------------

export type TipoAjusteDemanda = "ajuste_interno" | "ajuste_cliente" | "refacao";

export async function registrarAjusteDemanda(
  demandaId: string,
  tipo: TipoAjusteDemanda,
): Promise<DemandaHistoricoEvento> {
  const evento = await request<DemandaHistoricoEventoReadApi>(`/demandas/${demandaId}/ajustes`, {
    method: "POST",
    body: JSON.stringify({ tipo }),
  });
  return mapHistoricoEventoReadToEvento(evento);
}

// `enviado=true`: e-mail de conclusão foi enviado ao cliente. `enviado=false`: usuário
// dispensou o aviso. Mesmos campos reais nos dois casos — só o evento publicado muda.
export async function registrarConclusaoEmailDemanda(demandaId: string, enviado: boolean): Promise<Demanda> {
  const atualizada = await request<DemandaReadApi>(`/demandas/${demandaId}/conclusao-email`, {
    method: "POST",
    body: JSON.stringify({ enviado }),
  });
  return mapDemandaReadToDemanda(atualizada);
}

// ---------------------------------------------------------------------------------------
// WorkflowModelo
// ---------------------------------------------------------------------------------------

type WorkflowModeloEtapaReadApi = {
  id: string;
  ordem: number;
  nome: string;
  tipo: WorkflowModeloEtapa["tipo"];
  quantidadeAntesDeadline: number;
  unidadePrazo: WorkflowModeloEtapa["unidadePrazo"];
  usuarioResponsavelIds: string[];
  departamentoResponsavelIds: string[];
};

type WorkflowModeloReadApi = {
  id: string;
  empresaId: string;
  codigoInterno: string;
  codigoReferencia: string;
  anoReferencia: number;
  sequencialReferencia: number;
  nome: string;
  status: WorkflowModeloStatus;
  etapas: WorkflowModeloEtapaReadApi[];
  createdAt: string;
  updatedAt: string;
};

function mapWorkflowModeloReadToWorkflowModelo(data: WorkflowModeloReadApi): WorkflowModelo {
  return {
    id: data.id,
    empresaId: data.empresaId,
    codigoInterno: data.codigoInterno,
    codigoReferencia: data.codigoReferencia,
    anoReferencia: data.anoReferencia,
    sequencialReferencia: data.sequencialReferencia,
    nome: data.nome,
    status: data.status,
    etapas: data.etapas.map((etapa) => ({
      id: etapa.id,
      nome: etapa.nome,
      tipo: etapa.tipo,
      quantidadeAntesDeadline: etapa.quantidadeAntesDeadline,
      unidadePrazo: etapa.unidadePrazo,
      usuarioResponsavelIds: etapa.usuarioResponsavelIds,
      departamentoResponsavelIds: etapa.departamentoResponsavelIds,
    })),
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
  };
}

function workflowModeloDraftParaPayload(draft: WorkflowModeloFormDraft) {
  return {
    nome: draft.nome,
    etapas: draft.etapas.map((etapa) => ({
      nome: etapa.nome,
      tipo: etapa.tipo,
      quantidadeAntesDeadline: etapa.quantidadeAntesDeadline,
      unidadePrazo: etapa.unidadePrazo,
      usuarioResponsavelIds: etapa.usuarioResponsavelIds,
      departamentoResponsavelIds: etapa.departamentoResponsavelIds,
    })),
  };
}

/** Projeção mínima pra seleção operacional — ver WorkflowModeloDiretorioItem. */
type WorkflowModeloDiretorioApi = {
  id: string;
  codigoReferencia: string;
  nome: string;
};

export async function listDiretorioWorkflowModelos(): Promise<WorkflowModeloDiretorioItem[]> {
  return request<WorkflowModeloDiretorioApi[]>("/workflow-modelos/diretorio");
}

/** Projeção mínima pra seleção operacional — ver TipoTarefaDiretorioItem. */
type TipoTarefaDiretorioApi = {
  id: string;
  nome: string;
};

export async function listDiretorioTiposTarefa(): Promise<TipoTarefaDiretorioItem[]> {
  return request<TipoTarefaDiretorioApi[]>("/tipos-tarefa/diretorio");
}

// CRUD real (Fase 2G.9) — cadastro administrativo, mesmo padrão de Departamento/
// WorkflowModelo (arquivar/restaurar dedicados, status "arquivado" nunca aceito via PATCH).
type TipoTarefaReadApi = {
  id: string;
  empresaId: string;
  nome: string;
  descricao: string | null;
  ordem: number;
  status: TipoTarefaStatus;
  createdAt: string;
  updatedAt: string;
};

function mapTipoTarefaReadToTipoTarefa(data: TipoTarefaReadApi): TipoTarefa {
  return {
    id: data.id,
    empresaId: data.empresaId,
    nome: data.nome,
    descricao: data.descricao ?? "",
    ordem: data.ordem,
    status: data.status,
    createdAt: data.createdAt,
    updatedAt: data.updatedAt,
  };
}

function tipoTarefaDraftParaPayload(draft: TipoTarefaFormDraft) {
  return {
    nome: draft.nome,
    descricao: draft.descricao || null,
    ordem: draft.ordem,
  };
}

export async function listTiposTarefaReais(params?: { status?: string; search?: string }): Promise<TipoTarefa[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  const data = await request<TipoTarefaReadApi[]>(`/tipos-tarefa?${query.toString()}`);
  return data.map(mapTipoTarefaReadToTipoTarefa);
}

export async function criarTipoTarefaReal(draft: TipoTarefaFormDraft): Promise<TipoTarefa> {
  const criado = await request<TipoTarefaReadApi>("/tipos-tarefa", {
    method: "POST",
    body: JSON.stringify(tipoTarefaDraftParaPayload(draft)),
  });
  // status só é aceito no PATCH — criar sempre nasce ativo.
  if (draft.status === "inativo") {
    return atualizarTipoTarefaReal(criado.id, draft);
  }
  return mapTipoTarefaReadToTipoTarefa(criado);
}

export async function atualizarTipoTarefaReal(
  tipoTarefaId: string,
  draft: TipoTarefaFormDraft,
): Promise<TipoTarefa> {
  const atualizado = await request<TipoTarefaReadApi>(`/tipos-tarefa/${tipoTarefaId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...tipoTarefaDraftParaPayload(draft), status: draft.status }),
  });
  return mapTipoTarefaReadToTipoTarefa(atualizado);
}

// "Excluir" = arquivar (soft-delete permanente) — ver docs/padrao-arquivamento.md.
export async function arquivarTipoTarefaReal(
  tipoTarefaId: string,
  motivoArquivamento: string,
): Promise<TipoTarefa> {
  const arquivado = await request<TipoTarefaReadApi>(`/tipos-tarefa/${tipoTarefaId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapTipoTarefaReadToTipoTarefa(arquivado);
}

export async function restaurarTipoTarefaReal(tipoTarefaId: string): Promise<TipoTarefa> {
  const restaurado = await request<TipoTarefaReadApi>(`/tipos-tarefa/${tipoTarefaId}/restaurar`, {
    method: "POST",
  });
  return mapTipoTarefaReadToTipoTarefa(restaurado);
}

// Detalhe completo (com etapas) — aberto a qualquer autenticado, não só admin/gestor: quem
// pode criar Demanda precisa ver as etapas do workflow escolhido antes de aplicar. Usado pela
// prévia da Nova Tarefa depois de escolher um item do diretório.
export async function obterWorkflowModeloReal(workflowModeloId: string): Promise<WorkflowModelo> {
  return mapWorkflowModeloReadToWorkflowModelo(
    await request<WorkflowModeloReadApi>(`/workflow-modelos/${workflowModeloId}`),
  );
}

export async function listWorkflowModelosReais(params?: { status?: string; search?: string }): Promise<WorkflowModelo[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  const data = await request<WorkflowModeloReadApi[]>(`/workflow-modelos?${query.toString()}`);
  return data.map(mapWorkflowModeloReadToWorkflowModelo);
}

export async function criarWorkflowModeloReal(draft: WorkflowModeloFormDraft): Promise<WorkflowModelo> {
  const criado = await request<WorkflowModeloReadApi>("/workflow-modelos", {
    method: "POST",
    body: JSON.stringify(workflowModeloDraftParaPayload(draft)),
  });
  // status só é aceito no PATCH — criar sempre nasce ativo.
  if (draft.status === "inativo") {
    return atualizarWorkflowModeloReal(criado.id, draft);
  }
  return mapWorkflowModeloReadToWorkflowModelo(criado);
}

export async function atualizarWorkflowModeloReal(
  workflowModeloId: string,
  draft: WorkflowModeloFormDraft,
): Promise<WorkflowModelo> {
  const atualizado = await request<WorkflowModeloReadApi>(`/workflow-modelos/${workflowModeloId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...workflowModeloDraftParaPayload(draft), status: draft.status }),
  });
  return mapWorkflowModeloReadToWorkflowModelo(atualizado);
}

// "Excluir" = arquivar (soft-delete permanente) — ver docs/padrao-arquivamento.md.
export async function arquivarWorkflowModeloReal(
  workflowModeloId: string,
  motivoArquivamento: string,
): Promise<WorkflowModelo> {
  const arquivado = await request<WorkflowModeloReadApi>(`/workflow-modelos/${workflowModeloId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
  return mapWorkflowModeloReadToWorkflowModelo(arquivado);
}

export async function restaurarWorkflowModeloReal(workflowModeloId: string): Promise<WorkflowModelo> {
  const restaurado = await request<WorkflowModeloReadApi>(`/workflow-modelos/${workflowModeloId}/restaurar`, {
    method: "POST",
  });
  return mapWorkflowModeloReadToWorkflowModelo(restaurado);
}

// ---------------------------------------------------------------------------------
// Relatórios — agregação de eventos (Fase 2F.4)
// ---------------------------------------------------------------------------------

export type ContagemAjustes = {
  ajustesInternos: number;
  ajustesCliente: number;
  refacoes: number;
};

export type RelatorioAjustesProjeto = {
  total: ContagemAjustes;
  porDemanda: Record<string, ContagemAjustes>;
};

/** `GET /relatorios/demandas/ajustes` já devolve exatamente este formato (camelCase via
 * alias do schema Pydantic) — sem mapeamento snake_case aqui, diferente da maioria das
 * outras entidades deste módulo. `projetoId` inexistente ou de outra empresa vira 404, que
 * `request()` propaga como erro (ver `ProjetoArquivadoConflictError` e afins acima) — quem
 * chama trata como qualquer outra falha, não como "zero real". */
export async function getRelatorioAjustesPorProjeto(projetoId: string): Promise<RelatorioAjustesProjeto> {
  return request<RelatorioAjustesProjeto>(`/relatorios/demandas/ajustes?projetoId=${encodeURIComponent(projetoId)}`);
}

/**
 * D4A — "Análise de projeto" agregada no servidor sobre o universo INTEGRAL do Projeto (nunca
 * `AppDataContext.demandas`, que é `GET /demandas?limit=200` da empresa inteira). Só o Projeto
 * é filtro: a tela nunca teve período/status/cliente.
 */
export async function getRelatorioAnaliseProjeto(projetoId: string): Promise<RelatorioAnaliseProjeto> {
  return request<RelatorioAnaliseProjeto>(`/relatorios/projetos/analise?projetoId=${encodeURIComponent(projetoId)}`);
}

/**
 * D4B — opções do seletor de "Performance de colaborador": o mesmo conjunto do diretório de
 * usuários (todos os status, sem conta de sistema, `nome ASC`), mas sem o `limit=200`.
 */
export async function getRelatorioColaboradores(): Promise<RelatorioColaboradorOpcao[]> {
  return request<RelatorioColaboradorOpcao[]>("/relatorios/colaboradores");
}

/** D4B — "Performance de colaborador" no servidor, sobre TODAS as Demandas dele (nunca `AppDataContext.demandas`). */
export async function getRelatorioPerformanceColaborador(colaboradorId: string): Promise<RelatorioPerformanceColaborador> {
  return request<RelatorioPerformanceColaborador>(
    `/relatorios/colaboradores/performance?colaboradorId=${encodeURIComponent(colaboradorId)}`,
  );
}

/** D4B — gráfico "Demandas em aberto por projeto" de um Cliente. */
export async function getRelatorioAbertasPorProjeto(clienteId: string): Promise<FatiaPizza[]> {
  return request<FatiaPizza[]>(`/relatorios/graficos/abertas-por-projeto?clienteId=${encodeURIComponent(clienteId)}`);
}

/** D4B — gráfico "Volume de demandas por projeto e colaborador". */
export async function getRelatorioVolumePorColaborador(): Promise<SerieBarraEmpilhada[]> {
  return request<SerieBarraEmpilhada[]>("/relatorios/graficos/volume-por-colaborador");
}

/** D4B — gráfico "Volume de demandas em fluxo": 12 semanas (a corrente + 11), da mais antiga à mais nova. */
export async function getRelatorioVolumeSemanal(): Promise<RelatorioPontoSemanal[]> {
  return request<RelatorioPontoSemanal[]>("/relatorios/graficos/volume-semanal");
}

/** D4A — "Análise de peças" paginada no servidor (`limit`/`offset`, com `total`), mais recente primeiro. */
export async function getRelatorioPecasProjeto(
  projetoId: string,
  limit: number,
  offset: number,
): Promise<RelatorioPecasPagina> {
  const search = new URLSearchParams({ projetoId, limit: String(limit), offset: String(offset) });
  return request<RelatorioPecasPagina>(`/relatorios/projetos/pecas?${search.toString()}`);
}

// ---------------------------------------------------------------------------------
// Regra de Expediente — singleton por Empresa (Fase 2G.3)
// ---------------------------------------------------------------------------------
//
// `RegraExpedienteRead`/`JanelaDiaRead`/`EstadoExpedienteRead` do backend já devolvem
// exatamente o formato de `RegraExpediente`/`JanelaDia`/`EstadoExpediente` (camelCase via
// alias Pydantic) — mesmo caso de `RelatorioAjustesProjeto` acima, sem mapeamento aqui.

export async function getRegraExpedienteReal(): Promise<RegraExpediente> {
  return request<RegraExpediente>("/regra-expediente");
}

export async function atualizarRegraExpedienteReal(
  draft: RegraExpedienteUpdateDraft,
): Promise<RegraExpediente> {
  return request<RegraExpediente>("/regra-expediente", {
    method: "PATCH",
    body: JSON.stringify(draft),
  });
}

// Leitura operacional enxuta — Kanban, capacidade de Meu Departamento. Nunca baixa a regra
// inteira: ver docstring de app/api/routes/expediente.py.
export async function getEstadoExpedienteReal(): Promise<EstadoExpediente> {
  return request<EstadoExpediente>("/expediente/estado");
}

// ---------------------------------------------------------------------------------
// Categoria de Peça e Peça — catálogo real (Fase 2G.4)
// ---------------------------------------------------------------------------------
//
// `CategoriaPecaRead`/`PecaRead` do backend já devolvem exatamente o formato de
// `CategoriaPeca`/`Peca` (camelCase via alias Pydantic) — mesmo caso de RegraExpediente,
// sem mapeamento aqui.

function categoriaPecaDraftParaPayload(draft: CategoriaPecaFormDraft) {
  return { nome: draft.nome, ...(draft.ordem !== undefined ? { ordem: draft.ordem } : {}) };
}

export async function listCategoriasPecaReais(params?: {
  search?: string;
  status?: "ativo" | "arquivado";
}): Promise<CategoriaPeca[]> {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.status) query.set("status", params.status);
  return request<CategoriaPeca[]>(`/categorias-peca?${query.toString()}`);
}

export async function listDiretorioCategoriasPeca(): Promise<CategoriaPecaDiretorioItem[]> {
  return request<CategoriaPecaDiretorioItem[]>("/categorias-peca/diretorio");
}

export async function criarCategoriaPecaReal(draft: CategoriaPecaFormDraft): Promise<CategoriaPeca> {
  return request<CategoriaPeca>("/categorias-peca", {
    method: "POST",
    body: JSON.stringify(categoriaPecaDraftParaPayload(draft)),
  });
}

export async function atualizarCategoriaPecaReal(
  categoriaId: string,
  draft: CategoriaPecaFormDraft,
): Promise<CategoriaPeca> {
  return request<CategoriaPeca>(`/categorias-peca/${categoriaId}`, {
    method: "PATCH",
    body: JSON.stringify(categoriaPecaDraftParaPayload(draft)),
  });
}

export async function arquivarCategoriaPecaReal(categoriaId: string, motivoArquivamento: string): Promise<CategoriaPeca> {
  return request<CategoriaPeca>(`/categorias-peca/${categoriaId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
}

export async function restaurarCategoriaPecaReal(categoriaId: string): Promise<CategoriaPeca> {
  return request<CategoriaPeca>(`/categorias-peca/${categoriaId}/restaurar`, { method: "POST" });
}

function pecaDraftParaPayload(draft: PecaFormDraft) {
  return {
    nome: draft.nome,
    categoriaId: draft.categoriaId,
    tempoEstimadoMinutos: draft.tempoEstimadoMinutos,
    tempoMedioMinutos: draft.tempoMedioMinutos,
    valorTabelaCentavos: draft.valorTabelaCentavos,
    sindicatoAtivo: draft.sindicatoAtivo,
    valorSindicatoCriacaoCentavos: draft.valorSindicatoCriacaoCentavos,
    valorSindicatoAdaptacaoCentavos: draft.valorSindicatoAdaptacaoCentavos,
    valorSindicatoFinalizacaoCentavos: draft.valorSindicatoFinalizacaoCentavos,
    briefingPadrao: draft.briefingPadrao,
  };
}

export async function listPecasReais(params?: { search?: string; categoriaId?: string }): Promise<Peca[]> {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.categoriaId) query.set("categoriaId", params.categoriaId);
  return request<Peca[]>(`/pecas?${query.toString()}`);
}

export async function listDiretorioPecas(): Promise<PecaDiretorioItem[]> {
  return request<PecaDiretorioItem[]>("/pecas/diretorio");
}

export async function criarPecaReal(draft: PecaFormDraft): Promise<Peca> {
  const criada = await request<Peca>("/pecas", { method: "POST", body: JSON.stringify(pecaDraftParaPayload(draft)) });
  if (draft.status !== "ativo") {
    return atualizarPecaReal(criada.id, draft);
  }
  return criada;
}

export async function atualizarPecaReal(pecaId: string, draft: PecaFormDraft): Promise<Peca> {
  return request<Peca>(`/pecas/${pecaId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...pecaDraftParaPayload(draft), status: draft.status === "arquivado" ? undefined : draft.status }),
  });
}

export async function arquivarPecaReal(pecaId: string, motivoArquivamento: string): Promise<Peca> {
  return request<Peca>(`/pecas/${pecaId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
}

export async function restaurarPecaReal(pecaId: string): Promise<Peca> {
  return request<Peca>(`/pecas/${pecaId}/restaurar`, { method: "POST" });
}

// ---------------------------------------------------------------------------------
// Modelo de Campanha — biblioteca reutilizável (Fase 2G.5A backend / 2G.5B UI)
// ---------------------------------------------------------------------------------
//
// `ModeloCampanhaRead` do backend já devolve exatamente o formato de `ModeloCampanha`
// (camelCase via alias Pydantic), mesmo caso de CategoriaPeca/Peca — sem mapeamento aqui.
// Itens são sempre o agregado inteiro (sem endpoint próprio) — ver docstring de
// ModeloCampanhaService no backend.

function modeloCampanhaDraftParaPayload(draft: ModeloCampanhaFormDraft) {
  return {
    nome: draft.nome,
    descricao: draft.descricao.trim() || null,
    itens: draft.itens.map(itemModeloCampanhaDraftParaPayload),
  };
}

export async function listModelosCampanhaReais(params?: {
  status?: "ativo" | "inativo" | "arquivado";
  search?: string;
}): Promise<ModeloCampanha[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  return request<ModeloCampanha[]>(`/modelos-campanha?${query.toString()}`);
}

export async function criarModeloCampanhaReal(draft: ModeloCampanhaFormDraft): Promise<ModeloCampanha> {
  const criado = await request<ModeloCampanha>("/modelos-campanha", {
    method: "POST",
    body: JSON.stringify(modeloCampanhaDraftParaPayload(draft)),
  });
  // Criar sempre nasce ativo (ModeloCampanhaCreate não aceita status) — mesmo padrão de
  // Peça/WorkflowModelo: status só é assumido via PATCH em seguida.
  if (draft.status !== "ativo") {
    return atualizarModeloCampanhaReal(criado.id, draft);
  }
  return criado;
}

export async function atualizarModeloCampanhaReal(
  modeloCampanhaId: string,
  draft: ModeloCampanhaFormDraft,
): Promise<ModeloCampanha> {
  return request<ModeloCampanha>(`/modelos-campanha/${modeloCampanhaId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...modeloCampanhaDraftParaPayload(draft), status: draft.status }),
  });
}

export async function arquivarModeloCampanhaReal(
  modeloCampanhaId: string,
  motivoArquivamento: string,
): Promise<ModeloCampanha> {
  return request<ModeloCampanha>(`/modelos-campanha/${modeloCampanhaId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
}

export async function restaurarModeloCampanhaReal(modeloCampanhaId: string): Promise<ModeloCampanha> {
  return request<ModeloCampanha>(`/modelos-campanha/${modeloCampanhaId}/restaurar`, { method: "POST" });
}

export async function listDiretorioModelosCampanha(): Promise<ModeloCampanhaDiretorioItem[]> {
  return request<ModeloCampanhaDiretorioItem[]>("/modelos-campanha/diretorio");
}

// ---------------------------------------------------------------------------------
// Snapshot de Modelo de Campanha em Projeto (Fase 2G.5C3)
// ---------------------------------------------------------------------------------
//
// `ProjetoModeloCampanhaSnapshotRead` do backend já devolve exatamente este formato
// (camelCase via alias Pydantic), mesmo caso de ModeloCampanha — sem mapeamento aqui. GET
// devolve `null` (200) quando o Projeto ainda não tem Modelo aplicado — nunca 404 só por
// isso (404 fica reservado a Projeto inexistente/cross-tenant, tratado pelo `request()`).

export async function getProjetoModeloCampanhaSnapshot(
  projetoId: string,
): Promise<ProjetoModeloCampanhaSnapshot | null> {
  return request<ProjetoModeloCampanhaSnapshot | null>(`/projetos/${projetoId}/modelo-campanha`);
}

export async function aplicarModeloCampanhaAoProjetoReal(
  projetoId: string,
  modeloCampanhaId: string,
): Promise<ProjetoModeloCampanhaSnapshot> {
  return request<ProjetoModeloCampanhaSnapshot>(`/projetos/${projetoId}/modelo-campanha/aplicar`, {
    method: "POST",
    body: JSON.stringify({ modeloCampanhaId }),
  });
}

// Só os itens — proveniência/metadados (origem, nome do Modelo, aplicadoAt/Por) são
// controlados exclusivamente pelo backend via /aplicar, nunca por este PATCH.
export async function atualizarProjetoModeloCampanhaSnapshotReal(
  projetoId: string,
  draft: ProjetoModeloCampanhaUpdateDraft,
): Promise<ProjetoModeloCampanhaSnapshot> {
  return request<ProjetoModeloCampanhaSnapshot>(`/projetos/${projetoId}/modelo-campanha`, {
    method: "PATCH",
    body: JSON.stringify({ itens: draft.itens.map(itemModeloCampanhaDraftParaPayload) }),
  });
}

// ---------------------------------------------------------------------------------
// SLA — configuração de regras (Fase 2G.6B backend / 2G.6E2 UI)
// ---------------------------------------------------------------------------------
//
// `SlaRegraRead` do backend já devolve exatamente o formato de `SlaRegra` (camelCase via
// alias Pydantic) — sem mapeamento aqui. `""` do Combobox/Select do formulário nunca é
// enviado ao backend: a fronteira é só `slaRegraDraftParaPayload`, abaixo.
//
// `GET /slas` sem `status` OCULTA arquivado (mesmo comportamento de `/modelos-campanha`) —
// não existe forma de trazer os 3 status numa única chamada; ver `listSlaRegrasReais`.

function slaRegraDraftParaPayload(draft: SlaRegraFormDraft) {
  return {
    nome: draft.nome.trim(),
    descricao: draft.descricao.trim() || null,
    prioridadeAlvo: draft.prioridadeAlvo || null,
    departamentoId: draft.departamentoId || null,
    clienteId: draft.clienteId || null,
    prioridadeRegra: draft.prioridadeRegra,
    prazoPrimeiraRespostaQuantidade: draft.prazoPrimeiraRespostaQuantidade,
    prazoPrimeiraRespostaUnidade: draft.prazoPrimeiraRespostaUnidade,
    prazoResolucaoQuantidade: draft.prazoResolucaoQuantidade,
    prazoResolucaoUnidade: draft.prazoResolucaoUnidade,
    considerarApenasExpediente: draft.considerarApenasExpediente,
  };
}

export async function listSlaRegrasReais(params?: {
  status?: SlaRegraStatus;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<SlaRegra[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  query.set("limit", String(params?.limit ?? 200));
  if (params?.offset) query.set("offset", String(params.offset));
  return request<SlaRegra[]>(`/slas?${query.toString()}`);
}

// Um único POST — SlaRegraCreate não aceita `status`, e a regra sempre nasce ativa (o Switch
// ativo/inativo do form só existe em modo edição, então `draft.status` já chega "ativo" aqui).
// Nunca há PATCH de status encadeado após o create.
export async function criarSlaRegraReal(draft: SlaRegraFormDraft): Promise<SlaRegra> {
  return request<SlaRegra>("/slas", {
    method: "POST",
    body: JSON.stringify(slaRegraDraftParaPayload(draft)),
  });
}

export async function atualizarSlaRegraReal(slaRegraId: string, draft: SlaRegraFormDraft): Promise<SlaRegra> {
  return request<SlaRegra>(`/slas/${slaRegraId}`, {
    method: "PATCH",
    body: JSON.stringify({ ...slaRegraDraftParaPayload(draft), status: draft.status }),
  });
}

export async function arquivarSlaRegraReal(slaRegraId: string, motivoArquivamento: string): Promise<SlaRegra> {
  return request<SlaRegra>(`/slas/${slaRegraId}/arquivar`, {
    method: "POST",
    body: JSON.stringify({ motivoArquivamento }),
  });
}

export async function restaurarSlaRegraReal(slaRegraId: string): Promise<SlaRegra> {
  return request<SlaRegra>(`/slas/${slaRegraId}/restaurar`, { method: "POST" });
}

// ---------------------------------------------------------------------------------
// Configuração de e-mail — singleton por Empresa (Fase 2G.7B1 backend / 2G.7B2 UI)
// ---------------------------------------------------------------------------------
//
// `ConfiguracaoEmailRead` do backend já devolve exatamente o formato de
// `ConfiguracaoEmailRead` (camelCase via alias Pydantic) — sem mapeamento aqui. `""` dos
// inputs do formulário nunca é enviado ao backend: a fronteira é só
// `configuracaoEmailDraftParaPayload`, abaixo.
//
// `smtpSenha` tem uma fronteira própria, diferente dos outros campos: usa `undefined` (não
// `null`) pra representar "omitido" — `JSON.stringify` remove chaves `undefined` do corpo
// enviado, que é exatamente o que faz o backend preservar o ciphertext atual (ver
// ConfiguracaoEmailUpdate no backend, semântica de três estados). Nunca enviar `smtpSenha:
// ""` — o backend rejeita com 422.

function configuracaoEmailDraftParaPayload(draft: ConfiguracaoEmailFormDraft) {
  return {
    smtpHost: draft.smtpHost.trim() || null,
    smtpPort: draft.smtpPort.trim() ? Number(draft.smtpPort) : null,
    smtpUsuario: draft.smtpUsuario.trim() || null,
    smtpSenha: draft.removerSenha ? null : draft.smtpSenha.trim() ? draft.smtpSenha : undefined,
    remetenteEmail: draft.remetenteEmail.trim() || null,
    remetenteNome: draft.remetenteNome.trim() || null,
    usarTls: draft.usarTls,
    usarSsl: draft.usarSsl,
    ativo: draft.ativo,
  };
}

export async function obterConfiguracaoEmailReal(): Promise<ConfiguracaoEmailRead> {
  return request<ConfiguracaoEmailRead>("/configuracoes/email");
}

export async function atualizarConfiguracaoEmailReal(
  draft: ConfiguracaoEmailFormDraft,
): Promise<ConfiguracaoEmailRead> {
  return request<ConfiguracaoEmailRead>("/configuracoes/email", {
    method: "PATCH",
    body: JSON.stringify(configuracaoEmailDraftParaPayload(draft)),
  });
}

// Sem body — o endpoint usa só a configuração já persistida (nunca um draft arbitrário, ver
// docstring do backend sobre a mitigação de SSRF).
export async function testarConfiguracaoEmailReal(): Promise<ConfiguracaoEmailTesteResultado> {
  return request<ConfiguracaoEmailTesteResultado>("/configuracoes/email/testar", { method: "POST" });
}

// ---------------------------------------------------------------------------------
// Configuração de numeração de tarefas — leitura real, sem escrita (Fase 2G.8B)
// ---------------------------------------------------------------------------------
//
// Representa `numero_operacional` (contínuo, sem ano — ver types/configuracao-numeracao-
// tarefa.ts), nunca `codigoReferencia`. Só GET: não existe PATCH nem endpoint de ajuste —
// o único mecanismo de inicialização do contador é o CLI administrativo do backend.

export async function obterNumeracaoTarefaReal(): Promise<ConfiguracaoNumeracaoTarefaRead> {
  return request<ConfiguracaoNumeracaoTarefaRead>("/configuracoes/numeracao-tarefas");
}


// ── Personalização visual (Configurações → Personalizar) ──────────────────────────────────────────
// A Empresa vem SEMPRE do token (cookie de sessão no proxy) — nenhum empresaId é enviado.
export async function obterPersonalizacaoReal(): Promise<Branding> {
  return normalizarBranding(await request<unknown>("/configuracoes/personalizacao"));
}

export async function atualizarPersonalizacaoReal(payload: PersonalizacaoUpdatePayload): Promise<Branding> {
  return normalizarBranding(
    await request<unknown>("/configuracoes/personalizacao", { method: "PATCH", body: JSON.stringify(payload) }),
  );
}

/** Restaurar padrão: remove logo e devolve cores/tema ao padrão — não mexe em nenhuma outra configuração. */
export async function restaurarPersonalizacaoPadraoReal(): Promise<Branding> {
  return normalizarBranding(await request<unknown>("/configuracoes/personalizacao", { method: "DELETE" }));
}

export async function removerLogoPersonalizacaoReal(): Promise<Branding> {
  return normalizarBranding(await request<unknown>("/configuracoes/personalizacao/logo", { method: "DELETE" }));
}

// Upload multipart — não passa por `request()` (que força JSON e destruiria o boundary do FormData).
export async function enviarLogoPersonalizacaoReal(arquivo: File): Promise<Branding> {
  const formData = new FormData();
  formData.append("arquivo", arquivo);
  const response = await fetch("/api/backend/configuracoes/personalizacao/logo", {
    method: "POST",
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : (detail?.message ?? data?.message);
    throw new Error(message ?? `Erro ${response.status}`);
  }
  return normalizarBranding(await response.json());
}
