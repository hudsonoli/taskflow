"use client";

import { useState } from "react";
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

function cloneCliente(cliente: ClienteDraft): ClienteDraft {
  return {
    ...cliente,
    endereco: { ...cliente.endereco },
    contatos: cliente.contatos.map((contato) => ({ ...contato })),
    administrativo: {
      feeMensal: { ...cliente.administrativo.feeMensal },
      dadosBancarios: { ...cliente.administrativo.dadosBancarios },
    },
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
    administrativo: {
      feeMensal: {
        valor: null,
        moeda: "BRL",
        dataInicio: "",
        observacao: "",
      },
      dadosBancarios: {
        chavePix: "",
        banco: "",
        agencia: "",
        conta: "",
        tipoConta: "Corrente",
      },
    },
    historico: [],
  };
}

export type ClienteDraftStep = "documento" | "cadastro";

/**
 * Estado de edição/criação de um Cliente — extraído do antigo
 * NovoClienteModal.tsx sem nenhuma alteração de lógica de negócio (mesmos
 * handlers, mesma regra de geração de código/sigla, mesmo lookup mock).
 *
 * resetToken força uma reinicialização completa sempre que uma NOVA sessão
 * de edição começa (cliente diferente, nova criação, ou reabertura após
 * cancelar) — a página incrementa esse valor ao entrar em modo edit.
 */
export function useClienteDraft(cliente: ClienteDraft | undefined, resetToken: number) {
  const editing = cliente !== undefined;

  const [step, setStep] = useState<ClienteDraftStep>(editing ? "cadastro" : "documento");
  const [documentoInput, setDocumentoInput] = useState(cliente?.documento ?? "");
  const [loadingLookup, setLoadingLookup] = useState(false);
  const [activeSection, setActiveSection] = useState("dados");
  const [siglaTouched, setSiglaTouched] = useState(editing);
  const [draft, setDraft] = useState<ClienteDraft>(() =>
    cliente ? cloneCliente(cliente) : createEmptyDraft()
  );

  // Reinicializa todo o estado quando resetToken muda (nova sessão de
  // edição: cliente diferente, nova criação, ou reabertura após cancelar).
  // Ajuste de estado durante o render (padrão oficial do React para "reset
  // ao mudar uma chave"), não em useEffect — evita uma renderização em
  // cascata e satisfaz a regra react-hooks/set-state-in-effect.
  const [lastResetToken, setLastResetToken] = useState(resetToken);

  if (resetToken !== lastResetToken) {
    setLastResetToken(resetToken);
    setStep(editing ? "cadastro" : "documento");
    setDocumentoInput(cliente?.documento ?? "");
    setLoadingLookup(false);
    setActiveSection("dados");
    setSiglaTouched(editing);
    setDraft(cliente ? cloneCliente(cliente) : createEmptyDraft());
  }

  const documentType = detectDocumentType(documentoInput);
  const canContinue = documentType !== null;

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

  return {
    editing,
    step,
    documentoInput,
    setDocumentoInput,
    loadingLookup,
    documentType,
    canContinue,
    handleDocumentContinue,
    activeSection,
    setActiveSection,
    draft,
    setDraft,
    handleNomeFantasiaChange,
    handleSiglaChange,
  };
}
