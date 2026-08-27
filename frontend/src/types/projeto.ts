export type ProjetoStatus =
  | "planejamento"
  | "ativo"
  | "pausado"
  | "concluido"
  | "cancelado"
  | "arquivado";

/** `arquivado` entra pela ação de arquivar, com motivo — nunca é escolhido no formulário. */
export type ProjetoStatusEditavel = Exclude<ProjetoStatus, "arquivado">;

export type ProjetoPrioridade = "baixa" | "media" | "alta";

/**
 * Pessoa alocada ao projeto. `funcao` é atributo do **vínculo**, não da pessoa — a mesma
 * pessoa pode ser direção de arte num projeto e revisora em outro.
 *
 * O mock replicava `nome`, `departamentoId` e `departamentoNome` dentro de cada membro.
 * Isso saiu: nome e departamento vêm do diretório de usuários. Duplicá-los criaria dois
 * lugares para a mesma verdade — o cadastro muda, a cópia não.
 */
export type ProjetoEquipeMembro = {
  usuarioId: string;
  funcao: string;
};

export type Projeto = {
  id: string;
  empresaId: string;
  /** Identidade de negócio: P26000001. Imutável, pesquisável. */
  codigoReferencia: string;
  anoReferencia: number;
  /** O número que aparece no rótulo (ver lib/formatarReferencia.ts). */
  sequencialReferencia: number;
  nome: string;
  campanha: string;
  descricao: string;
  resumo: string;
  status: ProjetoStatus;
  prioridade: ProjetoPrioridade;
  /** Vazio em projeto interno da agência. */
  clienteId: string;
  dataInicio: string;
  dataFimPrevista: string;
  responsavelIds: string[];
  departamentoResponsavelIds: string[];
  equipe: ProjetoEquipeMembro[];
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  motivoArquivamento: string | null;
};

/**
 * O que o formulário edita. Fora dele ficam os campos que o backend controla: identidade,
 * códigos e auditoria.
 *
 * `agenciaId`, `historico[]` e `arquivos[]` saíram do modelo: o primeiro era constante sem
 * entidade, o segundo virou evento de domínio (`projeto.*`) e o terceiro depende de upload,
 * que é fase própria.
 */
export type ProjetoFormDraft = Pick<
  Projeto,
  | "nome"
  | "clienteId"
  | "campanha"
  | "descricao"
  | "resumo"
  | "prioridade"
  | "dataInicio"
  | "dataFimPrevista"
  | "responsavelIds"
  | "departamentoResponsavelIds"
  | "equipe"
> & { status: ProjetoStatusEditavel };
