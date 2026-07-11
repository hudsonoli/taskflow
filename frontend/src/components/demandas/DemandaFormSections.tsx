import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";
import { WorkflowEditor } from "@/components/workflows/WorkflowEditor";
import {
  departamentosProjetoDisponiveis,
  prioridadeDemandaLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
  responsaveisProjetoDisponiveis,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import type {
  Demanda,
  DemandaPrioridade,
  DemandaStatus,
} from "@/types/demanda";
import type {
  WorkflowInstancia,
  WorkflowTransicaoHistorico,
} from "@/types/workflow";

type DemandaSectionProps = {
  demanda: Demanda;
  onChange: (demanda: Demanda) => void;
};

function updateDemanda(
  demanda: Demanda,
  patch: Partial<Demanda>,
  onChange: (demanda: Demanda) => void
) {
  onChange({ ...demanda, ...patch, updatedAt: new Date().toISOString() });
}

export function DadosDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  return (
    <WorkspaceSection
      title="Dados"
      description="Dados principais da demanda e prazo da etapa atual."
    >
      <div className="grid gap-4 md:grid-cols-2">
        <Input label="Código" value={demanda.codigoInterno} disabled />
        <Input
          label="Projeto"
          value={resolveProjetoDemandaNome(demanda.projetoId)}
          disabled
        />
        <Input
          label="Cliente"
          value={resolveClienteProjetoNome(demanda.clienteId)}
          disabled
        />
        <Input
          label="Prazo atual"
          type="date"
          value={demanda.prazoEtapaAtual}
          onChange={(event) =>
            updateDemanda(
              demanda,
              { prazoEtapaAtual: event.target.value },
              onChange
            )
          }
        />
        <Select
          label="Prioridade"
          value={demanda.prioridade}
          onChange={(event) =>
            updateDemanda(
              demanda,
              { prioridade: event.target.value as DemandaPrioridade },
              onChange
            )
          }
          options={Object.entries(prioridadeDemandaLabels).map(
            ([value, label]) => ({ value, label })
          )}
        />
        <Select
          label="Status"
          value={demanda.status}
          onChange={(event) =>
            updateDemanda(
              demanda,
              { status: event.target.value as DemandaStatus },
              onChange
            )
          }
          options={Object.entries(statusDemandaLabels).map(([value, label]) => ({
            value,
            label,
          }))}
        />
      </div>
    </WorkspaceSection>
  );
}

export function BriefingDemandaSection({
  demanda,
  onChange,
}: DemandaSectionProps) {
  return (
    <WorkspaceSection
      title="Briefing"
      description="Editor simples nesta fase. Rich text será avaliado futuramente."
    >
      <Textarea
        label="Briefing"
        rows={10}
        value={demanda.briefing}
        onChange={(event) =>
          updateDemanda(demanda, { briefing: event.target.value }, onChange)
        }
      />
    </WorkspaceSection>
  );
}

export function WorkflowDemandaSection({
  demanda,
  onChange,
}: DemandaSectionProps) {
  function handleWorkflowChange(
    workflow: WorkflowInstancia,
    workflowHistorico: WorkflowTransicaoHistorico[]
  ) {
    updateDemanda(
      demanda,
      {
        workflow,
        workflowHistorico,
      },
      onChange
    );
  }

  return (
    <WorkflowEditor
      demandaId={demanda.id}
      workflow={demanda.workflow}
      history={demanda.workflowHistorico}
      onWorkflowChange={handleWorkflowChange}
    />
  );
}

export function ResponsaveisDemandaSection({
  demanda,
  onChange,
}: DemandaSectionProps) {
  return (
    <WorkspaceSection
      title="Responsáveis"
      description="Responsáveis principais por ID. Nomes são derivados apenas para exibição."
    >
      <div className="grid gap-4 md:grid-cols-2">
        <MultiSelect
          label="Usuários responsáveis"
          placeholder="Selecione usuários"
          values={demanda.usuarioResponsavelIds}
          onChange={(values) =>
            updateDemanda(demanda, { usuarioResponsavelIds: values }, onChange)
          }
          options={responsaveisProjetoDisponiveis.map((responsavel) => ({
            value: responsavel.id,
            label: responsavel.nome,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          placeholder="Selecione departamentos"
          values={demanda.departamentoResponsavelIds}
          onChange={(values) =>
            updateDemanda(
              demanda,
              { departamentoResponsavelIds: values },
              onChange
            )
          }
          options={departamentosProjetoDisponiveis.map((departamento) => ({
            value: departamento.id,
            label: departamento.nome,
          }))}
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Input
          label="Usuários selecionados"
          value={resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds)}
          disabled
        />
        <Input
          label="Departamentos selecionados"
          value={resolveDepartamentosProjetoNomes(
            demanda.departamentoResponsavelIds
          )}
          disabled
        />
      </div>
    </WorkspaceSection>
  );
}

export function HistoricoDemandaSection({ demanda }: { demanda: Demanda }) {
  return (
    <WorkspaceSection
      title="Histórico"
      description="Eventos mock preparados para auditoria futura."
    >
      <div className="space-y-3">
        {demanda.historico.map((evento) => (
          <div
            key={evento.id}
            className="rounded-3xl border border-zinc-100 bg-white p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium text-zinc-900">{evento.acao}</p>
                <p className="mt-1 text-sm text-zinc-500">
                  {evento.usuario} · {evento.dataHora}
                </p>
              </div>
              <Badge>{evento.dispositivo}</Badge>
            </div>
            <p className="mt-3 text-sm text-zinc-500">IP: {evento.ip}</p>
          </div>
        ))}
      </div>
    </WorkspaceSection>
  );
}
