"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Tabs } from "@/components/ui/Tabs";
import {
  EMPRESA_PADRAO_ID,
  detectDocumentType,
  formatDocument,
  generateCodigoInterno,
  generateId,
  generateSigla,
  mockCnpjLookup,
} from "@/lib/cliente-mock";
import type { ClienteDraft } from "@/types/cliente";
import {
  ContatosSection,
  DadosSection,
  EnderecoSection,
  EquipeSection,
  HistoricoSection,
} from "./ClienteFormSections";

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "endereco", label: "Endereço" },
  { id: "contatos", label: "Contatos" },
  { id: "equipe", label: "Equipe" },
  { id: "historico", label: "Histórico" },
];

function cloneCliente(cliente: ClienteDraft): ClienteDraft {
  return {
    ...cliente,
    endereco: { ...cliente.endereco },
    contatos: cliente.contatos.map((contato) => ({ ...contato })),
    historico: cliente.historico.map((evento) => ({ ...evento })),
  };
}

function createEmptyDraft(): ClienteDraft {
  return {
    clienteId: generateId("cliente"),
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "",
    tipoDocumento: "cnpj",
    documento: "",
    nomeRazaoSocial: "",
    nomeFantasia: "",
    sigla: "",
    email: "",
    telefone: "",
    celular: "",
    site: "",
    status: "Ativo",
    equipeResponsavelId: undefined,
    responsavelComercialId: undefined,
    responsavelAtendimentoId: undefined,
    endereco: {
      cep: "",
      logradouro: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "",
      uf: "",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
  };
}

type NovoClienteModalProps = {
  open: boolean;
  onClose: () => void;
  onCreate: (draft: ClienteDraft) => void;
  cliente?: ClienteDraft;
};

export function NovoClienteModal({
  open,
  onClose,
  onCreate,
  cliente,
}: NovoClienteModalProps) {
  const editing = cliente !== undefined;
  const [step, setStep] = useState<"documento" | "cadastro">(
    editing ? "cadastro" : "documento"
  );
  const [documentoInput, setDocumentoInput] = useState(
    cliente?.documento ?? ""
  );
  const [loadingLookup, setLoadingLookup] = useState(false);
  const [activeTab, setActiveTab] = useState("dados");
  const [siglaTouched, setSiglaTouched] = useState(editing);
  const [draft, setDraft] = useState<ClienteDraft>(() =>
    cliente ? cloneCliente(cliente) : createEmptyDraft()
  );

  const documentType = detectDocumentType(documentoInput);
  const canContinue = documentType !== null;

  function handleClose() {
    setStep("documento");
    setDocumentoInput("");
    setLoadingLookup(false);
    setActiveTab("dados");
    setSiglaTouched(false);
    setDraft(createEmptyDraft());
    onClose();
  }

  function handleDocumentContinue() {
    if (!documentType) return;

    const digits = documentoInput.replace(/\D/g, "");
    const codigoInterno = generateCodigoInterno();

    if (documentType === "cnpj") {
      setLoadingLookup(true);

      setTimeout(() => {
        const lookup = mockCnpjLookup(digits);

        setDraft((current) => ({
          ...current,
          tipoDocumento: "cnpj",
          documento: formatDocument(documentoInput),
          codigoInterno,
          nomeFantasia: lookup.nomeFantasia,
          nomeRazaoSocial: lookup.nomeRazaoSocial,
          sigla: generateSigla(lookup.nomeFantasia),
        }));

        setLoadingLookup(false);
        setStep("cadastro");
      }, 900);

      return;
    }

    setDraft((current) => ({
      ...current,
      tipoDocumento: "cpf",
      documento: formatDocument(documentoInput),
      codigoInterno,
    }));

    setStep("cadastro");
  }

  function handleNomeFantasiaChange(value: string) {
    setDraft((current) => ({
      ...current,
      nomeFantasia: value,
      sigla: siglaTouched ? current.sigla : generateSigla(value),
    }));
  }

  function handleSiglaChange(value: string) {
    setSiglaTouched(true);
    setDraft((current) => ({ ...current, sigla: value }));
  }

  function handleSave() {
    onCreate(draft);
    handleClose();
  }

  return (
    <Modal open={open} onClose={handleClose} maxWidthClassName="max-w-3xl">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            {editing ? "Editar Cliente" : "Novo Cliente"}
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            {step === "documento"
              ? "Informe o CNPJ ou CPF para iniciar o cadastro."
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

      {step === "documento" && (
        <div className="mt-6 space-y-4">
          <Input
            label="CNPJ ou CPF"
            placeholder="Digite o CNPJ ou CPF"
            value={documentoInput}
            onChange={(event) =>
              setDocumentoInput(formatDocument(event.target.value))
            }
          />

          {documentoInput.length > 0 && (
            <p className="text-xs text-zinc-400">
              {documentType === "cnpj" && "Documento identificado como CNPJ."}
              {documentType === "cpf" && "Documento identificado como CPF."}
              {documentType === null &&
                "Informe um CNPJ (14 dígitos) ou CPF (11 dígitos) válido."}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={handleClose}>
              Cancelar
            </Button>

            <Button
              disabled={!canContinue || loadingLookup}
              onClick={handleDocumentContinue}
            >
              {loadingLookup ? "Buscando dados..." : "Continuar"}
            </Button>
          </div>
        </div>
      )}

      {step === "cadastro" && (
        <div className="mt-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{draft.tipoDocumento === "cnpj" ? "CNPJ" : "CPF"}</Badge>
          </div>

          <div className="mt-4">
            <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
          </div>

          <div className="mt-6 max-h-[50vh] overflow-y-auto pr-1">
            {activeTab === "dados" && (
              <DadosSection
                draft={draft}
                onChange={setDraft}
                onNomeFantasiaChange={handleNomeFantasiaChange}
                onSiglaChange={handleSiglaChange}
              />
            )}

            {activeTab === "endereco" && (
              <EnderecoSection draft={draft} onChange={setDraft} />
            )}

            {activeTab === "contatos" && (
              <ContatosSection draft={draft} onChange={setDraft} />
            )}

            {activeTab === "equipe" && (
              <EquipeSection draft={draft} onChange={setDraft} />
            )}

            {activeTab === "historico" && <HistoricoSection />}
          </div>

          <div className="mt-6 flex justify-end gap-3 border-t border-zinc-100 pt-4">
            <Button variant="secondary" onClick={handleClose}>
              Cancelar
            </Button>

            <Button onClick={handleSave}>
              {editing ? "Salvar Alterações" : "Salvar Cliente"}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
