// Máscaras de apresentação — formatação pura de entrada, sem dado de domínio.
// Reúne os helpers que viviam dentro dos mocks removidos (usuarios-mock.ts na Fase 2A,
// clientes-mock.ts na 2B): são utilitários de UI, não tinham por que morar num mock.

import type { DocumentoTipo } from "@/types/cliente";

export function formatCPF(rawValue: string): string {
  const digits = rawValue.replace(/\D/g, "").slice(0, 11);
  return digits
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d)/, "$1.$2")
    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
}

/** CPF tem 11 dígitos, CNPJ 14. Qualquer outro comprimento é indefinido, não erro. */
export function detectDocumentType(rawValue: string): DocumentoTipo | null {
  const digits = rawValue.replace(/\D/g, "");
  if (digits.length === 11) return "cpf";
  if (digits.length === 14) return "cnpj";
  return null;
}

/** Aplica máscara de CPF ou CNPJ conforme a quantidade de dígitos já digitada. */
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

/** Só os dígitos — é assim que o backend indexa o documento para busca. */
export function somenteDigitos(valor: string): string {
  return valor.replace(/\D/g, "");
}
