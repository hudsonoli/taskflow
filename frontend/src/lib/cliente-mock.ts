import {
  EMPRESA_PADRAO_ID,
  equipesDisponiveis,
  generateCodigoInterno,
  generateId,
  generateSigla,
  responsaveisDisponiveis,
} from "@/lib/equipe-mock";
import type { DocumentoTipo } from "@/types/cliente";

export {
  EMPRESA_PADRAO_ID,
  equipesDisponiveis,
  generateCodigoInterno,
  generateId,
  generateSigla,
  responsaveisDisponiveis,
};

export function detectDocumentType(rawValue: string): DocumentoTipo | null {
  const digits = rawValue.replace(/\D/g, "");

  if (digits.length === 11) return "cpf";
  if (digits.length === 14) return "cnpj";
  return null;
}

export function formatDocument(rawValue: string): string {
  const digits = rawValue.replace(/\D/g, "").slice(0, 14);

  if (digits.length <= 11) {
    return digits
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d)/, "$1.$2")
      .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
  }

  return digits
    .replace(/(\d{2})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1/$2")
    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
}

export function mockCnpjLookup(cnpjDigits: string) {
  const sufixo = cnpjDigits.slice(-4);

  return {
    nomeFantasia: `Empresa ${sufixo}`,
    nomeRazaoSocial: `Empresa ${sufixo} Ltda`,
  };
}
