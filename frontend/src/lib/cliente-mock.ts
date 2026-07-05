import type { DocumentoTipo } from "@/types/cliente";

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

export function generateSigla(nome: string): string {
  const words = nome.trim().split(/\s+/).filter(Boolean);

  if (words.length === 0) return "";
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase();

  return words
    .slice(0, 4)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export function generateCodigoInterno(): string {
  const numero = Math.floor(1000 + Math.random() * 9000);
  return `#${numero}`;
}

export function mockCnpjLookup(cnpjDigits: string) {
  const sufixo = cnpjDigits.slice(-4);

  return {
    nomeFantasia: `Empresa ${sufixo}`,
    razaoSocial: `Empresa ${sufixo} Ltda`,
  };
}
