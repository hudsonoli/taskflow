// Shape real de ConfiguracaoNumeracaoTarefaRead (backend, Fase 2G.8B) — camelCase via alias
// Pydantic, sem mapeamento manual no client.
//
// Representa a numeração OPERACIONAL de Demanda/Tarefa (`numero_operacional` —
// `sequencias_operacionais`): contínua, sem ano, nunca reinicia. NÃO é o `codigoReferencia`
// (`T26000001`, anual, outro domínio — `sequencias_referencia`) — os dois nunca devem ser
// confundidos (ver Fase 2G.8A, achado central).
//
// Fase 7D.1: além do estado do contador, traz o FORMATO das próximas tarefas (prefixo, separador, ano, dígitos) e a prévia.
// Sem `empresaId` (implicitamente tenant-scoped, resolvido sempre por `current_user.empresa_id`) e SEM reinício anual (fase futura).
// Alterar o formato afeta só as novas tarefas: o identificador de cada tarefa é gravado na emissão e nunca muda.
export type ConfiguracaoNumeracaoTarefaRead = {
  entidade: string;
  rotuloEntidade: string;
  contadorAtual: number;
  proximoNumero: number;
  /** Mesmo valor de `proximoNumero` (compatibilidade). */
  proximoNumeroEstimado: number;
  maiorNumeroEmitido: number | null;
  consistente: boolean;
  motivoInconsistencia: string | null;
  /** Modelo legível, ex.: `BOX-<ano>-<número>`. */
  formatoExibicao: string;
  gerenciadoAutomaticamente: boolean;
  prefixo: string;
  separador: string;
  incluirAno: boolean;
  digitos: number;
  /** Como seria a PRÓXIMA tarefa (não consome número). */
  preview: string;
};
