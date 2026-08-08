export type DocumentoTipo = "cnpj" | "cpf";

/**
 * Sem `suspenso`, ao contrário de Cliente — decisão registrada em
 * backend/app/models/fornecedor.py. `arquivado` existe por causa do soft-delete e nunca é
 * escolhido no formulário: entra pela rota de arquivamento, com motivo.
 */
export type FornecedorStatus = "ativo" | "inativo" | "arquivado";

export type FornecedorStatusEditavel = Exclude<FornecedorStatus, "arquivado">;

/** Motivo da semelhança — lista fechada, espelha o backend. */
export type MotivoPossivelDuplicidade = "nome" | "documento" | "nome_documento";

/**
 * Cadastro já existente parecido com o que acabou de ser salvo.
 *
 * Informativo, nunca bloqueio: em Fornecedor, como em Cliente, nome e documento não são
 * identidade (ver docs/padrao-entidades-externas.md). A API responde 201 e devolve isto
 * junto; a interface só sinaliza.
 */
export type PossivelDuplicidadeFornecedor = {
  id: string;
  codigoReferencia: string;
  /** Vem pronto da API para o rótulo `#12-Nome` — nunca recortar `codigoReferencia`. */
  sequencialReferencia: number;
  nome: string;
  documento: string | null;
  status: FornecedorStatus;
  motivo: MotivoPossivelDuplicidade;
};

export type Fornecedor = {
  id: string;
  empresaId: string;
  /** Ponte de migração — chave de idempotência do seed. Nunca exibido. */
  codigoInterno: string;
  /** Identidade de negócio: F26000001. Imutável, pesquisável. */
  codigoReferencia: string;
  anoReferencia: number;
  /** O número que aparece no rótulo (ver lib/formatarReferencia.ts). */
  sequencialReferencia: number;
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
  arquivadoAt: string | null;
  motivoArquivamento: string | null;
  /** Preenchido só nas respostas de criação e alteração. */
  possiveisDuplicidades: PossivelDuplicidadeFornecedor[];
};

/**
 * O que o formulário edita. Fora dele ficam os campos que o backend controla: identidade,
 * códigos, auditoria e os avisos de duplicidade.
 */
export type FornecedorFormDraft = Omit<
  Fornecedor,
  | "id"
  | "empresaId"
  | "codigoInterno"
  | "codigoReferencia"
  | "anoReferencia"
  | "sequencialReferencia"
  | "createdAt"
  | "updatedAt"
  | "arquivadoAt"
  | "motivoArquivamento"
  | "possiveisDuplicidades"
  | "status"
> & { status: FornecedorStatusEditavel };
