export type DocumentoTipo = "cnpj" | "cpf";

export type ClienteStatus = "ativo" | "suspenso" | "inativo";

export type ClienteHistoricoEvento = {
  id: string;
  usuarioId: string;
  usuario: string;
  acao: string;
  dataHora: string;
  ip: string;
  dispositivo: string;
};

export type ClienteContato = {
  id: string;
  nome: string;
  email: string;
  telefone: string;
  cargo: string;
  // Recebe o aviso/e-mail de conclusão quando uma demanda deste cliente é finalizada.
  recebeEntregas: boolean;
};

export type Cliente = {
  id: string;
  empresaId: string;
  codigoInterno: string;
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
  tagIds: string[];
  origem: string;
  status: ClienteStatus;
  responsavelComercialId: string;
  clienteReferencial: boolean;
  contatos: ClienteContato[];
  // Ao concluir uma demanda deste cliente, oferece o aviso de envio do trabalho finalizado.
  avisarConclusaoPorEmail: boolean;
  // Visível apenas para perfis com acesso financeiro (ver podeVerDadosFinanceiros).
  feeMensal: number | null;
  horasContratadasMes: number | null;
  observacoes: string;
  corIdentificacao: string;
  createdAt: string;
  updatedAt: string;
  historico: ClienteHistoricoEvento[];
};

export type ClienteFormDraft = Omit<Cliente, "id" | "empresaId" | "codigoInterno" | "createdAt" | "updatedAt" | "historico">;
