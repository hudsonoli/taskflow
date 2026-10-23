import type { VisaoPauta } from "@/lib/pauta-operacional";
import type { PautaItem } from "@/types/pauta-operacional";

/** Resolvedores de rótulo e ações compartilhados pelas apresentações da Pauta (Gantt e Lista). Nenhuma regra de domínio: só nomes e navegação. */
export type PautaContexto = {
  visao: VisaoPauta;
  nomeCliente: (clienteId: string | null) => string | null;
  nomeProjeto: (projetoId: string | null) => string | null;
  nomeDepartamento: (departamentoId: string) => string;
  nomePessoa: (usuarioId: string) => string;
  emExecucaoIds: ReadonlySet<string>;
  onOpenDetails: (demandaId: string) => void;
};

/** Texto curto de quem é responsável NESTE agrupamento: colaborador → só os colegas ("Com João") ou o departamento; projeto → todos os nomes. */
export function rotuloDeResponsaveis(item: PautaItem, contexto: PautaContexto, usuarioDoGrupo?: string): string | null {
  const { usuarioIds, departamentoIds } = item.responsabilidadeEfetiva;
  if (usuarioIds.length === 0) {
    if (departamentoIds.length === 0) return contexto.visao === "projeto" ? "Sem responsável" : null;
    return `Departamento: ${departamentoIds.map(contexto.nomeDepartamento).join(", ")}`;
  }
  const nomes = (contexto.visao === "colaborador" ? usuarioIds.filter((id) => id !== usuarioDoGrupo) : usuarioIds).map(contexto.nomePessoa);
  if (nomes.length === 0) return null;
  return contexto.visao === "colaborador" ? `Com ${nomes.join(", ")}` : nomes.join(", ");
}

export function rotuloDeOrigem(item: PautaItem): string | null {
  const origem = item.responsabilidadeEfetiva.origem;
  if (origem === "tarefa") return "Herdado da tarefa";
  if (origem === "etapa") return "Definido na etapa";
  return null;
}

export function contextoDoItem(item: PautaItem, contexto: PautaContexto): string {
  return [contexto.nomeCliente(item.clienteId), contexto.nomeProjeto(item.projetoId)].filter(Boolean).join(" / ");
}
