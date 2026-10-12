// Tráfego — peças puras da faixa superior (seletor de Demanda, texto do cabeçalho e aviso de sessão já ativa). `npm run test:trafego-ui` (node --test, sem DOM).
import { CODIGO_SESSAO_ATIVA_EXISTENTE, SessaoTrabalhoErro } from "./sessao-trabalho-erro.ts";

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

export const MENSAGEM_SESSAO_ATIVA = "Você já possui uma atividade em execução.";
/** Quanto tempo o aviso flutuante fica na tela (o botão de fechar remove antes). */
export const DURACAO_AVISO_MS = 5000;

export type ResultadoAbrirSessao = { tipo: "aviso-sessao-ativa" } | { tipo: "erro"; mensagem: string };

/**
 * Como a tela trata a falha de "Iniciar sessão": SÓ o 409 `SESSAO_ATIVA_EXISTENTE` vira aviso flutuante (a sessão ativa já aparece em "Quem está trabalhando agora" — nada
 * de mensagem fixa na barra). Qualquer outro erro mantém o tratamento de erro de antes (mensagem do servidor). Decide pelo CÓDIGO, nunca pelo texto.
 */
export function classificarErroAbrirSessao(erro: unknown): ResultadoAbrirSessao {
  if (erro instanceof SessaoTrabalhoErro && erro.status === 409 && erro.codigo === CODIGO_SESSAO_ATIVA_EXISTENTE) return { tipo: "aviso-sessao-ativa" };
  return { tipo: "erro", mensagem: erro instanceof Error ? erro.message : "Erro ao iniciar sessão" };
}

/** Agenda o fechamento automático do aviso e devolve o cancelamento (limpeza do efeito / fechamento manual antes do prazo). Pura: o agendador é injetável. */
export function agendarFechamento(
  aoFechar: () => void,
  duracaoMs: number = DURACAO_AVISO_MS,
  agendar: (fn: () => void, ms: number) => unknown = (fn, ms) => setTimeout(fn, ms),
  cancelar: (id: unknown) => void = (id) => clearTimeout(id as ReturnType<typeof setTimeout>),
): () => void {
  const id = agendar(aoFechar, duracaoMs);
  return () => cancelar(id);
}
