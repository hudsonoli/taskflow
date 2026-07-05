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
  generateFornecedorId,
  generateSigla,
  mockCnpjLookup,
} from "@/lib/fornecedor-mock";
import type { FornecedorDraft } from "@/types/fornecedor";
import {
  ContatosSection,
  DadosSection,
  EnderecoSection,
  HistoricoSection,
} from "./FornecedorFormSections";

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "endereco", label: "Endereço" },
  { id: "contatos", label: "Contatos" },
  { id: "historico", label: "Histórico" },
];

function cloneFornecedor(
  fornecedor: FornecedorDraft
): FornecedorDraft {
  return {
    ...fornecedor,
    endereco: { ...fornecedor.endereco },
    contatos: fornecedor.contatos.map((contato) => ({
      ...contato,
    })),
    historico: fornecedor.historico.map((evento) => ({
      ...evento,
    })),
  };
}

function createEmptyDraft(): FornecedorDraft {
  const now = new Date().toISOString();

  return {
    fornecedorId: generateFornecedorId(),
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "",
    tipoDocumento: "cnpj",
    documento: "",
    nomeRazaoSocial: "",
    nomeFantasia: "",
    sigla: "",
    categoria: "Outros",
    email: "",
    telefone: "",
    celular: "",
    site: "",
    status: "Ativo",
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
    createdAt: now,
    updatedAt: now,
  };
}

type NovoFornecedorModalProps = {
  open: boolean;
  onClose: () => void;
  onSave: (draft: FornecedorDraft) => void;
  fornecedor?: FornecedorDraft;
};

type FornecedorModalContentProps = Omit<
  NovoFornecedorModalProps,
  "open"
>;

function FornecedorModalContent({
  onClose,
  onSave,
  fornecedor,
}: FornecedorModalContentProps) {
  const editing = fornecedor !== undefined;
  const [step, setStep] = useState<"documento" | "cadastro">(
    editing ? "cadastro" : "documento"
  );
  const [documentoInput, setDocumentoInput] = useState(
    fornecedor?.documento ?? ""
  );
  const [loadingLookup, setLoadingLookup] = useState(false);
  const [activeTab, setActiveTab] = useState("dados");
  const [siglaTouched, setSiglaTouched] = useState(editing);
  const [draft, setDraft] = useState<FornecedorDraft>(() =>
    fornecedor ? cloneFornecedor(fornecedor) : createEmptyDraft()
  );

  const documentType = detectDocumentType(documentoInput);
  const canContinue = documentType !== null;
  const canSave =
    draft.documento.length > 0 &&
    (draft.nomeFantasia.trim().length > 0 ||
      draft.nomeRazaoSocial.trim().length > 0);

  function handleDocumentContinue() {
    if (!documentType) return;

    const digits = documentoInput.replace(/\D/g, "");
    const codigoInterno = generateCodigoInterno();

    if (documentType === "cnpj") {
      setLoadingLookup(true);

      window.setTimeout(() => {
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
      }, 500);

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
      sigla: siglaTouched
        ? current.sigla
        : generateSigla(value),
    }));
  }

  function handleSiglaChange(value: string) {
    setSiglaTouched(true);
    setDraft((current) => ({
      ...current,
      sigla: value,
    }));
  }

  function handleSave() {
    const now = new Date();
    const evento = {
      id: `evento-fornecedor-${now.getTime()}`,
      usuarioId: "usuario-atual",
      usuario: "Usuário atual",
      dataHora: now.toLocaleString("pt-BR"),
      dispositivo: "Navegador",
      ipOrigem: "Local",
      acao: editing
        ? "Fornecedor atualizado."
        : "Fornecedor criado.",
    };

    onSave({
      ...draft,
      createdAt: editing ? draft.createdAt : now.toISOString(),
      updatedAt: now.toISOString(),
      historico: [...draft.historico, evento],
    });
    onClose();
  }

  return (
    <Modal
      open
      onClose={onClose}
      maxWidthClassName="max-w-4xl"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-zinc-900">
            {editing ? "Editar Fornecedor" : "Novo Fornecedor"}
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            {step === "documento"
              ? "Informe o CNPJ ou CPF para iniciar o cadastro."
              : `Código interno: ${draft.codigoInterno}`}
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

      {step === "documento" && (
        <div className="mt-6 space-y-4">
          <Input
            label="CNPJ ou CPF"
            placeholder="Digite o CNPJ ou CPF"
            value={documentoInput}
            onChange={(event) =>
              setDocumentoInput(
                formatDocument(event.target.value)
              )
            }
          />

          {documentoInput.length > 0 && (
            <p className="text-xs text-zinc-400">
              {documentType === "cnpj" &&
                "Documento identificado como CNPJ."}
              {documentType === "cpf" &&
                "Documento identificado como CPF."}
              {documentType === null &&
                "Informe um CNPJ (14 dígitos) ou CPF (11 dígitos)."}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              disabled={!canContinue || loadingLookup}
              onClick={handleDocumentContinue}
            >
              {loadingLookup
                ? "Buscando dados..."
                : "Continuar"}
            </Button>
          </div>
        </div>
      )}

      {step === "cadastro" && (
        <div className="mt-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>
              {draft.tipoDocumento === "cnpj" ? "CNPJ" : "CPF"}
            </Badge>
            <Badge>{draft.categoria}</Badge>
          </div>

          <div className="mt-4">
            <Tabs
              tabs={tabs}
              activeTab={activeTab}
              onChange={setActiveTab}
            />
          </div>

          <div className="mt-6 max-h-[52vh] overflow-y-auto pr-1">
            {activeTab === "dados" && (
              <DadosSection
                draft={draft}
                onChange={setDraft}
                onNomeFantasiaChange={handleNomeFantasiaChange}
                onSiglaChange={handleSiglaChange}
              />
            )}
            {activeTab === "endereco" && (
              <EnderecoSection
                draft={draft}
                onChange={setDraft}
              />
            )}
            {activeTab === "contatos" && (
              <ContatosSection
                draft={draft}
                onChange={setDraft}
              />
            )}
            {activeTab === "historico" && (
              <HistoricoSection
                draft={draft}
                onChange={setDraft}
              />
            )}
          </div>

          <div className="mt-6 flex justify-end gap-3 border-t border-zinc-100 pt-4">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button disabled={!canSave} onClick={handleSave}>
              {editing
                ? "Salvar Alterações"
                : "Salvar Fornecedor"}
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

export function NovoFornecedorModal({
  open,
  ...props
}: NovoFornecedorModalProps) {
  if (!open) return null;

  return <FornecedorModalContent {...props} />;
}
