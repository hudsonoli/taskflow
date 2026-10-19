// Janela PLANEJADA de uma etapa (11B.2B-A) — lógica PURA (testável com `node --test`), sem React nem fetch.
//
// Planejamento ≠ prazo: `planejadoInicio`/`planejadoFim` são datas de calendário da empresa (fim inclusivo) e nunca derivam de `prazoEtapaAtual`,
// `dataInicio`/`dataFimPrevista`, sessões ou tempo operacional. O servidor é a autoridade do estado e da validação; aqui só se traduz em rótulos e se
// avisa cedo (a mesma regra do backend: fim exige início e não pode ser anterior a ele).
//
// Estados da JANELA: nao_planejado (nada) · incompleto (só início — NÃO entra na ocupação) · planejado (início + fim ≥ início).
// `sem_dia_util` e `janela_vencida` NÃO são estados da janela: são estados derivados de ALOCAÇÃO da Fase B (Carga) e não existem nesta tela.
import type { DemandaWorkflowEtapa, PlanejamentoEstado, PlanejamentoEtapa } from "../types/demanda.ts";

export const TEXTO_PLANEJAMENTO_INCOMPLETO = "Planejamento incompleto";
export const TEXTO_AJUDA_PLANEJAMENTO = "Planejamento da equipe para esta etapa. Não é o prazo da tarefa e não altera nenhum prazo.";
export const TEXTO_ERRO_FIM_SEM_INICIO = "Informe o início do planejamento antes do fim (ou limpe os dois campos).";
export const TEXTO_ERRO_FIM_ANTES_DO_INICIO = "O fim do planejamento não pode ser anterior ao início.";

const DATA_PURA = /^(\d{4})-(\d{2})-(\d{2})$/;

/** `YYYY-MM-DD` real do calendário (sem rolar 31/02 para março). */
export function dataPuraValida(valor: string): boolean {
  const partes = DATA_PURA.exec(valor);
  if (!partes) return false;
  const [ano, mes, dia] = [Number(partes[1]), Number(partes[2]), Number(partes[3])];
  const data = new Date(Date.UTC(ano, mes - 1, dia));
  return data.getUTCFullYear() === ano && data.getUTCMonth() === mes - 1 && data.getUTCDate() === dia;
}

/** `2026-10-20` → `20/10/2026` por manipulação de texto: nunca passa por `Date`, então nunca desloca o dia por fuso. */
export function formatarDataPlanejada(valor: string | null | undefined): string {
  if (!valor || !dataPuraValida(valor)) return "—";
  const [ano, mes, dia] = valor.split("-");
  return `${dia}/${mes}/${ano}`;
}

/** Estado DERIVADO do par — o mesmo do servidor. Par inválido (fim sem início) não existe no servidor; aqui devolve `null` para a tela bloquear o envio. */
export function estadoDaJanela(inicio: string | null | undefined, fim: string | null | undefined): PlanejamentoEstado | null {
  const temInicio = Boolean(inicio);
  const temFim = Boolean(fim);
  if (!temInicio && temFim) return null;
  if (!temInicio) return "nao_planejado";
  return temFim ? "planejado" : "incompleto";
}

/** Erro do PAR digitado (ou `null` se pode enviar). Datas no formato `YYYY-MM-DD` (o que o `<input type="date">` entrega; vazio = sem data). */
export function erroDaJanela(inicio: string, fim: string): string | null {
  if (inicio && !dataPuraValida(inicio)) return "Informe o início como uma data válida.";
  if (fim && !dataPuraValida(fim)) return "Informe o fim como uma data válida.";
  if (fim && !inicio) return TEXTO_ERRO_FIM_SEM_INICIO;
  if (fim && inicio && fim < inicio) return TEXTO_ERRO_FIM_ANTES_DO_INICIO;
  return null;
}

/** Estado já resolvido da etapa (preferindo o que o servidor mandou; sem `planejamento` na resposta = não planejado). */
export function planejamentoDaEtapa(etapa: Pick<DemandaWorkflowEtapa, "planejamento">): PlanejamentoEtapa {
  return etapa.planejamento ?? { planejadoInicio: null, planejadoFim: null, estado: "nao_planejado" };
}

