import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";
import {
  departamentosProjetoDisponiveis,
  generateId,
  prioridadeDemandaLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
  responsaveisProjetoDisponiveis,
  statusDemandaLabels,
  workflowEtapaStatusLabels,
} from "@/lib/demandas-mock";
import type {
  Demanda,
  DemandaPrioridade,
  DemandaStatus,
  DemandaWorkflowEtapa,
  DemandaWorkflowEtapaStatus,
} from "@/types/demanda";

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

function createWorkflowEtapa(ordem: number): DemandaWorkflowEtapa {
  return {
    id: generateId("etapa-demanda"),
    nome: "Nova etapa",
    ordem,
    usuarioResponsavelIds: [],
    departamentoResponsavelIds: [],
    prazoHoras: 8,
    status: "pendente",
  };
}

export function WorkflowDemandaSection({
  demanda,
  onChange,
}: DemandaSectionProps) {
  function updateEtapa(etapaId: string, patch: Partial<DemandaWorkflowEtapa>) {
    updateDemanda(
      demanda,
      {
        workflowEtapas: demanda.workflowEtapas.map((etapa) =>
          etapa.id === etapaId ? { ...etapa, ...patch } : etapa
        ),
      },
      onChange
    );
  }

  function removeEtapa(etapaId: string) {
    const nextEtapas = demanda.workflowEtapas
      .filter((etapa) => etapa.id !== etapaId)
      .map((etapa, index) => ({ ...etapa, ordem: index + 1 }));

    updateDemanda(
      demanda,
      {
        workflowEtapas: nextEtapas,
        etapaAtualId:
          demanda.etapaAtualId === etapaId
            ? nextEtapas[0]?.id ?? ""
            : demanda.etapaAtualId,
      },
      onChange
    );
  }

  return (
    <WorkspaceSection
      title="Workflow"
      description="Etapas mock por demanda. Não há motor real, Kanban ou drag-and-drop nesta fase."
    >
      <div className="mb-4 flex justify-end">
        <Button
          type="button"
          onClick={() =>
            updateDemanda(
              demanda,
              {
                workflowEtapas: [
                  ...demanda.workflowEtapas,
                  createWorkflowEtapa(demanda.workflowEtapas.length + 1),
                ],
              },
              onChange
            )
          }
        >
          Adicionar etapa
        </Button>
      </div>

      <div className="space-y-4">
        {demanda.workflowEtapas.map((etapa) => (
          <div
            key={etapa.id}
            className="rounded-3xl border border-zinc-100 bg-white p-4 shadow-sm"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <Badge>Etapa {etapa.ordem}</Badge>
              <Button
                type="button"
                variant="secondary"
                onClick={() => removeEtapa(etapa.id)}
              >
                Remover etapa
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Nome da etapa"
                value={etapa.nome}
                onChange={(event) =>
                  updateEtapa(etapa.id, { nome: event.target.value })
                }
              />
              <Input
                label="Prazo em horas"
                type="number"
                min={1}
                value={etapa.prazoHoras}
                onChange={(event) =>
                  updateEtapa(etapa.id, {
                    prazoHoras: Number(event.target.value),
                  })
                }
              />
              <Select
                label="Status da etapa"
                value={etapa.status}
                onChange={(event) =>
                  updateEtapa(etapa.id, {
                    status: event.target.value as DemandaWorkflowEtapaStatus,
                  })
                }
                options={Object.entries(workflowEtapaStatusLabels).map(
                  ([value, label]) => ({ value, label })
                )}
              />
              <Select
                label="Etapa atual"
                value={demanda.etapaAtualId === etapa.id ? etapa.id : ""}
                onChange={() =>
                  updateDemanda(demanda, { etapaAtualId: etapa.id }, onChange)
                }
                options={[
                  { value: "", label: "Não" },
                  { value: etapa.id, label: "Sim" },
                ]}
              />
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <MultiSelect
                label="Usuários da etapa"
                placeholder="Selecione usuários"
                values={etapa.usuarioResponsavelIds}
                onChange={(values) =>
                  updateEtapa(etapa.id, { usuarioResponsavelIds: values })
                }
                options={responsaveisProjetoDisponiveis.map((responsavel) => ({
                  value: responsavel.id,
                  label: responsavel.nome,
                }))}
              />
              <MultiSelect
                label="Departamentos da etapa"
                placeholder="Selecione departamentos"
                values={etapa.departamentoResponsavelIds}
                onChange={(values) =>
                  updateEtapa(etapa.id, {
                    departamentoResponsavelIds: values,
                  })
                }
                options={departamentosProjetoDisponiveis.map((departamento) => ({
                  value: departamento.id,
                  label: departamento.nome,
                }))}
              />
            </div>
          </div>
        ))}
      </div>
    </WorkspaceSection>
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
