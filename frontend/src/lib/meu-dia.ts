// Meu Dia — lógica PURA da fila operacional pessoal (testável com `node --test`).
//
// Faixas (a MESMA ordem que o servidor aplica em `sort=fila_pessoal`; aqui só rotulam o que já veio ordenado):
//   execucao  — há sessão de trabalho ATIVA do próprio usuário nesta demanda (fonte real; `status == em_execucao` sozinho não conta);
//   atrasada  — prazo da etapa atual já passou;
//   hoje      — vence hoje (dia local);
//   futura    — tem prazo, ainda adiante;
//   sem_prazo — sem prazo definido.
export type FaixaFila = "execucao" | "atrasada" | "hoje" | "futura" | "sem_prazo";

export const ROTULO_FAIXA: Record<FaixaFila, string> = {
  execucao: "Em execução agora",
  atrasada: "Atrasada",
  hoje: "Vence hoje",
  futura: "Com prazo",
  sem_prazo: "Sem prazo",
};

function mesmoDiaLocal(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function faixaDaFila(prazoEtapaAtual: string | null | undefined, emExecucaoAgora: boolean, agora: Date): FaixaFila {
  if (emExecucaoAgora) return "execucao";
  if (!prazoEtapaAtual) return "sem_prazo";
  const prazo = new Date(prazoEtapaAtual);
  if (Number.isNaN(prazo.getTime())) return "sem_prazo";
  if (prazo.getTime() < agora.getTime()) return "atrasada";
  return mesmoDiaLocal(prazo, agora) ? "hoje" : "futura";
}

/** Fronteiras do dia LOCAL a partir de UMA referência (`agora`) — enviadas ao servidor, que não recalcula "hoje". */
export function fronteirasDoDia(agora: Date): { agora: string; hojeInicio: string; hojeFim: string } {
  const inicio = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate(), 0, 0, 0, 0);
  const fim = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate(), 23, 59, 59, 999);
  return { agora: agora.toISOString(), hojeInicio: inicio.toISOString(), hojeFim: fim.toISOString() };
}

/** Status que ainda fazem parte da fila de quem executa (os mesmos que o servidor considera "não finalizada" e não arquivada). */
export const STATUS_DA_FILA = ["rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"] as const;
