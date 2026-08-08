import { EMPRESA_PADRAO_ID, generateId } from "@/lib/ids";
import type { SlaRegra } from "@/types/sla";

export { EMPRESA_PADRAO_ID, generateId };

function criarSlaRegra(seed: string, patch: Partial<SlaRegra>): SlaRegra {
  return {
    id: `sla-${seed}`,
    empresaId: EMPRESA_PADRAO_ID,
    nome: "",
    descricao: "",
    prioridade: "todas",
    departamentoId: "",
    clienteId: "",
    prazoPrimeiraRespostaHoras: 4,
    prazoResolucaoHoras: 48,
    considerarApenasExpediente: true,
    ativo: true,
    createdAt: "2026-07-01T09:00:00-03:00",
    updatedAt: "2026-07-01T09:00:00-03:00",
    ...patch,
  };
}

export const slaRegrasMock: SlaRegra[] = [
  criarSlaRegra("padrao", {
    nome: "SLA Padrão",
    descricao: "Regra geral aplicada quando nenhuma outra regra mais específica combina com a tarefa.",
    prioridade: "todas",
    prazoPrimeiraRespostaHoras: 4,
    prazoResolucaoHoras: 48,
  }),
  criarSlaRegra("prioridade-alta", {
    nome: "Prioridade Alta",
    descricao: "Tarefas marcadas como prioridade alta, independente de departamento ou cliente.",
    prioridade: "alta",
    prazoPrimeiraRespostaHoras: 1,
    prazoResolucaoHoras: 24,
  }),
  criarSlaRegra("atendimento", {
    nome: "Departamento Atendimento",
    descricao: "Demandas sob responsabilidade do Atendimento — resposta rápida ao cliente.",
    prioridade: "todas",
    departamentoId: "dep-atendimento",
    prazoPrimeiraRespostaHoras: 2,
    prazoResolucaoHoras: 24,
  }),
  criarSlaRegra("cliente-exemplo", {
    nome: "Cliente Exemplo (contrato prioritário)",
    descricao: "Cliente com contrato de atendimento prioritário — prazos reduzidos.",
    prioridade: "todas",
    clienteId: "cliente-1",
    prazoPrimeiraRespostaHoras: 1,
    prazoResolucaoHoras: 12,
  }),
];
