import type { DemandaWorkflowEtapa } from "@/types/demanda";

/**
 * Apresentação da RESPONSABILIDADE de uma etapa do workflow (quem executa: Redação → Raquel, Direção de Arte → João…).
 *
 * Regra (do SERVIDOR, `app/core/executor_etapa.py`): a etapa tem responsabilidade EXPLÍCITA se possuir ao menos 1 usuário OU 1 departamento — vale só ela; senão, os responsáveis
 * GERAIS da tarefa são o fallback (resolvido em leitura, nunca copiado para a etapa); senão, ninguém. Numa tarefa que já existe, a tela só EXIBE `responsabilidadeEfetiva` (a origem
 * vem pronta). `previsaoNaCriacao` é a única reaplicação local da regra: antes de a tarefa existir não há servidor para responder, então a tela de criação pré-visualiza — e o servidor
 * continua sendo quem resolve de verdade ao gravar.
 */

export type OrigemResponsabilidade = "etapa" | "tarefa" | "nenhuma";

export type ResponsabilidadeExibida = { origem: OrigemResponsabilidade; usuarioIds: string[]; departamentoIds: string[] };

export const ROTULO_ORIGEM: Record<OrigemResponsabilidade, string> = {
  etapa: "Definido na etapa",
  tarefa: "Herdado da tarefa",
  nenhuma: "Sem responsável",
};

export const AJUDA_HERANCA = "Se nenhum responsável específico for definido, esta etapa usa os responsáveis gerais da tarefa.";

/** Tarefa existente: o que o servidor resolveu (nunca recomputado). Respostas antigas sem o campo caem nos vínculos explícitos da própria etapa. */
export function responsabilidadeDaEtapa(etapa: Pick<DemandaWorkflowEtapa, "usuarioResponsavelIds" | "departamentoResponsavelIds" | "responsabilidadeEfetiva">): ResponsabilidadeExibida {
  if (etapa.responsabilidadeEfetiva) return etapa.responsabilidadeEfetiva;
  const tem = etapa.usuarioResponsavelIds.length > 0 || etapa.departamentoResponsavelIds.length > 0;
  return { origem: tem ? "etapa" : "nenhuma", usuarioIds: etapa.usuarioResponsavelIds, departamentoIds: etapa.departamentoResponsavelIds };
}

/** Criação (ainda sem servidor): mesma regra de 3 degraus, só para pré-visualizar. */
export function previsaoNaCriacao(
  explicitos: { usuarioIds: string[]; departamentoIds: string[] },
  gerais: { usuarioIds: string[]; departamentoIds: string[] },
): ResponsabilidadeExibida {
  if (explicitos.usuarioIds.length > 0 || explicitos.departamentoIds.length > 0) return { origem: "etapa", ...explicitos };
  if (gerais.usuarioIds.length > 0 || gerais.departamentoIds.length > 0) return { origem: "tarefa", ...gerais };
  return { origem: "nenhuma", usuarioIds: [], departamentoIds: [] };
}

export type EtapaDoModeloEmEdicao = { modeloEtapaId: string; usuarioResponsavelIds: string[]; departamentoResponsavelIds: string[] };

/** Troca (ou insere) o ajuste de UMA etapa do modelo na lista de ajustes da criação — sem mutar a anterior. */
export function aplicarAjusteDaEtapa(lista: EtapaDoModeloEmEdicao[], ajuste: EtapaDoModeloEmEdicao): EtapaDoModeloEmEdicao[] {
  return [...lista.filter((item) => item.modeloEtapaId !== ajuste.modeloEtapaId), ajuste];
}

export function removerAjusteDaEtapa(lista: EtapaDoModeloEmEdicao[], modeloEtapaId: string): EtapaDoModeloEmEdicao[] {
  return lista.filter((item) => item.modeloEtapaId !== modeloEtapaId);
}

/** Pode abrir o editor de responsáveis da etapa? Mesma ideia de `podeEditarEsforco`: a tela só esconde o que o servidor recusaria de qualquer jeito (escopo-base, concluída, arquivada). */
export function podeEditarResponsaveisDaEtapa(
  demanda: { status: string; acessoApenasWorkflow?: boolean; acessoSomenteAcompanhamento?: boolean },
  etapa: Pick<DemandaWorkflowEtapa, "status">,
  somenteLeitura: boolean,
): boolean {
  if (somenteLeitura) return false;
  if (demanda.acessoApenasWorkflow === true || demanda.acessoSomenteAcompanhamento === true) return false;
  if (demanda.status === "arquivada") return false;
  return etapa.status !== "concluida";
}
