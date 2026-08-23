export type PecaStatus = "ativo" | "inativo" | "arquivado";

export type Peca = {
  id: string;
  empresaId: string;
  nome: string;
  categoriaId: string | null;
  // Resolvido pelo backend via join — nunca calculado no cliente (ver PecaService.to_read).
  categoriaNome: string | null;
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
  status: PecaStatus;
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  arquivadoPorUsuarioId: string | null;
  motivoArquivamento: string | null;
  restauradoAt: string | null;
  restauradoPorUsuarioId: string | null;
};

// Full-replace parcial (PATCH aceita subconjunto) — o form sempre manda os campos que edita;
// `categoriaId` pode ser `null` (sem categoria) ou omitido (não mexe).
export type PecaFormDraft = {
  nome: string;
  categoriaId: string | null;
  tempoEstimadoMinutos: number | null;
  tempoMedioMinutos: number | null;
  valorTabelaCentavos: number | null;
  sindicatoAtivo: boolean;
  valorSindicatoCriacaoCentavos: number | null;
  valorSindicatoAdaptacaoCentavos: number | null;
  valorSindicatoFinalizacaoCentavos: number | null;
  briefingPadrao: string;
  status: PecaStatus;
};

// Projeção mínima do diretório (GET /pecas/diretorio) — contrato pronto pra um futuro
// consumidor operacional, ainda sem uso nesta fase.
export type PecaDiretorioItem = {
  id: string;
  nome: string;
};
