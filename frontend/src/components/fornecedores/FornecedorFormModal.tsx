"use client";

import { useState } from "react";
import { Truck, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Tabs } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";
import {
  categoriasFornecedorDisponiveis,
  detectDocumentType,
  formatDocument,
  statusFornecedorEditaveis,
  statusFornecedorLabels,
} from "@/lib/fornecedores";
import { coresIdentificacaoDisponiveis, resolveCorIdentificacaoHex } from "@/lib/cores";
import type { Fornecedor, FornecedorFormDraft, FornecedorStatusEditavel } from "@/types/fornecedor";

const ufsDisponiveis = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
  "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "contato", label: "Contato" },
  { id: "endereco", label: "Endereço" },
];

function createInitialDraft(fornecedor?: Fornecedor): FornecedorFormDraft {
  // `arquivado` nunca chega aqui: a tabela oferece Restaurar, não Editar, para arquivados.
  const status: FornecedorStatusEditavel =
    fornecedor?.status === "inativo" ? "inativo" : "ativo";
  return {
    tipoDocumento: fornecedor?.tipoDocumento ?? "cnpj",
    documento: fornecedor?.documento ?? "",
    nome: fornecedor?.nome ?? "",
    categoria: fornecedor?.categoria ?? "",
    contatoNome: fornecedor?.contatoNome ?? "",
    email: fornecedor?.email ?? "",
    whatsapp: fornecedor?.whatsapp ?? "",
    site: fornecedor?.site ?? "",
    cep: fornecedor?.cep ?? "",
    bairro: fornecedor?.bairro ?? "",
    enderecoCompleto: fornecedor?.enderecoCompleto ?? "",
    cidade: fornecedor?.cidade ?? "",
    uf: fornecedor?.uf ?? "",
    status,
    observacoes: fornecedor?.observacoes ?? "",
    corIdentificacao: fornecedor?.corIdentificacao ?? coresIdentificacaoDisponiveis[0].id,
  };
}

export function FornecedorFormModal({
  open,
  fornecedor,
  salvando,
  onClose,
  onSave,
}: {
  open: boolean;
  fornecedor?: Fornecedor;
  salvando: boolean;
  onClose: () => void;
  onSave: (draft: FornecedorFormDraft, fornecedorId?: string) => void;
}) {
  const [draft, setDraft] = useState<FornecedorFormDraft>(() => createInitialDraft(fornecedor));
  const [activeTab, setActiveTab] = useState("dados");

  const editing = fornecedor !== undefined;
  const canSave = draft.nome.trim().length > 0 && !salvando;
  const documentoLabel = draft.tipoDocumento === "cpf" ? "CPF" : "CNPJ";

  function updateDraft(patch: Partial<FornecedorFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function handleDocumentoChange(rawValue: string) {
    const tipo = detectDocumentType(rawValue) ?? draft.tipoDocumento;
    updateDraft({ documento: formatDocument(rawValue), tipoDocumento: tipo });
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-2xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-sm font-bold text-white"
            style={{ backgroundColor: resolveCorIdentificacaoHex(draft.corIdentificacao) }}
          >
            {draft.nome.trim().slice(0, 2).toUpperCase() || <Truck className="h-5 w-5" />}
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${fornecedor.nome}` : "Novo fornecedor"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Gráficas, produtoras, freelancers, mídia.
              {editing && (
                <span className="ml-1 font-mono text-xs opacity-70">{fornecedor.codigoReferencia}</span>
              )}
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

      <div className="mt-5">
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      <div className="mt-5 flex flex-col gap-4">
        {activeTab === "dados" && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <Input label="Nome" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />
              <div>
                <Input
                  label="Categoria"
                  value={draft.categoria}
                  onChange={(event) => updateDraft({ categoria: event.target.value })}
                  list="fornecedores-categorias"
                  placeholder="ex.: Gráfica, Freelancer"
                />
                <datalist id="fornecedores-categorias">
                  {categoriasFornecedorDisponiveis.map((categoria) => (
                    <option key={categoria} value={categoria} />
                  ))}
                </datalist>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label={documentoLabel}
                value={draft.documento}
                onChange={(event) => handleDocumentoChange(event.target.value)}
                placeholder="00.000.000/0000-00"
              />
              {/* Só ativo e inativo: `arquivado` entra pela ação Arquivar, com motivo. */}
              <Select
                label="Status"
                value={draft.status}
                onChange={(event) => updateDraft({ status: event.target.value as FornecedorStatusEditavel })}
                options={statusFornecedorEditaveis.map((value) => ({
                  value,
                  label: statusFornecedorLabels[value],
                }))}
              />
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
          </>
        )}

        {activeTab === "contato" && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <Input label="Pessoa de contato" value={draft.contatoNome} onChange={(event) => updateDraft({ contatoNome: event.target.value })} />
              <Input label="Site" value={draft.site} onChange={(event) => updateDraft({ site: event.target.value })} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input label="E-mail" type="email" value={draft.email} onChange={(event) => updateDraft({ email: event.target.value })} />
              <Input label="WhatsApp / telefone" value={draft.whatsapp} onChange={(event) => updateDraft({ whatsapp: event.target.value })} />
            </div>

            <Textarea
              label="Observações"
              rows={3}
              placeholder="Prazos, condições de pagamento, histórico…"
              value={draft.observacoes}
              onChange={(event) => updateDraft({ observacoes: event.target.value })}
            />
          </>
        )}

        {activeTab === "endereco" && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <Input label="CEP" value={draft.cep} onChange={(event) => updateDraft({ cep: event.target.value })} />
              <Input label="Bairro" value={draft.bairro} onChange={(event) => updateDraft({ bairro: event.target.value })} />
            </div>

            <Input
              label="Endereço (rua, número e complemento)"
              value={draft.enderecoCompleto}
              onChange={(event) => updateDraft({ enderecoCompleto: event.target.value })}
            />

            <div className="grid gap-4 md:grid-cols-[1fr_120px]">
              <Input label="Cidade" value={draft.cidade} onChange={(event) => updateDraft({ cidade: event.target.value })} />
              <Select
                label="UF"
                value={draft.uf}
                onChange={(event) => updateDraft({ uf: event.target.value })}
                options={[{ value: "", label: "-" }, ...ufsDisponiveis.map((uf) => ({ value: uf, label: uf }))]}
              />
            </div>
          </>
        )}
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSave(draft, fornecedor?.id)}>
          {salvando ? "Salvando…" : "Salvar alterações"}
        </Button>
      </div>
    </Modal>
  );
}
