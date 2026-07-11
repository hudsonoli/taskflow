import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import {
  departamentosProjetoDisponiveis,
  responsaveisProjetoDisponiveis,
  workflowEtapaStatusLabels,
} from "@/lib/workflows-mock";
import type { WorkflowEtapa, WorkflowEtapaStatus } from "@/types/workflow";

type WorkflowStepCardProps = {
  etapa: WorkflowEtapa;
  isCurrent: boolean;
  canMoveUp: boolean;
  canMoveDown: boolean;
  onChange: (etapa: WorkflowEtapa) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
};

export function WorkflowStepCard({
  etapa,
  isCurrent,
  canMoveUp,
  canMoveDown,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}: WorkflowStepCardProps) {
  return (
    <div
      className={`rounded-3xl border bg-white p-4 shadow-sm ${
        isCurrent ? "border-zinc-900" : "border-zinc-100"
      }`}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>Etapa {etapa.ordem}</Badge>
          {isCurrent && <Badge>Atual</Badge>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={!canMoveUp}
            onClick={onMoveUp}
          >
            Subir
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={!canMoveDown}
            onClick={onMoveDown}
          >
            Descer
          </Button>
          <Button type="button" variant="secondary" onClick={onRemove}>
            Remover
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input
          label="Nome da etapa"
          value={etapa.nome}
          onChange={(event) => onChange({ ...etapa, nome: event.target.value })}
        />
        <Input
          label="Prazo em horas"
          type="number"
          min={1}
          value={etapa.prazoHoras}
          onChange={(event) =>
            onChange({ ...etapa, prazoHoras: Number(event.target.value) })
          }
        />
        <Select
          label="Status"
          value={etapa.status}
          onChange={(event) =>
            onChange({
              ...etapa,
              status: event.target.value as WorkflowEtapaStatus,
            })
          }
          options={Object.entries(workflowEtapaStatusLabels).map(
            ([value, label]) => ({ value, label })
          )}
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <MultiSelect
          label="Usuários responsáveis"
          placeholder="Selecione usuários"
          values={etapa.usuarioResponsavelIds}
          onChange={(values) =>
            onChange({ ...etapa, usuarioResponsavelIds: values })
          }
          options={responsaveisProjetoDisponiveis.map((responsavel) => ({
            value: responsavel.id,
            label: responsavel.nome,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          placeholder="Selecione departamentos"
          values={etapa.departamentoResponsavelIds}
          onChange={(values) =>
            onChange({ ...etapa, departamentoResponsavelIds: values })
          }
          options={departamentosProjetoDisponiveis.map((departamento) => ({
            value: departamento.id,
            label: departamento.nome,
          }))}
        />
      </div>
    </div>
  );
}
