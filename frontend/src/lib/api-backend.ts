import type { PerfilUsuario, Usuario, UsuarioFormDraft } from "@/types/usuario";
import type { GrupoCliente, GrupoClienteStatus } from "@/types/grupo-cliente";
import type { Departamento, DepartamentoFormDraft, DepartamentoStatus } from "@/types/departamento";
import type { Equipe, EquipeFormDraft, EquipeStatus } from "@/types/equipe";

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
// propósito, pra Cliente.tagIds antigos continuarem resolvendo nome/cor (ver
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
