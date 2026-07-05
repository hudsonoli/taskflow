"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Tabs } from "@/components/ui/Tabs";
import {
  createPermissoesCatalogo,
  departamentos,
  EMPRESA_PADRAO_ID,
  generateCodigoInterno,
  generateId,
} from "@/lib/usuario-mock";
import type { UsuarioDraft } from "@/types/usuario";
import {
  DadosSection,
  EnderecosSection,
  HistoricoSection,
  InformacoesSection,
  PermissoesSection,
} from "./UsuarioFormSections";

const departamentoOptions = [
  { value: "", label: "Selecione" },
  ...departamentos
    .filter((departamento) => departamento.ativo)
    .map((departamento) => ({
      value: departamento.id,
      label: departamento.nome,
    })),
];

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "permissoes", label: "Permissões" },
  { id: "endereco", label: "Endereço" },
  { id: "informacoes", label: "Informações" },
  { id: "historico", label: "Histórico" },
];

function createEmptyDraft(): UsuarioDraft {
  return {
    id: generateId("usuario"),
    codigoInterno: generateCodigoInterno(),
    empresaId: EMPRESA_PADRAO_ID,
    nome: "",
    email: "",
    departamentoId: "",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Operador",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      chavePix: "",
      banco: "",
      agencia: "",
      conta: "",
      rg: "",
      cpf: "",
    },
    historico: [],
  };
}

type NovoUsuarioModalProps = {
  open: boolean;
  onClose: () => void;
  onUpsert: (draft: UsuarioDraft) => void;
};

export function NovoUsuarioModal({
  open,
  onClose,
  onUpsert,
}: NovoUsuarioModalProps) {
  const [step, setStep] = useState<"inicial" | "completo">("inicial");
  const [activeTab, setActiveTab] = useState("dados");
  const [draft, setDraft] = useState<UsuarioDraft>(createEmptyDraft());

  const canSubmit =
    draft.nome.trim() !== "" &&
    draft.email.trim() !== "" &&
    draft.departamentoId !== "";

  function handleClose() {
    setStep("inicial");
    setActiveTab("dados");
    setDraft(createEmptyDraft());
    onClose();
  }

  function handleSalvarFechar() {
    onUpsert(draft);
    handleClose();
  }

  function handleSalvarContinuar() {
    onUpsert(draft);
    setStep("completo");
  }

  function handleSalvarAlteracoes() {
    onUpsert(draft);
    handleClose();
  }

  return (
    <Modal open={open} onClose={handleClose} maxWidthClassName="max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            Novo Colaborador
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            {step === "inicial"
              ? "Informe os dados básicos para criar o colaborador."
              : `Código interno: ${draft.codigoInterno}`}
          </p>
        </div>

        <button
          onClick={handleClose}
          aria-label="Fechar"
          className="rounded-full p-1 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700"
        >
          ✕
        </button>
      </div>

      {step === "inicial" && (
        <div className="mt-6 space-y-4">
          <Input
            label="Nome completo"
            value={draft.nome}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                nome: event.target.value,
              }))
            }
          />

          <Input
            label="E-mail"
            type="email"
            value={draft.email}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                email: event.target.value,
              }))
            }
          />

          <Select
            label="Departamento"
            options={departamentoOptions}
            value={draft.departamentoId}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                departamentoId: event.target.value,
              }))
            }
          />

          <div className="flex flex-wrap justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={handleClose}>
              Cancelar
            </Button>

            <Button
              variant="secondary"
              disabled={!canSubmit}
              onClick={handleSalvarFechar}
            >
              Salvar e fechar
            </Button>

            <Button disabled={!canSubmit} onClick={handleSalvarContinuar}>
              Salvar e continuar
            </Button>
          </div>
        </div>
      )}

      {step === "completo" && (
        <div className="mt-6">
          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          <div className="mt-6 max-h-[50vh] overflow-y-auto pr-1">
            {activeTab === "dados" && (
              <DadosSection draft={draft} onChange={setDraft} />
            )}

            {activeTab === "permissoes" && (
              <PermissoesSection draft={draft} onChange={setDraft} />
            )}

            {activeTab === "endereco" && (
              <EnderecosSection draft={draft} onChange={setDraft} />
            )}

            {activeTab === "informacoes" && (
              <InformacoesSection draft={draft} onChange={setDraft} />
            )}

            {activeTab === "historico" && <HistoricoSection />}
          </div>

          <div className="mt-6 flex justify-end gap-3 border-t border-zinc-100 pt-4">
            <Button variant="secondary" onClick={handleClose}>
              Fechar
            </Button>

            <Button onClick={handleSalvarAlteracoes}>Salvar Alterações</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
