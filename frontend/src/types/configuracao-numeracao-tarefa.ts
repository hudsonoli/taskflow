// Shape real de ConfiguracaoNumeracaoTarefaRead (backend, Fase 2G.8B) — camelCase via alias
// Pydantic, sem mapeamento manual no client.
//
// Representa a numeração OPERACIONAL de Demanda/Tarefa (`numero_operacional` —
// `sequencias_operacionais`): contínua, sem ano, nunca reinicia. NÃO é o `codigoReferencia`
// (`T26000001`, anual, outro domínio — `sequencias_referencia`) — os dois nunca devem ser
// confundidos (ver Fase 2G.8A, achado central).
//
// Tela 100% informativa: sem draft, sem escrita, sem `empresaId` (implicitamente
// tenant-scoped, resolvido sempre por `current_user.empresa_id`).
export type ConfiguracaoNumeracaoTarefaRead = {
  entidade: string;
  rotuloEntidade: string;
  contadorAtual: number;
  proximoNumeroEstimado: number;
  maiorNumeroEmitido: number | null;
  consistente: boolean;
  formatoExibicao: string;
  gerenciadoAutomaticamente: boolean;
};
