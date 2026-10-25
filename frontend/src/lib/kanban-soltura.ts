// Decisão PURA do que fazer quando um card é solto numa coluna do Kanban (testável com `node --test`). Não decide nada de negócio: só escolhe QUAL comando do servidor chamar.
//
// SEMÂNTICA ÚNICA DO DESTINO "EM EXECUÇÃO": no Kanban, soltar um card em Em execução significa SEMPRE "começar a trabalhar" — `POST /demandas/{id}/iniciar-trabalho`, o comando autoritativo de
// sessão/foco (abre a sessão pessoal e, se a pessoa tinha foco em outra tarefa, pausa a anterior quando ela era a última executora). Nunca um PATCH de status, para ninguém (operador, gestor,
// dono/admin), seja a tarefa planejada, pausada ou até JÁ em execução: a intenção do gesto é pessoal. Quem o servidor não reconhece como executor recebe a recusa normal do backend (403/404/409)
// e a tarefa fica onde estava — NUNCA há fallback para "mudar o status". Mudar o status administrativamente continua nos controles próprios (campo Status do drawer/formulário).
//
// As demais colunas seguem o PATCH de status.

import type { DemandaStatus, DemandaStatusEditavel } from "@/types/demanda";

/** Destinos de PATCH de status do Kanban: tudo, MENOS Em execução (que é o comando de iniciar trabalho). */
export type StatusMovivelPeloKanban = Exclude<DemandaStatusEditavel, "em_execucao">;

export type DecisaoSoltura =
  | { acao: "nada" }
  | { acao: "iniciar-trabalho" }
  | { acao: "mover"; novoStatus: StatusMovivelPeloKanban }
  | { acao: "bloqueado-expediente" };

export type EntradaSoltura = {
  /** status que a coluna de destino agrupa (o primeiro é o destino ao soltar) */
  statusDaColuna: readonly DemandaStatusEditavel[];
  statusAtual: DemandaStatus;
  /** o expediente permite começar a trabalhar agora (decisão do servidor para esta pessoa) */
  podeIniciarNoExpediente: boolean;
};

export function decidirSoltura(entrada: EntradaSoltura): DecisaoSoltura {
  const { statusDaColuna, statusAtual, podeIniciarNoExpediente } = entrada;
  const novoStatus = statusDaColuna[0];
  if (!novoStatus) return { acao: "nada" };

  if (novoStatus === "em_execucao") {
    // Segunda barreira, além de desabilitar o arraste: soltar depois do fim do turno continua bloqueado (o servidor também recusa) — sem request e sem fallback.
    return podeIniciarNoExpediente ? { acao: "iniciar-trabalho" } : { acao: "bloqueado-expediente" };
  }

  if ((statusDaColuna as readonly DemandaStatus[]).includes(statusAtual)) return { acao: "nada" };
  return { acao: "mover", novoStatus };
}
