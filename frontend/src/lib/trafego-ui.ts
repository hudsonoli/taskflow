// Tráfego — peças puras da faixa superior (seletor de Demanda e texto do cabeçalho). `npm run test:trafego-ui` (node --test, sem DOM).

export const PLACEHOLDER_DEMANDA = "Selecione uma demanda...";

/** Texto explicativo da Central de Tráfego: aparece no tooltip do ícone de informação (não mais como parágrafo fixo). */
export const TEXTO_INFO_TRAFEGO = "Sessões de trabalho abertas e encerradas via API, calculadas pelo motor de horas do backend.";

export type OpcaoSelecao = { value: string; label: string; disabled?: boolean };

/**
 * Opções do seletor de Demanda: SEMPRE começa pela opção vazia explícita. Sem ela, um `<select>` controlado com `value=""` mostra visualmente a primeira
 * demanda mas mantém o estado vazio — e com uma única demanda não há outra opção para trocar, então o `onChange` nunca disparava e o botão ficava desabilitado
 * para sempre. A primeira demanda NÃO é auto-selecionada: iniciar sessão é ação operacional, a escolha é explícita.
 */
export function opcoesDeDemanda<T>(demandas: readonly T[], paraOpcao: (demanda: T) => { value: string; label: string }): OpcaoSelecao[] {
  return [{ value: "", label: PLACEHOLDER_DEMANDA, disabled: true }, ...demandas.map(paraOpcao)];
}

/** Habilitação do botão "Iniciar sessão": mesma regra de sempre — não está enviando, e Demanda E Usuário escolhidos. */
export function podeIniciarSessao({ enviando, demandaId, usuarioId }: { enviando: boolean; demandaId: string; usuarioId: string }): boolean {
  return !(enviando || !demandaId || !usuarioId);
}
