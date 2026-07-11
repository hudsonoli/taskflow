"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  clientesProjetoDisponiveis,
  prioridadeProjetoLabels,
  responsaveisProjetoDisponiveis,
  statusProjetoLabels,
} from "@/lib/projetos-mock";
import type { Projeto, ProjetoFormDraft, ProjetoPrioridade, ProjetoStatus } from "@/types/projeto";

type NovoProjetoModalProps = {
  open: boolean;
  projeto?: Projeto;
  onClose: () => void;
  onSaveAndClose: (draft: ProjetoFormDraft, projetoId?: string) => void;
  onSaveAndContinue: (draft: ProjetoFormDraft, projetoId?: string) => void;
};

function createInitialDraft(projeto?: Projeto): ProjetoFormDraft {
  return {
    nome: projeto?.nome ?? "",
    clienteId: projeto?.clienteId ?? clientesProjetoDisponiveis[0].id,
    campanha: projeto?.campanha ?? "",
    responsavelId:
      projeto?.responsavelId ?? responsaveisProjetoDisponiveis[0].id,
    dataInicio: projeto?.dataInicio ?? "",
    dataFimPrevista: projeto?.dataFimPrevista ?? "",
    status: projeto?.status ?? "planejamento",
    prioridade: projeto?.prioridade ?? "media",
    descricao: projeto?.descricao ?? "",
  };
}

export function NovoProjetoModal({
  open,
  projeto,
  onClose,
  onSaveAndClose,
  onSaveAndContinue,
}: NovoProjetoModalProps) {
  const [draft, setDraft] = useState<ProjetoFormDraft>(() =>
    createInitialDraft(projeto)
  );

  const editing = projeto !== undefined;
  const canSave = draft.nome.trim().length > 0 && draft.campanha.trim().length > 0;

  function updateDraft(patch: Partial<ProjetoFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            {editing ? "Editar Projeto" : "Novo Projeto"}
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            {editing
              ? "Atualize os dados mock do projeto."
              : "Cadastre um projeto local para organizar campanha, equipe e modelo de demandas."}
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
          label="Nome do projeto"
          value={draft.nome}
          onChange={(event) => updateDraft({ nome: event.target.value })}
        />
        <Select
          label="Cliente"
          value={draft.clienteId}
          onChange={(event) => updateDraft({ clienteId: event.target.value })}
          options={clientesProjetoDisponiveis.map((cliente) => ({
            value: cliente.id,
            label: cliente.nome,
          }))}
        />
        <Input
          label="Campanha"
          value={draft.campanha}
          onChange={(event) => updateDraft({ campanha: event.target.value })}
        />
        <Select
          label="Responsável"
          value={draft.responsavelId}
          onChange={(event) =>
            updateDraft({ responsavelId: event.target.value })
          }
          options={responsaveisProjetoDisponiveis.map((responsavel) => ({
            value: responsavel.id,
            label: responsavel.nome,
          }))}
        />
        <Input
          label="Data de início"
          type="date"
          value={draft.dataInicio}
          onChange={(event) => updateDraft({ dataInicio: event.target.value })}
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
          label="Status"
          value={draft.status}
          onChange={(event) =>
            updateDraft({ status: event.target.value as ProjetoStatus })
          }
          options={Object.entries(statusProjetoLabels).map(([value, label]) => ({
            value,
            label,
          }))}
        />
        <Select
          label="Prioridade"
          value={draft.prioridade}
          onChange={(event) =>
            updateDraft({
              prioridade: event.target.value as ProjetoPrioridade,
            })
          }
          options={Object.entries(prioridadeProjetoLabels).map(
            ([value, label]) => ({
              value,
              label,
            })
          )}
        />
      </div>

      <div className="mt-4">
        <Textarea
          label="Descrição"
          rows={4}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
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
          onClick={() => onSaveAndContinue(draft, projeto?.id)}
        >
          Salvar e continuar
        </Button>
        <Button
          type="button"
          disabled={!canSave}
          onClick={() => onSaveAndClose(draft, projeto?.id)}
        >
          Salvar e fechar
        </Button>
      </div>
    </Modal>
  );
}
