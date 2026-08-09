import type { ProjetoPrioridade, ProjetoStatus } from "@/types/projeto";

/**
 * Rótulos de apresentação de Projeto.
 *
 * Moravam em `lib/projetos-mock.ts` e sobreviveram à remoção dele: são regras de interface,
 * não dados. Nada aqui fala com a API — persistência é responsabilidade de
 * `lib/api-backend.ts`.
 */

export const statusProjetoLabels: Record<ProjetoStatus, string> = {
  planejamento: "Planejamento",
  ativo: "Ativo",
  pausado: "Pausado",
  concluido: "Concluído",
  cancelado: "Cancelado",
  arquivado: "Arquivado",
};

export const prioridadeProjetoLabels: Record<ProjetoPrioridade, string> = {
  baixa: "Baixa",
  media: "Média",
  alta: "Alta",
};
