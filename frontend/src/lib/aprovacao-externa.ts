// Aprovação externa — lado INTERNO (Fase 9B). Lógica PURA (testável com `node --test`), sem React nem fetch.
//
// O SERVIDOR decide tudo: quem pode gerenciar (`podeGerenciar`, autoridade própria — responsável da etapa, Head, gestor/admin, responsável da
// Demanda; Atendimento NÃO ganha por ser Atendimento), o estado derivado do link e a validade. Aqui só se traduz o estado em rótulos/ações. O token
// existe em claro apenas na resposta da criação e vive só em memória do componente: nunca em storage, URL, log ou estado persistido.
import type {
  AprovacaoExterna,
  AprovacaoExternaCriada,
  AprovacaoExternaNovaEntrada,
  AprovacaoExternaPainel,
  ContatoClienteAprovacao,
  EstadoAprovacaoExterna,
} from "../types/aprovacao-externa.ts";
import type { DemandaWorkflowEtapa } from "../types/demanda.ts";
import { PAGINA_APROVACAO_EXTERNA, caminhoDoTenant } from "./tenant.ts";

export const ARQUIVOS_MAX = 10;
export const INSTRUCAO_MAX = 1000;
export const VALIDADES_DIAS = [1, 3, 7, 14, 30] as const;
export const AVISO_LINK_UNICO = "O link é exibido somente agora. Para gerar outro, revogue e crie um novo.";

/** Link público do portal (Fase 9D): `<origem>/e/<slug>/aprovacao#token=<token>`. O slug é o da empresa que o SERVIDOR devolveu na criação (nunca um valor fixo);
 * o token vai no FRAGMENTO — o navegador não o envia ao servidor na requisição da página — e jamais em query string. */
export function linkDeAprovacao(origem: string, slug: string, token: string): string {
  return `${origem.replace(/\/+$/, "")}${caminhoDoTenant(slug, PAGINA_APROVACAO_EXTERNA)}#token=${token}`;
}

export const rotuloEstadoAprovacao: Record<EstadoAprovacaoExterna, string> = {
  pendente: "Aguardando o cliente",
  aprovada: "Aprovada pelo cliente",
  ajustes_solicitados: "Ajustes solicitados",
  revogada: "Link revogado",
  expirada: "Link expirado",
  obsoleta: "Link obsoleto",
};

export const toneEstadoAprovacao: Record<EstadoAprovacaoExterna, "neutral" | "blue" | "green" | "amber" | "red"> = {
  pendente: "blue",
  aprovada: "green",
  ajustes_solicitados: "amber",
  revogada: "neutral",
  expirada: "neutral",
  obsoleta: "neutral",
};

/** O bloco só existe na etapa ATUAL de APROVAÇÃO, fora da leitura global (Pauta). O painel do servidor decide o resto. */
export function podeExibirBlocoAprovacao(
  etapa: Pick<DemandaWorkflowEtapa, "id" | "tipo" | "status">,
  etapaAtualId: string | null,
  somenteLeitura: boolean,
): boolean {
  return !somenteLeitura && etapa.tipo === "aprovacao" && etapa.id === etapaAtualId && etapa.status !== "concluida";
}

/** Sem autoridade e sem histórico de link, não há nada para mostrar. */
export function deveRenderizarPainel(painel: Pick<AprovacaoExternaPainel, "podeGerenciar" | "atual"> | null): boolean {
  return painel !== null && (painel.podeGerenciar || painel.atual !== null);
}

/** Ações disponíveis, SEMPRE condicionadas ao `podeGerenciar` do servidor. */
export function acoesDoPainel(painel: Pick<AprovacaoExternaPainel, "podeGerenciar" | "atual">): {
  gerarNovo: boolean;
  revogar: boolean;
} {
  if (!painel.podeGerenciar) return { gerarNovo: false, revogar: false };
  const estado = painel.atual?.estado ?? null;
  return {
    gerarNovo: estado !== "aprovada", // decidida como aprovada encerra a etapa; ajustes/revogada/expirada/obsoleta permitem outro link
    revogar: estado === "pendente",
  };
}

const TIPOS_ELEGIVEIS = ["layout", "anexo"] as const;
const MIME_ELEGIVEIS = ["image/png", "image/jpeg", "application/pdf"] as const;

