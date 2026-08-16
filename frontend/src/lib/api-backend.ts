import type { PerfilUsuario, Usuario, UsuarioFormDraft } from "@/types/usuario";
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
import type {
  Projeto,
  ProjetoFormDraft,
  ProjetoModeloCampanhaItem,
  ProjetoPrioridade,
  ProjetoStatus,
} from "@/types/projeto";
import type {
  Demanda,
  DemandaArquivo,
  DemandaChecklistItem,
  DemandaComentario,
  DemandaDiretorio,
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

export class ProjetoArquivadoConflictError extends Error {
  projetoArquivadoId: string;

  constructor(message: string, projetoArquivadoId: string) {
    super(message);
    this.name = "ProjetoArquivadoConflictError";
    this.projetoArquivadoId = projetoArquivadoId;
  }
}

export type JanelaExpediente = {
  manhaInicio: string;
  manhaFim: string;
  tardeInicio: string;
  tardeFim: string;
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

export type UsuarioPerfilBaseApi = "admin" | "gestor" | "operador";

// perfil_base real só aceita 3 valores — mapeamento usado tanto no seed (backend) quanto
// aqui: superadmin|diretoria -> admin, financeiro -> gestor, cliente -> operador. Ver
// "Limitação conhecida" no plano da Fase 1 — o rótulo rico do mock não é preservado no
// backend real ainda, só a permissão equivalente mais próxima.
export const PERFIL_PARA_PERFIL_BASE: Record<PerfilUsuario, UsuarioPerfilBaseApi> = {
  superadmin: "admin",
  admin: "admin",
  diretoria: "admin",
  financeiro: "gestor",
  gestor: "gestor",
  operador: "operador",
  cliente: "operador",
};

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

export async function listUsuariosReais(empresaId: string): Promise<Usuario[]> {
  const data = await request<UsuarioReadApi[]>(`/usuarios?empresaId=${encodeURIComponent(empresaId)}&limit=200`);
  return data.map(mapUsuarioReadToUsuario);
}

// Autoedição de perfil (tela "Minha Conta") — PATCH direto, só os campos que a própria
// pessoa pode alterar de si mesma (nome, cargo, cor, foto). Sem passar pelo draft completo
// de UsuarioFormDraft (que é do cadastro administrativo).
export async function atualizarPerfilProprio(
  usuarioId: string,
  patch: { nome?: string; cargo?: string | null; corIdentificacao?: string | null; fotoUrl?: string | null },
): Promise<Usuario> {
  const updated = await request<UsuarioReadApi>(`/usuarios/${usuarioId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  return mapUsuarioReadToUsuario(updated);
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

export async function listDiretorioUsuarios(): Promise<UsuarioDiretorioItem[]> {
  const data = await request<UsuarioDiretorioApi[]>("/usuarios/diretorio?limit=200");
  // Normaliza null -> undefined pros componentes de UI (Avatar/MemberSelector etc.) que
  // esperam `string | undefined`, não `string | null` — um só lugar, não em cada consumidor.
  return data.map((usuario) => ({
    ...usuario,
    cargo: usuario.cargo ?? undefined,
    departamentoId: usuario.departamentoId ?? undefined,
    fotoUrl: usuario.fotoUrl ?? undefined,
    corIdentificacao: usuario.corIdentificacao ?? undefined,
  }));
}

export async function criarUsuarioReal(draft: UsuarioFormDraft, empresaId: string, codigoInterno: string): Promise<Usuario> {
  const created = await request<UsuarioReadApi>("/usuarios", {
    method: "POST",
    body: JSON.stringify({ ...draftParaPayload(draft), empresaId, codigoInterno, acessoSistema: true }),
  });
  if (!draft.ativo) {
    await request(`/usuarios/${created.id}/inativar`, { method: "POST", body: JSON.stringify({}) });
    return { ...mapUsuarioReadToUsuario(created), ativo: false };
  }
  return mapUsuarioReadToUsuario(created);
}

export async function atualizarUsuarioReal(usuarioId: string, draft: UsuarioFormDraft, ativoAnterior: boolean): Promise<Usuario> {
  const updated = await request<UsuarioReadApi>(`/usuarios/${usuarioId}`, {
    method: "PATCH",
    body: JSON.stringify(draftParaPayload(draft)),
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
  modeloCampanhaId: string | null;
  modeloCampanha: ProjetoModeloCampanhaItem[];
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
    modeloCampanhaId: data.modeloCampanhaId ?? "",
    modeloCampanha: data.modeloCampanha ?? [],
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
    modeloCampanha: draft.modeloCampanha,
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

export type DemandaEscopo = "meus" | "meu-departamento" | "atendimento";

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
    usuarioResponsavelIds: draft.usuarioResponsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
  };
}

export async function listDemandasReais(params?: {
  status?: string;
  search?: string;
  clienteId?: string;
  projetoId?: string;
  departamentoId?: string;
  escopo?: DemandaEscopo;
}): Promise<Demanda[]> {
  const query = new URLSearchParams({ limit: "200" });
  if (params?.status) query.set("status", params.status);
  if (params?.search) query.set("search", params.search);
  if (params?.clienteId) query.set("clienteId", params.clienteId);
  if (params?.projetoId) query.set("projetoId", params.projetoId);
  if (params?.departamentoId) query.set("departamentoId", params.departamentoId);
  if (params?.escopo) query.set("escopo", params.escopo);
  const data = await request<DemandaReadApi[]>(`/demandas?${query.toString()}`);
  return data.map(mapDemandaReadToDemanda);
}

export async function getDemandaReal(demandaId: string): Promise<Demanda> {
  return mapDemandaReadToDemanda(await request<DemandaReadApi>(`/demandas/${demandaId}`));
}

export async function listDiretorioDemandas(): Promise<DemandaDiretorio[]> {
  return request<DemandaDiretorio[]>("/demandas/diretorio");
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

export async function listChecklistDemanda(demandaId: string): Promise<DemandaChecklistItem[]> {
  const itens = await request<DemandaChecklistItemReadApi[]>(`/demandas/${demandaId}/checklist`);
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
  nomeOriginal: string;
  contentType: string | null;
  tamanhoBytes: number;
  enviadoPorUsuarioId: string | null;
  createdAt: string;
};

function mapArquivoReadToArquivo(data: DemandaArquivoReadApi): DemandaArquivo {
  return { ...data };
}

export async function listArquivosDemanda(demandaId: string): Promise<DemandaArquivo[]> {
  const arquivos = await request<DemandaArquivoReadApi[]>(`/demandas/${demandaId}/arquivos`);
  return arquivos.map(mapArquivoReadToArquivo);
}

// Upload é multipart — `request()` força `Content-Type: application/json`, o que destruiria
// o boundary do FormData (mesma razão documentada no proxy, ver
// src/app/api/backend/[...path]/route.ts). Por isso fala com `fetch` diretamente.
export async function uploadArquivoDemanda(demandaId: string, file: File): Promise<DemandaArquivo> {
  const formData = new FormData();
  formData.append("file", file);
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

export async function excluirArquivoDemanda(demandaId: string, arquivoId: string): Promise<void> {
  await request<null>(`/demandas/${demandaId}/arquivos/${arquivoId}`, { method: "DELETE" });
}

// Usada direto num `<a href>` — o proxy lê o cookie de sessão, então o navegador autentica
// a navegação normalmente, sem JS extra. Nunca aponta pro FastAPI direto.
export function urlDownloadArquivoDemanda(demandaId: string, arquivoId: string): string {
  return `/api/backend/demandas/${demandaId}/arquivos/${arquivoId}/download`;
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
  texto: string;
  createdAt: string;
  updatedAt: string;
  editadoEm: string | null;
};

function mapComentarioReadToComentario(data: DemandaComentarioReadApi): DemandaComentario {
  return { ...data };
}

export async function listComentariosDemanda(demandaId: string): Promise<DemandaComentario[]> {
  const comentarios = await request<DemandaComentarioReadApi[]>(`/demandas/${demandaId}/comentarios`);
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

export async function listHistoricoDemanda(demandaId: string): Promise<DemandaHistoricoEvento[]> {
  const eventos = await request<DemandaHistoricoEventoReadApi[]>(`/demandas/${demandaId}/historico`);
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