/** Linha de leitura. `null` quando NÃO há planejamento (nenhuma indicação especial). */
export function resumoDoPlanejamento(planejamento: PlanejamentoEtapa): { texto: string; incompleto: boolean } | null {
  if (planejamento.estado === "nao_planejado") return null;
  if (planejamento.estado === "incompleto") {
    return { texto: `Planejado a partir de ${formatarDataPlanejada(planejamento.planejadoInicio)}`, incompleto: true };
  }
  return {
    texto: `Planejado de ${formatarDataPlanejada(planejamento.planejadoInicio)} até ${formatarDataPlanejada(planejamento.planejadoFim)}`,
    incompleto: false,
  };
}

export type CorpoPlanejamento = { planejadoInicio?: string | null; planejadoFim?: string | null };

/** O que está no servidor (`atual`) e o que o formulário mostra (`digitado`), ambos como texto `YYYY-MM-DD` ou vazio. */
export type ParDeDatas = { inicio: string; fim: string };

/**
 * PATCH PARCIAL a partir do que mudou no formulário. Cada campo tem três situações — e só duas delas viajam:
 * - **mudou para uma data** → `"YYYY-MM-DD"`;
 * - **mudou para vazio** → `null` (limpa);
 * - **não mudou** → AUSENTE do corpo (o servidor mantém o valor).
 * Vazio nunca vira string vazia nem data inválida. `null` quando nada mudou (nada a enviar).
 */
export function corpoDoPlanejamento(atual: ParDeDatas, digitado: ParDeDatas): CorpoPlanejamento | null {
  const corpo: CorpoPlanejamento = {};
  if (digitado.inicio !== atual.inicio) corpo.planejadoInicio = digitado.inicio || null;
  if (digitado.fim !== atual.fim) corpo.planejadoFim = digitado.fim || null;
  return Object.keys(corpo).length > 0 ? corpo : null;
}

/**
 * ÚNICA fonte da validação e do "pode salvar" do formulário (a tela só lê isto). A regra vale para o PAR RESULTANTE:
 * - vazio/vazio, início/vazio (incompleto) e início/fim ≥ início são VÁLIDOS;
 * - fim sem início e fim < início são inválidos.
 * `podeSalvar` = par válido E algo mudou (dirty).
 */
export function estadoDoFormulario(atual: ParDeDatas, digitado: ParDeDatas): {
  erro: string | null; mudou: boolean; podeSalvar: boolean; estado: PlanejamentoEstado | null; corpo: CorpoPlanejamento | null;
} {
  const erro = erroDaJanela(digitado.inicio, digitado.fim);
  const corpo = corpoDoPlanejamento(atual, digitado);
  return { erro, mudou: corpo !== null, podeSalvar: erro === null && corpo !== null, estado: estadoDaJanela(digitado.inicio, digitado.fim), corpo };
}

export async function salvarPlanejamento<T>(
  atual: ParDeDatas,
  digitado: ParDeDatas,
  salvar: (corpo: CorpoPlanejamento) => Promise<T>,
) {
  const { erro, corpo } = estadoDoFormulario(atual, digitado);
  if (erro) return { ok: false as const, mensagem: erro };
  if (!corpo) return { ok: false as const, mensagem: "Nenhuma alteração para salvar." };
  try {
    return { ok: true as const, valor: await salvar(corpo) };
  } catch (falha) {
    return { ok: false as const, mensagem: falha instanceof Error && falha.message ? falha.message : "Não foi possível salvar o planejamento." };
  }
}

// ── capacidade alocável (Configurações → Horário de expediente) ───────────────────────────────────────────────────

export const PERCENTUAL_ALOCAVEL_MIN = 1;
export const PERCENTUAL_ALOCAVEL_MAX = 100;
export const PERCENTUAL_ALOCAVEL_PADRAO = 100;
export const TEXTO_AJUDA_CAPACIDADE_ALOCAVEL = "Percentual do expediente disponível para planejamento de tarefas.";

/** Inteiro de 1 a 100; qualquer outra coisa é inválida (o servidor também recusa). */
export function percentualAlocavelValido(valor: unknown): valor is number {
  return typeof valor === "number" && Number.isInteger(valor) && valor >= PERCENTUAL_ALOCAVEL_MIN && valor <= PERCENTUAL_ALOCAVEL_MAX;
}

/** Texto digitado → número válido ou `null` (vazio, decimal, fora do intervalo). Não "corrige" em silêncio. */
export function lerPercentualAlocavel(texto: string): number | null {
  if (!/^\d{1,3}$/.test(texto.trim())) return null;
  const valor = Number(texto.trim());
  return percentualAlocavelValido(valor) ? valor : null;
}
