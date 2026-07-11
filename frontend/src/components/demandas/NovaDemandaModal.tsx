"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  departamentosProjetoDisponiveis,
  prioridadeDemandaLabels,
  projetosDemandaDisponiveis,
  resolveClienteIdByProjetoId,
  resolveClienteProjetoNome,
  responsaveisProjetoDisponiveis,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import type {
  Demanda,
  DemandaFormDraft,
  DemandaPrioridade,
  DemandaStatus,
} from "@/types/demanda";

type NovaDemandaModalProps = {
  open: boolean;
  demanda?: Demanda;
  onClose: () => void;
  onSaveAndClose: (draft: DemandaFormDraft, demandaId?: string) => void;
  onSaveAndContinue: (draft: DemandaFormDraft, demandaId?: string) => void;
};

function createInitialDraft(demanda?: Demanda): DemandaFormDraft {
  const defaultProjectId = projetosDemandaDisponiveis[0]?.id ?? "";
  const projectId = demanda?.projetoId ?? defaultProjectId;

  return {
    nome: demanda?.nome ?? "",
    projetoId: projectId,
    clienteId: demanda?.clienteId ?? resolveClienteIdByProjetoId(projectId),
    briefing: demanda?.briefing ?? "",
    prioridade: demanda?.prioridade ?? "media",
    status: demanda?.status ?? "planejada",
    usuarioResponsavelIds:
      demanda?.usuarioResponsavelIds ?? [responsaveisProjetoDisponiveis[0].id],
    departamentoResponsavelIds:
      demanda?.departamentoResponsavelIds ?? [
        departamentosProjetoDisponiveis[0].id,
      ],
    dataFimPrevista: demanda?.dataFimPrevista ?? "",
  };
}

export function NovaDemandaModal({
  open,
  demanda,
  onClose,
  onSaveAndClose,
  onSaveAndContinue,
}: NovaDemandaModalProps) {
  const [draft, setDraft] = useState<DemandaFormDraft>(() =>
    createInitialDraft(demanda)
  );

  const editing = demanda !== undefined;
  const canSave = draft.nome.trim().length > 0 && draft.projetoId.length > 0;

  function updateDraft(patch: Partial<DemandaFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function handleProjectChange(projectId: string) {
    updateDraft({
      projetoId: projectId,
      clienteId: resolveClienteIdByProjetoId(projectId),
    });
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            {editing ? "Editar Demanda" : "Nova Demanda"}
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            Cadastro local para estruturar demandas, briefing e responsáveis.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
        >
          ✕
        </button>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Input
          label="Nome"
          value={draft.nome}
          onChange={(event) => updateDraft({ nome: event.target.value })}
        />
        <Select
          label="Projeto"
          value={draft.projetoId}
          onChange={(event) => handleProjectChange(event.target.value)}
          options={projetosDemandaDisponiveis.map((projeto) => ({
            value: projeto.id,
            label: projeto.nome,
          }))}
        />
        <Input
          label="Cliente derivado do projeto"
          value={resolveClienteProjetoNome(draft.clienteId)}
          disabled
        />
        <Input
          label="Data prevista"
          type="date"
          value={draft.dataFimPrevista}
          onChange={(event) =>
            updateDraft({ dataFimPrevista: event.target.value })
          }
        />
        <Select
          label="Prioridade"
          value={draft.prioridade}
          onChange={(event) =>
            updateDraft({ prioridade: event.target.value as DemandaPrioridade })
          }
          options={Object.entries(prioridadeDemandaLabels).map(
            ([value, label]) => ({ value, label })
          )}
        />
        <Select
          label="Status"
          value={draft.status}
          onChange={(event) =>
            updateDraft({ status: event.target.value as DemandaStatus })
          }
          options={Object.entries(statusDemandaLabels).map(([value, label]) => ({
            value,
            label,
          }))}
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <MultiSelect
          label="Usuários responsáveis"
          placeholder="Selecione usuários"
          values={draft.usuarioResponsavelIds}
          onChange={(values) => updateDraft({ usuarioResponsavelIds: values })}
          options={responsaveisProjetoDisponiveis.map((responsavel) => ({
            value: responsavel.id,
            label: responsavel.nome,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          placeholder="Selecione departamentos"
          values={draft.departamentoResponsavelIds}
          onChange={(values) =>
            updateDraft({ departamentoResponsavelIds: values })
          }
          options={departamentosProjetoDisponiveis.map((departamento) => ({
            value: departamento.id,
            label: departamento.nome,
          }))}
        />
      </div>

      <div className="mt-4">
        <Textarea
          label="Briefing"
          rows={5}
          value={draft.briefing}
          onChange={(event) => updateDraft({ briefing: event.target.value })}
        />
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={!canSave}
          onClick={() => onSaveAndContinue(draft, demanda?.id)}
        >
          Salvar e continuar
        </Button>
        <Button
          type="button"
          disabled={!canSave}
          onClick={() => onSaveAndClose(draft, demanda?.id)}
        >
          Salvar e fechar
        </Button>
      </div>
    </Modal>
  );
}
