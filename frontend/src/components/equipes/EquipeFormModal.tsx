"use client";

import { useState } from "react";
import { UsersRound, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";
import { coresIdentificacaoDisponiveis, resolveCorIdentificacaoHex } from "@/lib/cores";
import { normalizarReferenciasParaCodigoInterno } from "@/lib/referencias";
import type { UsuarioDiretorioItem } from "@/lib/api-backend";
import type { Equipe, EquipeFormDraft } from "@/types/equipe";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";

function createInitialDraft(equipe?: Equipe): EquipeFormDraft {
  return {
    nome: equipe?.nome ?? "",
    descricao: equipe?.descricao ?? "",
    liderId: equipe?.liderId ?? "",
    membroIds: equipe?.membroIds ?? [],
    corIdentificacao: equipe?.corIdentificacao ?? coresIdentificacaoDisponiveis[0].id,
    status: equipe?.status === "inativo" ? "inativo" : "ativo",
    departamentoId: equipe?.departamentoId ?? null,
  };
}

export function EquipeFormModal({
  open,
  equipe,
  usuarios,
  onClose,
  onSave,
  departamentos,
  salvando,
}: {
  open: boolean;
  equipe?: Equipe;
  usuarios: UsuarioDiretorioItem[];
  onClose: () => void;
  onSave: (draft: EquipeFormDraft, equipeId?: string) => void;
  departamentos: DepartamentoDiretorioItem[];
  salvando?: boolean;
}) {
  const [draft, setDraft] = useState<EquipeFormDraft>(() => createInitialDraft(equipe));

  const editing = equipe !== undefined;
  const canSave = draft.nome.trim().length > 0;

  function updateDraft(patch: Partial<EquipeFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  // Picker só oferece usuário ativo; grava codigoInterno enquanto Equipe continuar mock —
  // ver docs/padrao-arquivamento.md / lib/referencias.ts.
  const memberOptions = usuarios
    .filter((usuario) => usuario.status === "ativo")
    .map((usuario) => ({
      id: usuario.codigoInterno,
      nome: usuario.nome,
      corIdentificacao: usuario.corIdentificacao,
      fotoUrl: usuario.fotoUrl,
    }));

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-sm font-bold text-white"
            style={{ backgroundColor: resolveCorIdentificacaoHex(draft.corIdentificacao) }}
          >
            {draft.nome.trim().slice(0, 2).toUpperCase() || <UsersRound className="h-5 w-5" />}
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${equipe.nome}` : "Nova equipe"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Cadastro local — squads e times para organizar a operação.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <Input label="Nome" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <Select
          label="Departamento"
          value={draft.departamentoId ?? ""}
          onChange={(event) => updateDraft({ departamentoId: event.target.value || null })}
          options={[
            // Sem departamento = squad transversal (gente de várias áreas). É um caso
            // legítimo, por isso a opção é explícita e não um "vazio" acidental.
            { value: "", label: "Transversal (sem departamento)" },
            // Departamento arquivado não aceita vínculo novo — só aparece se já for o atual.
            ...departamentos
              .filter((d) => d.status !== "arquivado" || d.id === draft.departamentoId)
              .map((d) => ({
                value: d.id,
                label: d.status === "arquivado" ? `${d.nome} (arquivado)` : d.nome,
              })),
          ]}
        />

        <Textarea
          label="Descrição"
          rows={3}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
        />

        <MemberSelector
          label="Líder"
          multiple={false}
          values={draft.liderId ? normalizarReferenciasParaCodigoInterno([draft.liderId], usuarios) : []}
          onChange={(values) => updateDraft({ liderId: values[0] ?? "" })}
          placeholder="Sem líder"
          options={memberOptions}
        />

        <MemberSelector
          label="Membros"
          values={normalizarReferenciasParaCodigoInterno(draft.membroIds, usuarios)}
          onChange={(values) => updateDraft({ membroIds: values })}
          placeholder="Selecionar membros…"
          options={memberOptions}
        />

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch checked={draft.status === "ativo"} onChange={(checked) => updateDraft({ status: checked ? "ativo" : "inativo" })} label={draft.status === "ativo" ? "Ativa" : "Inativa"} />
        </div>

        <div>
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">Cor de identificação</span>
          <div className="flex flex-wrap gap-2">
            {coresIdentificacaoDisponiveis.map((cor) => (
              <button
                key={cor.id}
                type="button"
                aria-label={cor.id}
                onClick={() => updateDraft({ corIdentificacao: cor.id })}
                className={
                  draft.corIdentificacao === cor.id
                    ? "h-7 w-7 rounded-full ring-2 ring-offset-2 ring-zinc-900 dark:ring-offset-zinc-900 dark:ring-zinc-100"
                    : "h-7 w-7 rounded-full"
                }
                style={{ backgroundColor: cor.hex }}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave || salvando} onClick={() => onSave(draft, equipe?.id)}>
          {salvando ? "Salvando…" : "Salvar alterações"}
        </Button>
      </div>
    </Modal>
  );
}
