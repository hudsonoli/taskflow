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
 * Item do modelo de campanha — value object, vive dentro do projeto.
 *
 * `tipoTarefaId`, `workflowSugeridoId` e `responsavelOuSetorSugeridoId` são ids **legados
 * em texto**, sem relação real: TipoTarefa e Workflow ainda não migraram. Os nomes vêm
 * junto porque hoje não há de onde resolvê-los. Viram relação de verdade quando esses
 * domínios migrarem.
 */
export type ProjetoModeloCampanhaItem = {
  id: string;
  nomeDemanda: string;
  tipoTarefaId: string;
  tipoTarefaNome: string;
  briefingBase: string;
  prioridadePadrao: ProjetoPrioridade;
  workflowSugeridoId: string;
  workflowSugeridoNome: string;
  responsavelOuSetorSugeridoId: string;
  responsavelOuSetorSugeridoNome: string;
};

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
  /** Chave estável de importação/integração. Nunca exibido. */
  codigoInterno: string;
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
  modeloCampanhaId: string;
  modeloCampanha: ProjetoModeloCampanhaItem[];
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
  | "modeloCampanha"
> & { status: ProjetoStatusEditavel };
