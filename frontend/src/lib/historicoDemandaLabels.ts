import type { DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import { statusDemandaLabels } from "@/lib/demandas";
import type { DemandaHistoricoEvento, DemandaStatus } from "@/types/demanda";

/**
 * Traduz um evento de domínio real (`DemandaHistoricoEvento.tipo`, ver
 * app/domain/event_types.py) para uma frase legível na timeline — a UI nunca mostra `tipo`
 * ou `dados` crus (ver instrução da Fase 2E.4, item 7).
 *
 * Tipo desconhecido cai no fallback: eventos de fases futuras aparecem com o próprio `tipo`
 * em vez de quebrar a tela — degrada, não falha.
 */

type Contexto = {
  usuarios: UsuarioDiretorioItem[];
  departamentos: DepartamentoDiretorioItem[];
};

const CAMPO_LABEL: Record<string, string> = {
  nome: "nome",
  status: "status",
  motivoBloqueio: "motivo do bloqueio",
  clienteId: "cliente",
  projetoId: "projeto",
  pit: "PIT",
  briefing: "briefing",
  prioridade: "prioridade",
  sinalizada: "sinalização",
  dataInicio: "data de início",
  dataFimPrevista: "prazo final",
  prazoEtapaAtual: "prazo da etapa atual",
  enviadoClienteEm: "envio ao cliente",
  prazoRetornoCliente: "prazo de retorno do cliente",
  retornoRecebidoEm: "retorno do cliente",
  emailConclusaoEnviado: "aviso de conclusão",
  emailConclusaoData: "data do aviso de conclusão",
  vinculos: "responsáveis/departamentos",
};

function nomeUsuario(usuarioId: unknown, { usuarios }: Contexto): string {
  if (typeof usuarioId !== "string") return "Usuário removido";
  return usuarios.find((usuario) => usuario.id === usuarioId)?.nome ?? "Usuário removido";
}

function nomeDepartamento(departamentoId: unknown, { departamentos }: Contexto): string {
  if (typeof departamentoId !== "string") return "departamento removido";
  return departamentos.find((departamento) => departamento.id === departamentoId)?.nome ?? "departamento removido";
}

function listaCamposAlterados(dados: Record<string, unknown>): string {
  const campos = Array.isArray(dados.camposAlterados) ? (dados.camposAlterados as unknown[]) : [];
  return campos.map((campo) => CAMPO_LABEL[String(campo)] ?? String(campo)).join(", ") || "dados da tarefa";
}

const DESCRITORES: Record<string, (dados: Record<string, unknown>, contexto: Contexto) => string> = {
  "demanda.criada": () => "Tarefa criada",
  "demanda.alterada": (dados) => `Atualização de ${listaCamposAlterados(dados)}`,
  "demanda.status_alterado": (dados) => {
    const de = statusDemandaLabels[dados.de as DemandaStatus] ?? String(dados.de ?? "");
    const para = statusDemandaLabels[dados.para as DemandaStatus] ?? String(dados.para ?? "");
    return `Status alterado de "${de}" para "${para}"`;
  },
  "demanda.bloqueada": (dados) => `Tarefa bloqueada — ${String(dados.motivoBloqueio ?? "sem motivo registrado")}`,
  "demanda.desbloqueada": () => "Tarefa desbloqueada",
  "demanda.responsavel_adicionado": (dados, ctx) => `${nomeUsuario(dados.usuarioId, ctx)} adicionado como responsável`,
  "demanda.responsavel_removido": (dados, ctx) => `${nomeUsuario(dados.usuarioId, ctx)} removido como responsável`,
  "demanda.departamento_adicionado": (dados, ctx) => `Departamento ${nomeDepartamento(dados.departamentoId, ctx)} adicionado`,
  "demanda.departamento_removido": (dados, ctx) => `Departamento ${nomeDepartamento(dados.departamentoId, ctx)} removido`,
  "demanda.arquivada": (dados) => `Tarefa arquivada — ${String(dados.motivoArquivamento ?? "sem motivo registrado")}`,
  "demanda.restaurada": () => "Tarefa restaurada",
  "demanda.checklist_item_criado": (dados) => `Item de checklist adicionado: "${String(dados.texto ?? "")}"`,
  "demanda.checklist_item_alterado": (dados) => `Item de checklist editado: "${String(dados.texto ?? "")}"`,
  "demanda.checklist_item_concluido": () => "Item de checklist concluído",
  "demanda.checklist_item_reaberto": () => "Item de checklist reaberto",
  "demanda.checklist_item_excluido": () => "Item de checklist excluído",
  "demanda.arquivo_enviado": (dados) => `Arquivo enviado: "${String(dados.nomeOriginal ?? "")}"`,
  "demanda.arquivo_removido": (dados) => `Arquivo removido: "${String(dados.nomeOriginal ?? "")}"`,
  "demanda.comentario_criado": () => "Comentário publicado",
  "demanda.comentario_editado": () => "Comentário editado",
  "demanda.comentario_removido": () => "Comentário removido",
  "demanda.workflow_aplicado": () => "Workflow aplicado à tarefa",
  "demanda.ajuste_interno_registrado": () => "Ajuste interno registrado",
  "demanda.ajuste_cliente_registrado": () => "Ajuste solicitado pelo cliente registrado",
  "demanda.refacao_registrada": () => "Refação registrada",
  "demanda.email_conclusao_enviado": () => "E-mail de conclusão enviado ao cliente",
  "demanda.email_conclusao_dispensado": () => "Aviso de conclusão dispensado — e-mail não enviado",
  "demanda.retorno_cliente_registrado": () => "Retorno do cliente registrado",
};

export function descreverEventoHistorico(evento: DemandaHistoricoEvento, contexto: Contexto): string {
  const descritor = DESCRITORES[evento.tipo];
  if (!descritor) return evento.tipo;
  return descritor(evento.dados, contexto);
}

/** Só para agrupar visualmente por "família" de evento — não é `DemandaHistoricoTipo` do
 * mock antigo, é derivado do prefixo do tipo real. */
export function corDoEventoHistorico(tipo: string): "blue" | "green" | "amber" | "red" | "neutral" {
  if (tipo.includes("removid") || tipo.includes("exclu") || tipo === "demanda.bloqueada") return "red";
  if (tipo.includes("refacao") || tipo.includes("ajuste_cliente")) return "amber";
  if (tipo.includes("concluid") || tipo.includes("restaurada") || tipo === "demanda.criada") return "green";
  if (tipo.includes("adicionado") || tipo.includes("criado") || tipo.includes("aplicado")) return "blue";
  return "neutral";
}
