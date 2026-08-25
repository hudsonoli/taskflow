export type ModeloCampanhaStatus = "ativo" | "inativo" | "arquivado";

export type PrioridadePadrao = "baixa" | "media" | "alta";

export const prioridadePadraoLabels: Record<PrioridadePadrao, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};

// Item persistido — sempre com `id` (gerado pelo servidor) e os `*Nome` resolvidos via join
// no backend (ModeloCampanhaService._resolver_nomes_itens), nunca calculados no cliente.
export type ModeloCampanhaItem = {
  id: string;
  ordem: number;
  nome: string;
  briefingPadrao: string | null;
  prioridadePadrao: PrioridadePadrao;
  pecaId: string | null;
  pecaNome: string | null;
  tipoTarefaId: string | null;
  tipoTarefaNome: string | null;
  workflowModeloId: string | null;
  workflowModeloNome: string | null;
  responsavelUsuarioId: string | null;
  responsavelUsuarioNome: string | null;
  responsavelDepartamentoId: string | null;
  responsavelDepartamentoNome: string | null;
};

export type ModeloCampanha = {
  id: string;
  empresaId: string;
  nome: string;
  descricao: string | null;
  status: ModeloCampanhaStatus;
  itens: ModeloCampanhaItem[];
  createdAt: string;
  updatedAt: string;
  arquivadoAt: string | null;
  arquivadoPorUsuarioId: string | null;
  motivoArquivamento: string | null;
  restauradoAt: string | null;
  restauradoPorUsuarioId: string | null;
};

/**
 * Item do formulário. `id` só existe para item que já veio do servidor — mantido estável
 * entre edições pra preservação histórica de referência (ver ModeloCampanhaService
 * `_preparar_itens`/`_validar_campo_referencia` no backend). Item novo nasce SEM `id`: o
 * servidor gera o UUID, o frontend nunca inventa um (ver item 16 da Fase 2G.5B).
 *
 * `clientKey` é só uma chave de reconciliação local (React `key` + estado de expandir/
 * colapsar) — nunca enviada ao backend, existe pra item novo (sem `id`) também precisar de
 * uma chave estável enquanto é editado nesta sessão do formulário.
 */
export type ModeloCampanhaItemFormDraft = {
  id?: string;
  clientKey: string;
  nome: string;
  briefingPadrao: string;
  prioridadePadrao: PrioridadePadrao;
  pecaId: string | null;
  pecaNome: string | null;
  tipoTarefaId: string | null;
  tipoTarefaNome: string | null;
  workflowModeloId: string | null;
  workflowModeloNome: string | null;
  responsavelUsuarioId: string | null;
  responsavelUsuarioNome: string | null;
  responsavelDepartamentoId: string | null;
  responsavelDepartamentoNome: string | null;
};

export type ModeloCampanhaFormDraft = {
  nome: string;
  descricao: string;
  status: Exclude<ModeloCampanhaStatus, "arquivado">;
  itens: ModeloCampanhaItemFormDraft[];
};

/** Projeção mínima do diretório (GET /modelos-campanha/diretorio) — só ativo, sem itens. Sem
 * consumidor nesta fase (2G.5B é só a biblioteca administrativa); reservado pra 2G.5C. */
export type ModeloCampanhaDiretorioItem = {
  id: string;
  nome: string;
};
