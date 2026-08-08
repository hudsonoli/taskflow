export type ConfiguracaoNumeracaoTarefa = {
  id: string;
  empresaId: string;
  ano: number;
  // Número que será usado pela próxima tarefa criada neste ano (ex.: 63 -> próxima tarefa = #260063).
  proximoNumero: number;
  createdAt: string;
  updatedAt: string;
};
