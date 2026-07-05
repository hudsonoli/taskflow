import type {
  FornecedorCategoria,
  FornecedorDocumentoTipo,
  FornecedorDraft,
} from "@/types/fornecedor";

export const EMPRESA_PADRAO_ID = "empresa-principal";

export const categoriasFornecedor = [
  "Gráfica",
  "Brindes",
  "Comunicação Visual",
  "Fotografia",
  "Vídeo",
  "Freelancer",
  "Programação",
  "Hospedagem",
  "Impressão",
  "Transporte",
  "Outros",
] satisfies FornecedorCategoria[];

export function generateFornecedorId(): string {
  return `fornecedor-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function generateContatoId(): string {
  return `contato-fornecedor-${Date.now()}-${Math.random()
    .toString(16)
    .slice(2)}`;
}

export function generateCodigoInterno(): string {
  const numero = Math.floor(Math.random() * 10000);
  return `#${numero.toString().padStart(4, "0")}`;
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

export function detectDocumentType(
  rawValue: string
): FornecedorDocumentoTipo | null {
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
    nomeFantasia: `Fornecedor ${sufixo}`,
    nomeRazaoSocial: `Fornecedor ${sufixo} Ltda`,
  };
}

export const initialFornecedores = [
  {
    fornecedorId: "fornecedor-1",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#2001",
    tipoDocumento: "cnpj",
    documento: "12.456.789/0001-10",
    nomeRazaoSocial: "Gráfica Horizonte Ltda",
    nomeFantasia: "Gráfica Horizonte",
    sigla: "GH",
    categoria: "Gráfica",
    email: "contato@graficahorizonte.com.br",
    telefone: "(11) 3456-7890",
    celular: "(11) 99876-5432",
    site: "https://graficahorizonte.com.br",
    status: "Ativo",
    endereco: {
      cep: "01310-100",
      logradouro: "Avenida Paulista",
      numero: "1000",
      complemento: "Conjunto 42",
      bairro: "Bela Vista",
      cidade: "São Paulo",
      uf: "SP",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [
      {
        contatoId: "contato-fornecedor-1",
        nome: "Marina Alves",
        cargo: "Atendimento",
        email: "marina@graficahorizonte.com.br",
        telefone: "",
        celular: "(11) 99876-5432",
      },
    ],
    historico: [
      {
        id: "evento-fornecedor-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "05/07/2026 10:00",
        dispositivo: "Desktop - Chrome",
        ipOrigem: "192.168.0.10",
        acao: "Fornecedor criado.",
      },
    ],
    createdAt: "2026-07-05T10:00:00-03:00",
    updatedAt: "2026-07-05T10:00:00-03:00",
  },
  {
    fornecedorId: "fornecedor-2",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#2002",
    tipoDocumento: "cnpj",
    documento: "23.567.890/0001-21",
    nomeRazaoSocial: "Studio Frame Produções Ltda",
    nomeFantasia: "Studio Frame",
    sigla: "SF",
    categoria: "Vídeo",
    email: "producao@studioframe.com.br",
    telefone: "(21) 3344-5566",
    celular: "",
    site: "https://studioframe.com.br",
    status: "Ativo",
    endereco: {
      cep: "22250-040",
      logradouro: "Rua Voluntários da Pátria",
      numero: "250",
      complemento: "Sala 301",
      bairro: "Botafogo",
      cidade: "Rio de Janeiro",
      uf: "RJ",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
    createdAt: "2026-07-04T14:30:00-03:00",
    updatedAt: "2026-07-04T14:30:00-03:00",
  },
  {
    fornecedorId: "fornecedor-3",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#2003",
    tipoDocumento: "cpf",
    documento: "123.456.789-01",
    nomeRazaoSocial: "Lucas Mendes",
    nomeFantasia: "Lucas Mendes Fotografia",
    sigla: "LMF",
    categoria: "Fotografia",
    email: "lucas@lucasmendesfoto.com.br",
    telefone: "",
    celular: "(11) 99123-4567",
    site: "",
    status: "Ativo",
    endereco: {
      cep: "",
      logradouro: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "São Paulo",
      uf: "SP",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
    createdAt: "2026-07-03T09:15:00-03:00",
    updatedAt: "2026-07-03T09:15:00-03:00",
  },
  {
    fornecedorId: "fornecedor-4",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#2004",
    tipoDocumento: "cnpj",
    documento: "34.678.901/0001-32",
    nomeRazaoSocial: "Servidor Nuvem Tecnologia Ltda",
    nomeFantasia: "Servidor Nuvem",
    sigla: "SN",
    categoria: "Hospedagem",
    email: "suporte@servidornuvem.com.br",
    telefone: "0800 123 4567",
    celular: "",
    site: "https://servidornuvem.com.br",
    status: "Inativo",
    endereco: {
      cep: "",
      logradouro: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "Curitiba",
      uf: "PR",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
    createdAt: "2026-07-01T16:00:00-03:00",
    updatedAt: "2026-07-02T11:20:00-03:00",
  },
] satisfies FornecedorDraft[];
