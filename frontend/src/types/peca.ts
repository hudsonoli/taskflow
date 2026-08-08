export type Peca = {
  id: string;
  empresaId: string;
  nome: string;
  categoria: string;
  tempoEstimadoMinutos: number | null;
  // Tempo médio de referência (histórico/importado) para este tipo de peça.
  tempoMedioMinutos: number | null;
  // Calculado a partir de sessões de trabalho reais vinculadas a esta peça. Fica null até
  // existir vínculo Demanda→Peça no modelo de dados (ainda não existe nesta fase) — nunca
  // deve ser preenchido com valor aproximado/inventado.
  tempoCalculadoExecucaoMinutos: number | null;
  // Visível apenas para perfis com acesso financeiro (ver podeVerDadosFinanceiros).
  valorTabelaCentavos: number | null;
  // Liga/desliga se esta peça tem valores de sindicato — quando false, os valores abaixo
  // não se aplicam (mesmo que tenham ficado preenchidos de um cadastro anterior).
  sindicatoAtivo: boolean;
  valorSindicatoCriacaoCentavos: number | null;
  valorSindicatoAdaptacaoCentavos: number | null;
  valorSindicatoFinalizacaoCentavos: number | null;
  briefingPadrao: string;
  ativa: boolean;
  createdAt: string;
  updatedAt: string;
};

export type PecaFormDraft = Omit<Peca, "id" | "empresaId" | "createdAt" | "updatedAt">;
