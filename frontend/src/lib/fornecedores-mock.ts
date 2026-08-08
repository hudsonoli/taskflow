import { EMPRESA_PADRAO_ID, generateId } from "@/lib/ids";
import type { DocumentoTipo, Fornecedor, FornecedorStatus } from "@/types/fornecedor";
import fornecedoresImportadosRaw from "@/lib/fornecedores-import.json";

export { EMPRESA_PADRAO_ID, generateId };

export const statusFornecedorLabels: Record<FornecedorStatus, string> = {
  ativo: "Ativo",
  inativo: "Inativo",
};

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

function criarFornecedor(seed: string, patch: Partial<Fornecedor>): Fornecedor {
  return {
    id: `fornecedor-${seed}`,
    empresaId: EMPRESA_PADRAO_ID,
    tipoDocumento: "cnpj",
    documento: "",
    nome: "",
    categoria: "",
    contatoNome: "",
    email: "",
    whatsapp: "",
    site: "",
    cep: "",
    bairro: "",
    enderecoCompleto: "",
    cidade: "",
    uf: "",
    status: "ativo",
    observacoes: "",
    corIdentificacao: "zinc",
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-01T09:00:00-03:00",
    ...patch,
  };
}

const fornecedoresDemo: Fornecedor[] = [
  criarFornecedor("1", {
    documento: "12.345.678/0001-11",
    nome: "Gráfica Union",
    categoria: "Gráfica",
    contatoNome: "Renata Alves",
    email: "contato@graficaunion.com.br",
    whatsapp: "(62) 3222-1000",
    status: "ativo",
    corIdentificacao: "blue",
  }),
  criarFornecedor("2", {
    documento: "98.765.432/0001-22",
    nome: "Estúdio Vértice — Vídeo",
    categoria: "Vídeo / Produtora",
    contatoNome: "Pedro Nunes",
    email: "contato@verticevideo.com.br",
    whatsapp: "(62) 3555-2200",
    status: "ativo",
    corIdentificacao: "purple",
  }),
];

const fornecedoresImportados = fornecedoresImportadosRaw as Fornecedor[];

const nomesDemoFornecedor = new Set(fornecedoresDemo.map((fornecedor) => fornecedor.nome.trim().toLowerCase()));
const fornecedoresImportadosSemDuplicar = fornecedoresImportados.filter(
  (fornecedor) => !nomesDemoFornecedor.has(fornecedor.nome.trim().toLowerCase()),
);

export const fornecedoresMock: Fornecedor[] = [...fornecedoresDemo, ...fornecedoresImportadosSemDuplicar];
