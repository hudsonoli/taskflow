import type { ClienteStatus, ClienteTipoPessoa } from "./cliente-api";

export type ClienteStatusLabel = "Ativo" | "Suspenso" | "Inativo";

export type ClienteDocumentoTipo = "cpf" | "cnpj";

export type Cliente = {
  id: string;
  empresaId: string;
  agenciaId: string | null;
  codigoInterno: string;
  tipoPessoa: ClienteTipoPessoa;
  tipoDocumento: ClienteDocumentoTipo;
  documento: string | null;
  razaoSocial: string | null;
  nomeFantasia: string | null;
  nome: string | null;
  nomePrincipal: string;
  sigla: string | null;
  email: string | null;
  telefone: string | null;
  celular: string | null;
  site: string | null;
  codigoExterno: string | null;
  observacoes: string | null;
  status: ClienteStatus;
  statusLabel: ClienteStatusLabel;
  statusAlteradoAt: string | null;
  statusAlteradoPorUsuarioId: string | null;
  motivoStatus: string | null;
  createdAt: string;
  updatedAt: string;
};
