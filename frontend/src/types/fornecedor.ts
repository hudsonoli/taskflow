export type DocumentoTipo = "cnpj" | "cpf";

export type FornecedorStatus = "ativo" | "inativo";

export type Fornecedor = {
  id: string;
  empresaId: string;
  tipoDocumento: DocumentoTipo;
  documento: string;
  nome: string;
  categoria: string;
  contatoNome: string;
  email: string;
  whatsapp: string;
  site: string;
  cep: string;
  bairro: string;
  enderecoCompleto: string;
  cidade: string;
  uf: string;
  status: FornecedorStatus;
  observacoes: string;
  corIdentificacao: string;
  createdAt: string;
  updatedAt: string;
};

export type FornecedorFormDraft = Omit<Fornecedor, "id" | "empresaId" | "createdAt" | "updatedAt">;
