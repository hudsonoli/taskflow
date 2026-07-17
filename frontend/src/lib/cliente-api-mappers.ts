import type {
  ClienteApiResponse,
  ClienteCreatePayload,
  ClienteStatus,
  ClienteTipoPessoa,
  ClienteUpdatePayload,
} from "../types/cliente-api";
import type { Cliente, ClienteStatusLabel } from "../types/cliente-domain";
import type { ClienteDraft } from "../types/cliente";

export type ClientePayloadDraft = Pick<
  ClienteDraft,
  | "empresaId"
  | "codigoInterno"
  | "tipoDocumento"
  | "documento"
  | "nomeRazaoSocial"
  | "nomeFantasia"
  | "sigla"
  | "email"
  | "telefone"
  | "celular"
  | "site"
> & {
  agenciaId?: string | null;
  codigoExterno?: string | null;
  observacoes?: string | null;
};

const STATUS_LABELS: Record<ClienteStatus, ClienteStatusLabel> = {
  ativo: "Ativo",
  suspenso: "Suspenso",
  inativo: "Inativo",
};

function optionalText(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized || null;
}

function mapTipoPessoa(draft: ClientePayloadDraft): ClienteTipoPessoa {
  return draft.tipoDocumento === "cpf" ? "fisica" : "juridica";
}

function mapSupportedDraftFields(draft: ClientePayloadDraft) {
  const tipoPessoa = mapTipoPessoa(draft);
  const nomeRazaoSocial = optionalText(draft.nomeRazaoSocial);

  return {
    agenciaId: draft.agenciaId ?? null,
    codigoInterno: draft.codigoInterno.trim(),
    tipoPessoa,
    documento: normalizeClienteDocumento(draft.documento),
    razaoSocial: tipoPessoa === "juridica" ? nomeRazaoSocial : null,
    nomeFantasia: optionalText(draft.nomeFantasia),
    nome: tipoPessoa === "fisica" ? nomeRazaoSocial : null,
    sigla: optionalText(draft.sigla),
    email: optionalText(draft.email),
    telefone: optionalText(draft.telefone),
    celular: optionalText(draft.celular),
    site: optionalText(draft.site),
    codigoExterno: optionalText(draft.codigoExterno),
    observacoes: optionalText(draft.observacoes),
  };
}

export function normalizeClienteDocumento(value: string | null | undefined): string | null {
  if (!value) return null;
  const digits = value.replace(/\D/g, "");
  return digits || null;
}

export function mapClienteStatusLabel(status: ClienteStatus): ClienteStatusLabel {
  return STATUS_LABELS[status];
}

export function mapClienteApiResponseToDomain(response: ClienteApiResponse): Cliente {
  return {
    id: response.id,
    empresaId: response.empresaId,
    agenciaId: response.agenciaId,
    codigoInterno: response.codigoInterno,
    tipoPessoa: response.tipoPessoa,
    tipoDocumento: response.tipoPessoa === "fisica" ? "cpf" : "cnpj",
    documento: response.documento,
    razaoSocial: response.razaoSocial,
    nomeFantasia: response.nomeFantasia,
    nome: response.nome,
    nomePrincipal:
      response.nomeFantasia ??
      response.razaoSocial ??
      response.nome ??
      response.codigoInterno,
    sigla: response.sigla,
    email: response.email,
    telefone: response.telefone,
    celular: response.celular,
    site: response.site,
    codigoExterno: response.codigoExterno,
    observacoes: response.observacoes,
    status: response.status,
    statusLabel: mapClienteStatusLabel(response.status),
    statusAlteradoAt: response.statusAlteradoAt,
    statusAlteradoPorUsuarioId: response.statusAlteradoPorUsuarioId,
    motivoStatus: response.motivoStatus,
    createdAt: response.createdAt,
    updatedAt: response.updatedAt,
  };
}

export function mapClienteDraftToCreatePayload(
  draft: ClientePayloadDraft
): ClienteCreatePayload {
  return {
    empresaId: draft.empresaId,
    ...mapSupportedDraftFields(draft),
    status: "ativo",
  };
}

export function mapClienteDraftToUpdatePayload(
  draft: ClientePayloadDraft
): ClienteUpdatePayload {
  return mapSupportedDraftFields(draft);
}
