// Decisão PURA do que fazer quando um card é solto numa coluna do Kanban (testável com `node --test`). Não decide nada de negócio: só escolhe QUAL comando do servidor chamar.
//
// - Soltar em "Em execução" é "começar a trabalhar" (`POST /demandas/{id}/iniciar-trabalho`) — o servidor decide se abre a sessão pessoal (só para quem executa a etapa) e faz a troca de
//   foco (a tarefa anterior da PESSOA vai para Pausada se ela era a última executora). Nunca um PATCH de status para Em execução.
// - Tarefa que JÁ está em Em execução mas sem a sessão da pessoa (colocada ali pelo campo Status do drawer, ou criada já em execução): soltá-la na própria coluna NÃO é um no-op — é o mesmo
//   comando do botão "Iniciar trabalho" do card (idempotente no servidor). Sem isso a tarefa nunca ganha sessão e a troca de foco seguinte não tem "tarefa anterior" a pausar.
// - As demais colunas seguem o PATCH de status.

import type { DemandaStatus, DemandaStatusEditavel } from "@/types/demanda";

export type DecisaoSoltura =
  | { acao: "nada" }
  | { acao: "iniciar-trabalho" }
  | { acao: "mover"; novoStatus: DemandaStatusEditavel }
  | { acao: "bloqueado-expediente" };

export type EntradaSoltura = {
  /** status que a coluna de destino agrupa (o primeiro é o destino ao soltar) */
  statusDaColuna: readonly DemandaStatusEditavel[];
  statusAtual: DemandaStatus;
  /** flag do servidor: esta pessoa executa a etapa atual e pode começar a trabalhar nela */
  podeIniciarTrabalho: boolean | undefined;
  /** flag do servidor: esta pessoa já tem sessão ativa nesta tarefa */
  trabalhandoAgora: boolean | undefined;
  /** o expediente permite começar a trabalhar agora (decisão do servidor para esta pessoa) */
  podeIniciarNoExpediente: boolean;
};

export function decidirSoltura(entrada: EntradaSoltura): DecisaoSoltura {
  const { statusDaColuna, statusAtual, podeIniciarTrabalho, trabalhandoAgora, podeIniciarNoExpediente } = entrada;
  const novoStatus = statusDaColuna[0];
  if (!novoStatus) return { acao: "nada" };
  const jaNaColuna = (statusDaColuna as readonly DemandaStatus[]).includes(statusAtual);

  if (jaNaColuna) {
    const semSessaoDaPessoa = novoStatus === "em_execucao" && statusAtual === "em_execucao" && podeIniciarTrabalho === true && trabalhandoAgora !== true;
    if (!semSessaoDaPessoa) return { acao: "nada" };
    return podeIniciarNoExpediente ? { acao: "iniciar-trabalho" } : { acao: "bloqueado-expediente" };
  }

  // Segunda barreira, além de desabilitar o arraste: soltar depois do fim do turno continua bloqueado (o servidor também recusa).
  if (novoStatus === "em_execucao") return podeIniciarNoExpediente ? { acao: "iniciar-trabalho" } : { acao: "bloqueado-expediente" };
  return { acao: "mover", novoStatus };
}
