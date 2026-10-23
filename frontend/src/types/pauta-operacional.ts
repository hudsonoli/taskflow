/**
 * Pauta operacional por ETAPA (`GET /pauta/operacional`). O servidor devolve ITENS neutros; agrupar por colaborador ou projeto é só apresentação.
 * `responsabilidadeEfetiva` é a regra central do domínio (etapa explícita → responsáveis gerais da tarefa → ninguém); `planejamento` é a janela PLANEJADA
 * da etapa (datas do calendário da empresa) — prazo nunca é geometria.
 */

export type PautaOrigemResponsabilidade = "etapa" | "tarefa" | "nenhuma";
export type PautaEstadoPlanejamento = "planejado" | "incompleto" | "nao_planejado";

export type PautaPlanejamento = {
  inicio: string | null;
  fim: string | null;
  estado: PautaEstadoPlanejamento;
  invalido: boolean;
};

export type PautaResponsabilidade = {
  origem: PautaOrigemResponsabilidade;
  usuarioIds: string[];
  departamentoIds: string[];
};

export type PautaItem = {
  etapaId: string;
  etapaNome: string;
  etapaTipo: string;
  etapaOrdem: number;
  etapaStatus: string;
  etapaAtual: boolean;
  demandaId: string;
  demandaIdentificador: string;
  demandaNome: string;
  demandaStatus: string;
  prioridade: "baixa" | "media" | "alta";
  clienteId: string | null;
  projetoId: string | null;
  /** Só na etapa atual; informação secundária (nunca posiciona a barra). */
  prazoEtapaAtual: string | null;
  planejamento: PautaPlanejamento;
  responsabilidadeEfetiva: PautaResponsabilidade;
};

export type PautaPessoa = { id: string; nome: string };

export type PautaBalde = { total: number; devolvidos: number; truncado: boolean };

export type PautaOperacional = {
  meta: { agoraServidor: string; fusoEmpresa: string; hoje: string; inicio: string; fim: string };
  totais: {
    planejadas: PautaBalde;
    incompletas: PautaBalde;
    naoPlanejadas: PautaBalde;
    planejadasAntes: number;
    planejadasDepois: number;
  };
  itens: PautaItem[];
  pessoas: PautaPessoa[];
};

export type ParametrosPautaOperacional = {
  inicio?: string;
  fim?: string;
  usuarioIds?: string[];
  departamentoIds?: string[];
  clienteIds?: string[];
  projetoIds?: string[];
  prioridades?: string[];
  busca?: string;
};
