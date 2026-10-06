"use client";

import { useState } from "react";
import { Building2, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { Modal } from "@/components/ui/Modal";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";
import { coresIdentificacaoDisponiveis, estiloCorIdentificacao } from "@/lib/cores";
import { useUsuariosSelector } from "@/lib/useResponsaveisSelector";
import type { Departamento, DepartamentoFormDraft } from "@/types/departamento";

function createInitialDraft(departamento?: Departamento): DepartamentoFormDraft {
  return {
    nome: departamento?.nome ?? "",
    descricao: departamento?.descricao ?? "",
    responsavelId: departamento?.responsavelId ?? "",
    status: departamento?.status === "inativo" ? "inativo" : "ativo",
    corIdentificacao: departamento?.corIdentificacao ?? coresIdentificacaoDisponiveis[0].id,
  };
}

export function DepartamentoFormModal({
  open,
  departamento,
  onClose,
  onSave,
  salvando,
}: {
  open: boolean;
  departamento?: Departamento;
  onClose: () => void;
  onSave: (draft: DepartamentoFormDraft, departamentoId?: string) => void;
  salvando?: boolean;
}) {
  const [draft, setDraft] = useState<DepartamentoFormDraft>(() => createInitialDraft(departamento));
  const { buscarOpcoes, resolverSelecionados } = useUsuariosSelector();

  const editing = departamento !== undefined;
  const canSave = draft.nome.trim().length > 0;

  function updateDraft(patch: Partial<DepartamentoFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-sm font-bold text-white"
            style={estiloCorIdentificacao(draft.corIdentificacao)}
          >
            {draft.nome.trim().slice(0, 2).toUpperCase() || <Building2 className="h-5 w-5" />}
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-fg">
              {editing ? `Editando: ${departamento.nome}` : "Novo departamento"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-fg-muted">
              Cadastro local — usado nos filtros de Usuários e Projetos.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="rounded-full p-2 text-fg-subtle transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-6 flex flex-col gap-4">
        <Input label="Nome" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <Textarea
          label="Descrição"
          rows={3}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
        />

        {/* Busca no servidor (sem o corte de 200). Oferece usuário ativo; o já selecionado continua
            visível mesmo se arquivado/inativo/bloqueado (resolvido por id). Identidade = UUID. */}
        <MemberSelector
          label="Responsável"
          multiple={false}
          values={draft.responsavelId ? [draft.responsavelId] : []}
          onChange={(values) => updateDraft({ responsavelId: values[0] ?? "" })}
          placeholder="Sem responsável"
          buscarOpcoes={buscarOpcoes}
          resolverSelecionados={resolverSelecionados}
          emptyLabel="Nenhum usuário encontrado"
        />

        <div className="rounded-xl border border-zinc-200 bg-surface px-3.5 py-2.5 dark:border-zinc-700">
          <Switch checked={draft.status === "ativo"} onChange={(checked) => updateDraft({ status: checked ? "ativo" : "inativo" })} label={draft.status === "ativo" ? "Ativo" : "Inativo"} />
        </div>

        <div>
          <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Cor de identificação</span>
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
        <Button type="button" disabled={!canSave || salvando} onClick={() => onSave(draft, departamento?.id)}>
          {salvando ? "Salvando…" : "Salvar alterações"}
        </Button>
      </div>
    </Modal>
  );
}
