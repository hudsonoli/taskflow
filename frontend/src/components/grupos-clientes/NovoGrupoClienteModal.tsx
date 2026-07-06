"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Tabs } from "@/components/ui/Tabs";
import {
  cloneGrupoCliente,
  createEmptyGrupoClienteDraft,
} from "@/lib/grupo-cliente-mock";
import type { GrupoClienteDraft } from "@/types/grupo-cliente";
import { ContatosSection, DadosSection } from "./GrupoClienteFormSections";

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "contatos", label: "Contatos" },
];

type NovoGrupoClienteModalProps = {
  open: boolean;
  onClose: () => void;
  onSave: (draft: GrupoClienteDraft) => void;
  grupoCliente?: GrupoClienteDraft;
};

export function NovoGrupoClienteModal({
  open,
  onClose,
  onSave,
  grupoCliente,
}: NovoGrupoClienteModalProps) {
  const editing = grupoCliente !== undefined;
  const [activeTab, setActiveTab] = useState("dados");
  const [draft, setDraft] = useState<GrupoClienteDraft>(() =>
    grupoCliente ? cloneGrupoCliente(grupoCliente) : createEmptyGrupoClienteDraft()
  );


  const canSave =
    draft.nome.trim().length > 0 && draft.sigla.trim().length > 0;

  function handleClose() {
    setActiveTab("dados");
    setDraft(createEmptyGrupoClienteDraft());
    onClose();
  }

  function handleSave() {
    onSave({
      ...draft,
      updatedAt: new Date().toISOString(),
    });
    handleClose();
  }

  return (
    <Modal open={open} onClose={handleClose} maxWidthClassName="max-w-4xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            {editing ? "Editar grupo de clientes" : "Novo grupo de clientes"}
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Código interno: {draft.codigoInterno}
          </p>
        </div>

        <button
          type="button"
          onClick={handleClose}
          aria-label="Fechar"
          className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
        >
          ✕
        </button>
      </div>

      <div className="mt-6">
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      <div className="mt-6 max-h-[55vh] overflow-y-auto pr-1">
        {activeTab === "dados" && (
          <DadosSection draft={draft} onChange={setDraft} />
        )}

        {activeTab === "contatos" && <ContatosSection />}
      </div>

      <div className="mt-6 flex justify-end gap-3 border-t border-zinc-100 pt-4">
        <Button variant="secondary" onClick={handleClose}>
          Cancelar
        </Button>

        <Button onClick={handleSave} disabled={!canSave}>
          {editing ? "Salvar Alterações" : "Salvar Grupo"}
        </Button>
      </div>
    </Modal>
  );
}
