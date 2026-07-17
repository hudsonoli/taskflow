export type ClienteStatus = "ativo" | "suspenso" | "inativo";

export type ClienteTipoPessoa = "fisica" | "juridica";

export type ClienteApiResponse = {
  id: string;
  empresaId: string;
  agenciaId: string | null;
  codigoInterno: string;
  tipoPessoa: ClienteTipoPessoa;
  documento: string | null;
  razaoSocial: string | null;
  nomeFantasia: string | null;
  nome: string | null;
  sigla: string | null;
  email: string | null;
  telefone: string | null;
  celular: string | null;
  site: string | null;
  codigoExterno: string | null;
  observacoes: string | null;
  status: ClienteStatus;
  statusAlteradoAt: string | null;
  statusAlteradoPorUsuarioId: string | null;
  motivoStatus: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ClienteCreatePayload = {
  empresaId: string;
  agenciaId?: string | null;
  codigoInterno: string;
  tipoPessoa: ClienteTipoPessoa;
  documento?: string | null;
  razaoSocial?: string | null;
  nomeFantasia?: string | null;
  nome?: string | null;
  sigla?: string | null;
  email?: string | null;
  telefone?: string | null;
  celular?: string | null;
  site?: string | null;
  codigoExterno?: string | null;
  observacoes?: string | null;
  status?: "ativo";
};

export type ClienteUpdatePayload = {
  agenciaId?: string | null;
  codigoInterno?: string;
  tipoPessoa?: ClienteTipoPessoa;
  documento?: string | null;
  razaoSocial?: string | null;
  nomeFantasia?: string | null;
  nome?: string | null;
  sigla?: string | null;
  email?: string | null;
  telefone?: string | null;
  celular?: string | null;
  site?: string | null;
  codigoExterno?: string | null;
  observacoes?: string | null;
};

export type ClienteListParams = {
  status?: ClienteStatus;
  tipoPessoa?: ClienteTipoPessoa;
  agenciaId?: string;
  busca?: string;
  limit?: number;
  offset?: number;
};

export type ClienteSuspenderPayload = {
  motivo: string;
};

export type ClienteReativarPayload = {
  motivo?: string | null;
};

export type ClienteInativarPayload = {
  motivo: string;
};
