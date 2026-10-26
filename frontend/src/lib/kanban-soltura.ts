// Decisão PURA do que fazer quando um card é solto numa coluna do Kanban (testável com `node --test`). Não decide nada de negócio: só escolhe QUAL comando do servidor chamar, ANTES de qualquer
// mutation, a partir de dois sinais que o SERVIDOR calcula por tarefa (a interface nunca recalcula responsabilidade nem RBAC):
//   - `ehExecutorEfetivo`: SÓ responsabilidade (regra central de executor da etapa atual, sem status/expediente/perfil);
//   - `podeAlterarStatus`: SÓ autoridade (`demandas.editar` efetiva, a mesma que o PATCH de status exige).
//
// DESTINO "EM EXECUÇÃO" — duas intenções, escolhidas pela RESPONSABILIDADE antes do perfil:
//   A) é executor efetivo  → "começar a trabalhar": `POST /demandas/{id}/iniciar-trabalho` (sessão pessoal e foco único: a anterior pausa se ele era o último executor). Também com a tarefa JÁ em execução
//      e sem sessão dele. Nunca PATCH, nem para admin/gestor que executa.
//   B) NÃO é executor, mas tem autoridade → mudança ADMINISTRATIVA de status (PATCH `status=em_execucao`): sem sessão pessoal e sem tocar no foco que a pessoa já tenha em outra tarefa.
//   C) NÃO é executor e não tem autoridade → bloqueado: nem POST nem PATCH.
// NUNCA há fallback baseado em erro (POST recusado → PATCH): o servidor continua recusando o POST de quem não é executor (403) e a escolha acima acontece antes. Fora do expediente o gesto é
// bloqueado para os dois caminhos, sem request (o servidor também recusa).
//
// As demais colunas seguem o PATCH de status.

import type { DemandaStatus, DemandaStatusEditavel } from "@/types/demanda";

export type DecisaoSoltura =
  | { acao: "nada" }
  | { acao: "iniciar-trabalho" }
  | { acao: "alterar-status-administrativo"; novoStatus: "em_execucao" }
  | { acao: "mover"; novoStatus: Exclude<DemandaStatusEditavel, "em_execucao"> }
  | { acao: "bloqueado-expediente" }
  | { acao: "bloqueado-sem-autoridade" };

export type EntradaSoltura = {
  /** status que a coluna de destino agrupa (o primeiro é o destino ao soltar) */
  statusDaColuna: readonly DemandaStatusEditavel[];
  statusAtual: DemandaStatus;
  /** o expediente permite começar a trabalhar agora (decisão do servidor para esta pessoa) */
  podeIniciarNoExpediente: boolean;
  /** sinal do servidor: a pessoa é executor efetivo desta tarefa (só responsabilidade) */
  ehExecutorEfetivo: boolean;
  /** sinal do servidor: a pessoa pode alterar o status desta tarefa administrativamente (só autoridade) */
  podeAlterarStatus: boolean;
};

export function decidirSoltura(entrada: EntradaSoltura): DecisaoSoltura {
  const { statusDaColuna, statusAtual, podeIniciarNoExpediente, ehExecutorEfetivo, podeAlterarStatus } = entrada;
  const novoStatus = statusDaColuna[0];
  if (!novoStatus) return { acao: "nada" };

  if (novoStatus === "em_execucao") {
    // Segunda barreira, além de desabilitar o arraste: soltar depois do fim do turno continua bloqueado — sem request e sem converter em outro caminho.
    if (!podeIniciarNoExpediente) return { acao: "bloqueado-expediente" };
    if (ehExecutorEfetivo) return { acao: "iniciar-trabalho" };
    if (!podeAlterarStatus) return { acao: "bloqueado-sem-autoridade" };
    // Já está em execução e a pessoa não executa: não há o que mudar (e nenhuma sessão a abrir).
    if (statusAtual === "em_execucao") return { acao: "nada" };
    return { acao: "alterar-status-administrativo", novoStatus: "em_execucao" };
  }

  if ((statusDaColuna as readonly DemandaStatus[]).includes(statusAtual)) return { acao: "nada" };
  return { acao: "mover", novoStatus: novoStatus as Exclude<DemandaStatusEditavel, "em_execucao"> };
}
