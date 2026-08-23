export type CategoriaPecaStatus = "ativo" | "arquivado";

export type CategoriaPeca = {
  id: string;
  empresaId: string;
  nome: string;
  ordem: number;
  status: CategoriaPecaStatus;
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  arquivadoPorUsuarioId: string | null;
  motivoArquivamento: string | null;
  restauradoAt: string | null;
  restauradoPorUsuarioId: string | null;
};

export type CategoriaPecaFormDraft = {
  nome: string;
  ordem?: number;
};

// Projeção mínima do diretório (GET /categorias-peca/diretorio) — só categorias ativas,
// usada no seletor do formulário de Peça.
export type CategoriaPecaDiretorioItem = {
  id: string;
  nome: string;
};
