export type DocumentoTipo = "cnpj" | "cpf";

/** `arquivado` não é escolhido no formulário — entra pela ação de arquivar. */
export type ClienteStatus = "ativo" | "suspenso" | "inativo" | "arquivado";
export type ClienteStatusEditavel = Exclude<ClienteStatus, "arquivado">;

export const statusClienteLabels: Record<ClienteStatus, string> = {
  ativo: "Ativo",
  suspenso: "Suspenso",
  inativo: "Inativo",
  arquivado: "Arquivado",
};

export const origensClienteDisponiveis = [
  "Indicação",
  "Prospecção ativa",
  "Site/Formulário",
  "Redes sociais",
  "Evento",
  "Outro",
];

export type ClienteContato = {
  id: string;
  nome: string;
  email: string;
  telefone: string;
  cargo: string;
  // Recebe o aviso/e-mail de conclusão quando uma demanda deste cliente é finalizada.
  recebeEntregas: boolean;
};

/**
 * Motivo da semelhança com um cliente já existente. Lista fechada: a interface decide a
 * apresentação sem interpretar texto livre.
 */
export type MotivoPossivelDuplicidade = "nome" | "documento" | "nome_documento";

/**
 * Cliente já cadastrado parecido com o que acabou de ser gravado.
 *
 * **Informativo, nunca bloqueio.** Nome e documento não são identidade em Cliente — filiais
 * homônimas com CNPJ distinto e empreendimentos distintos sob o mesmo CNPJ são cadastros
 * legítimos (ver docs/padrao-entidades-externas.md). A criação sempre acontece; isto só
 * permite avisar o operador. Nunca fazer merge automático nem alterar o registro existente.
 */
export type PossivelDuplicidadeCliente = {
  id: string;
  codigoReferencia: string;
  nome: string;
  documento: string | null;
  status: ClienteStatus;
  motivo: MotivoPossivelDuplicidade;
};

export type Cliente = {
  /** UUID técnico — usado em rotas e relações. Nunca exibido. */
  id: string;
  empresaId: string;
  /** Ponte de importação (`#2001`). Não editável, não aceito pela API pública. */
  codigoInterno: string;
  /** Identidade funcional (`C26000001`) — imutável e pesquisável. */
  codigoReferencia: string;
  anoReferencia: number;
  /** Exibido como `#1 — Nome do Cliente`. */
  sequencialReferencia: number;
  logoUrl?: string;
  tipoDocumento: DocumentoTipo;
  documento: string;
  nome: string;
  razaoSocial: string;
  email: string;
  whatsapp: string;
  cep: string;
  bairro: string;
  enderecoCompleto: string;
  cidade: string;
  uf: string;
  segmento: string;
  /** UUIDs reais de GrupoCliente — o vínculo N:N vive em tabela própria no backend. */
  grupoClienteIds: string[];
  origem: string;
  status: ClienteStatus;
  responsavelComercialId: string;
  clienteReferencial: boolean;
  contatos: ClienteContato[];
  // Ao concluir uma demanda deste cliente, oferece o aviso de envio do trabalho finalizado.
  avisarConclusaoPorEmail: boolean;
  // Visível apenas para perfis com acesso financeiro (ver podeVerDadosFinanceiros).
  // Centavos como inteiro: dinheiro nunca em float.
  feeMensalCentavos: number | null;
  horasContratadasMes: number | null;
  observacoes: string;
  corIdentificacao: string;
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  motivoArquivamento: string | null;
  /**
   * Só vem preenchido nas respostas de criação e alteração — em listagem seria uma consulta
   * por linha sem serventia.
   */
  possiveisDuplicidades: PossivelDuplicidadeCliente[];
};

/** O que o formulário edita. Códigos, empresa e auditoria são responsabilidade do backend. */
export type ClienteFormDraft = {
  nome: string;
  razaoSocial: string;
  tipoDocumento: DocumentoTipo;
  documento: string;
  email: string;
  whatsapp: string;
  cep: string;
  bairro: string;
  enderecoCompleto: string;
  cidade: string;
  uf: string;
  segmento: string;
  grupoClienteIds: string[];
  origem: string;
  status: ClienteStatusEditavel;
  responsavelComercialId: string;
  clienteReferencial: boolean;
  contatos: ClienteContato[];
  avisarConclusaoPorEmail: boolean;
  feeMensalCentavos: number | null;
  horasContratadasMes: number | null;
  observacoes: string;
  corIdentificacao: string;
  logoUrl: string;
};
