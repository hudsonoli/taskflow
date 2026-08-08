import { EMPRESA_PADRAO_ID } from "@/lib/ids";
import type { ConfiguracaoNumeracaoTarefa } from "@/types/configuracao-numeracao-tarefa";

export { EMPRESA_PADRAO_ID };

// Continuidade da numeração já usada no iClips (hoje em #002062) — ajustar manualmente ao migrar.
export const configuracaoNumeracaoTarefaMock: ConfiguracaoNumeracaoTarefa = {
  id: "configuracao-numeracao-tarefa-padrao",
  empresaId: EMPRESA_PADRAO_ID,
  ano: 2026,
  proximoNumero: 63,
  createdAt: "2026-08-02T09:00:00-03:00",
  updatedAt: "2026-08-02T09:00:00-03:00",
};