type ArquivoSelecionavel = { id: string; tipo: string; contentType: string | null; nomeOriginal: string | null };

/** Só arquivo físico PNG/JPG/PDF de tipo layout/anexo (links nunca). O servidor revalida tudo (inclusive o SHA-256 do que está em disco). */
export function arquivoElegivelParaAprovacao(arquivo: ArquivoSelecionavel): boolean {
  return (
    (TIPOS_ELEGIVEIS as readonly string[]).includes(arquivo.tipo) &&
    arquivo.nomeOriginal !== null &&
    arquivo.contentType !== null &&
    (MIME_ELEGIVEIS as readonly string[]).includes(arquivo.contentType)
  );
}

export function alternarArquivo(selecionados: string[], arquivoId: string): string[] {
  if (selecionados.includes(arquivoId)) return selecionados.filter((id) => id !== arquivoId);
  if (selecionados.length >= ARQUIVOS_MAX) return selecionados;
  return [...selecionados, arquivoId];
}

export function erroDaInstrucao(texto: string): string | null {
  const limpo = texto.trim();
  if (limpo.length > INSTRUCAO_MAX) return `A instrução pode ter no máximo ${INSTRUCAO_MAX} caracteres.`;
  if (limpo.includes("<") || limpo.includes(">")) return "A instrução não pode conter HTML.";
  return null;
}

/** Quem recebe entregas primeiro (o servidor já ordena assim; reforço defensivo e estável). */
export function ordenarContatos(contatos: ContatoClienteAprovacao[]): ContatoClienteAprovacao[] {
  return [...contatos].sort((a, b) => Number(b.recebeEntregas) - Number(a.recebeEntregas));
}

export function montarEntradaDeCriacao(entrada: {
  arquivoIds: string[];
  instrucao: string;
  validadeDias: number;
  contato: ContatoClienteAprovacao | null;
}): AprovacaoExternaNovaEntrada {
  const instrucao = entrada.instrucao.trim();
  return {
    arquivoIds: entrada.arquivoIds,
    instrucao: instrucao || null,
    validadeDias: entrada.validadeDias,
    destinatarioNome: entrada.contato?.nome ?? null,
    destinatarioEmail: entrada.contato?.email ?? null,
  };
}

export function erroDaCriacao(entrada: { arquivoIds: string[]; instrucao: string }): string | null {
  if (entrada.arquivoIds.length === 0) return "Selecione ao menos um arquivo para o cliente avaliar.";
  if (entrada.arquivoIds.length > ARQUIVOS_MAX) return `Selecione no máximo ${ARQUIVOS_MAX} arquivos.`;
  return erroDaInstrucao(entrada.instrucao);
}

export type ResultadoCriacao =
  | { ok: true; criada: AprovacaoExternaCriada }
  | { ok: false; mensagem: string; conflito: boolean };

/**
 * Cria o link e traduz o desfecho. `conflito` = o estado da Demanda mudou (etapa não é mais a atual, arquivada…): o chamador recarrega o workflow e
 * fecha o modal. Outros erros mantêm o modal aberto com a seleção preservada. `criar` é injetado (API real na tela, stub no teste).
 */
export async function criarLinkDeAprovacao(entrada: {
  corpo: AprovacaoExternaNovaEntrada;
  criar: (corpo: AprovacaoExternaNovaEntrada) => Promise<AprovacaoExternaCriada>;
  ehConflito: (erro: unknown) => boolean;
}): Promise<ResultadoCriacao> {
  const erro = erroDaCriacao({ arquivoIds: entrada.corpo.arquivoIds, instrucao: entrada.corpo.instrucao ?? "" });
  if (erro) return { ok: false, mensagem: erro, conflito: false };
  try {
    return { ok: true, criada: await entrada.criar(entrada.corpo) };
  } catch (falha) {
    const mensagem = falha instanceof Error && falha.message ? falha.message : "Não foi possível gerar o link de aprovação.";
    return { ok: false, mensagem, conflito: entrada.ehConflito(falha) };
  }
}

export function descreverDecisaoInterna(aprovacao: AprovacaoExterna): string | null {
  const decisao = aprovacao.decisao;
  if (!decisao) return null;
  const verbo = decisao.decisao === "aprovada" ? "Aprovado" : "Ajustes solicitados";
  return `${verbo} por ${decisao.nomeAprovador} (identidade declarada, não verificada)`;
}
