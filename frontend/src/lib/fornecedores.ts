import type { DocumentoTipo, FornecedorStatus, FornecedorStatusEditavel } from "@/types/fornecedor";

/**
 * Auxiliares de apresentação do cadastro de Fornecedor.
 *
 * Moravam em `lib/fornecedores-mock.ts` e sobreviveram à remoção dele: são regras de
 * interface (rótulos, máscara de documento, sugestões de categoria), não dados. Nenhuma
 * delas fala com a API — persistência é responsabilidade de `lib/api-backend.ts`.
 */

export const statusFornecedorLabels: Record<FornecedorStatus, string> = {
  ativo: "Ativo",
  inativo: "Inativo",
  arquivado: "Arquivado",
};

/** Só o que o formulário pode escolher — `arquivado` entra pela rota de arquivamento. */
export const statusFornecedorEditaveis: FornecedorStatusEditavel[] = ["ativo", "inativo"];

// Categorias comuns de fornecedores de agência — sugestões, o campo aceita qualquer texto.
export const categoriasFornecedorDisponiveis = [
  "Gráfica",
  "Vídeo / Produtora",
  "Fotografia",
  "Freelancer",
  "Mídia / Tráfego",
  "Impressão / Brindes",
  "Hospedagem / TI",
  "Banco de imagens",
  "Áudio / Locução",
  "Outros",
];

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
