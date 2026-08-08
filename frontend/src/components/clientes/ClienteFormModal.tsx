"use client";

import { useState } from "react";
import { Mail, Plus, Search, Trash2, User, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { Tabs } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";
import {
  coresIdentificacaoDisponiveis,
  detectDocumentType,
  formatDocument,
  generateId,
  mockDocumentoLookup,
  origensClienteDisponiveis,
  resolveCorIdentificacaoHex,
  responsaveisProjetoDisponiveis,
  statusClienteLabels,
} from "@/lib/clientes-mock";
import { useAppData } from "@/lib/AppDataContext";
import { resolverGrupoClientePorReferencia } from "@/lib/referencias";
import { podeVerDadosFinanceiros } from "@/types/usuario";
import type { Cliente, ClienteContato, ClienteFormDraft, ClienteStatus } from "@/types/cliente";
import type { GrupoClienteDiretorioItem } from "@/lib/api-backend";

const ufsDisponiveis = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
  "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

function criarContatoVazio(): ClienteContato {
  return { id: generateId("contato"), nome: "", email: "", telefone: "", cargo: "", recebeEntregas: true };
}

function createInitialDraft(cliente?: Cliente): ClienteFormDraft {
  return {
    tipoDocumento: cliente?.tipoDocumento ?? "cnpj",
    documento: cliente?.documento ?? "",
    nome: cliente?.nome ?? "",
    razaoSocial: cliente?.razaoSocial ?? "",
    email: cliente?.email ?? "",
    whatsapp: cliente?.whatsapp ?? "",
    cep: cliente?.cep ?? "",
    bairro: cliente?.bairro ?? "",
    enderecoCompleto: cliente?.enderecoCompleto ?? "",
    cidade: cliente?.cidade ?? "",
    uf: cliente?.uf ?? "",
    segmento: cliente?.segmento ?? "",
    tagIds: cliente?.tagIds ?? [],
    origem: cliente?.origem ?? "",
    status: cliente?.status ?? "ativo",
    responsavelComercialId: cliente?.responsavelComercialId ?? "",
    clienteReferencial: cliente?.clienteReferencial ?? false,
    contatos: cliente?.contatos ?? [],
    avisarConclusaoPorEmail: cliente?.avisarConclusaoPorEmail ?? true,
    feeMensal: cliente?.feeMensal ?? null,
    horasContratadasMes: cliente?.horasContratadasMes ?? null,
    observacoes: cliente?.observacoes ?? "",
    corIdentificacao: cliente?.corIdentificacao ?? coresIdentificacaoDisponiveis[0].id,
  };
}

export function ClienteFormModal({
  open,
  cliente,
  grupos,
  onClose,
  onSave,
}: {
  open: boolean;
  cliente?: Cliente;
  grupos: GrupoClienteDiretorioItem[];
  onClose: () => void;
  onSave: (draft: ClienteFormDraft, clienteId?: string) => void;
}) {
  const { perfilAtual } = useAppData();
  const [draft, setDraft] = useState<ClienteFormDraft>(() => createInitialDraft(cliente));
  const [activeTab, setActiveTab] = useState("dados");

  const editing = cliente !== undefined;
  const canSave = draft.nome.trim().length > 0;
  const podeVerComercial = podeVerDadosFinanceiros(perfilAtual);
  const documentoLabel = draft.tipoDocumento === "cpf" ? "CPF" : "CNPJ";

  const tabs = [
    { id: "dados", label: "Dados" },
    { id: "endereco", label: "Endereço" },
    { id: "contatos", label: "Contatos" },
    ...(podeVerComercial ? [{ id: "comercial", label: "Comercial" }] : []),
  ];

  // Se a permissão mudar (ex.: troca de usuário simulado) enquanto a aba Comercial está
  // selecionada, cai para Dados em vez de manter uma aba que a pessoa não deveria ver.
  const effectiveTab = activeTab === "comercial" && !podeVerComercial ? "dados" : activeTab;

  function updateDraft(patch: Partial<ClienteFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function handleDocumentoChange(rawValue: string) {
    const tipo = detectDocumentType(rawValue) ?? draft.tipoDocumento;
    updateDraft({ documento: formatDocument(rawValue), tipoDocumento: tipo });
  }

  function handleBuscarDocumento() {
    if (!draft.documento.trim()) return;
    const resultado = mockDocumentoLookup(draft.documento, draft.tipoDocumento);
    updateDraft({ nome: resultado.nome, razaoSocial: resultado.razaoSocial });
  }

  function addContato() {
    updateDraft({ contatos: [...draft.contatos, criarContatoVazio()] });
  }

  function updateContato(contatoId: string, patch: Partial<ClienteContato>) {
    updateDraft({ contatos: draft.contatos.map((contato) => (contato.id === contatoId ? { ...contato, ...patch } : contato)) });
  }

  function removeContato(contatoId: string) {
    updateDraft({ contatos: draft.contatos.filter((contato) => contato.id !== contatoId) });
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-3xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl text-sm font-bold text-white"
            style={{ backgroundColor: resolveCorIdentificacaoHex(draft.corIdentificacao) }}
          >
            {draft.nome.trim().slice(0, 2).toUpperCase() || <User className="h-5 w-5" />}
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${cliente.nome}` : "Novo cliente"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Cadastro local do cliente — dados usados em projetos e demandas.
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
        <Tabs tabs={tabs} activeTab={effectiveTab} onChange={setActiveTab} />
      </div>

      <div className="mt-5 flex flex-col gap-4">
        {effectiveTab === "dados" && (
          <>
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <Input
                  label={documentoLabel}
                  value={draft.documento}
                  onChange={(event) => handleDocumentoChange(event.target.value)}
                  placeholder="00.000.000/0000-00"
                />
              </div>
              <Button type="button" variant="secondary" onClick={handleBuscarDocumento} className="mb-0.5">
                <Search className="h-3.5 w-3.5" />
                Buscar {documentoLabel}
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input label="Nome (como é chamado)" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />
              <Input label="Razão social" value={draft.razaoSocial} onChange={(event) => updateDraft({ razaoSocial: event.target.value })} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input label="E-mail" type="email" value={draft.email} onChange={(event) => updateDraft({ email: event.target.value })} />
              <Input label="WhatsApp" value={draft.whatsapp} onChange={(event) => updateDraft({ whatsapp: event.target.value })} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input label="Segmento/Ramo" value={draft.segmento} onChange={(event) => updateDraft({ segmento: event.target.value })} />
              <Select
                label="Status"
                value={draft.status}
                onChange={(event) => updateDraft({ status: event.target.value as ClienteStatus })}
                options={Object.entries(statusClienteLabels).map(([value, label]) => ({ value, label }))}
              />
            </div>

            <MultiSelect
              label="Grupos de clientes"
              values={draft.tagIds.map((referencia) => resolverGrupoClientePorReferencia(referencia, grupos)?.id ?? referencia)}
              onChange={(values) => updateDraft({ tagIds: values })}
              options={grupos
                .filter(
                  (grupo) =>
                    grupo.status === "ativo" ||
                    draft.tagIds.some((referencia) => resolverGrupoClientePorReferencia(referencia, grupos)?.id === grupo.id),
                )
                .map((grupo) => ({
                  value: grupo.id,
                  label: grupo.status === "arquivado" ? `${grupo.nome} (arquivado)` : grupo.nome,
                }))}
            />

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

        {effectiveTab === "endereco" && (
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

        {effectiveTab === "contatos" && (
          <>
            <div className="flex items-center justify-between rounded-xl border border-zinc-200 bg-zinc-50/70 px-4 py-3 dark:border-zinc-700 dark:bg-zinc-800/60">
              <div className="flex items-start gap-2">
                <Mail className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
                <div>
                  <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Avisar sobre e-mail de conclusão</p>
                  <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                    Ao concluir uma demanda deste cliente, oferece o envio do trabalho finalizado.
                  </p>
                </div>
              </div>
              <Switch
                checked={draft.avisarConclusaoPorEmail}
                onChange={(checked) => updateDraft({ avisarConclusaoPorEmail: checked })}
              />
            </div>

            {draft.contatos.length === 0 ? (
              <p className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/70 px-3 py-4 text-center text-xs text-zinc-400 dark:border-zinc-700 dark:bg-zinc-800/60">
                Nenhum contato cadastrado.
              </p>
            ) : (
              <div className="flex flex-col gap-3">
                {draft.contatos.map((contato) => (
                  <div key={contato.id} className="rounded-xl border border-zinc-200 bg-zinc-50/60 p-3 dark:border-zinc-700 dark:bg-zinc-800/40">
                    <div className="grid gap-3 md:grid-cols-2">
                      <Input label="Nome" value={contato.nome} onChange={(event) => updateContato(contato.id, { nome: event.target.value })} />
                      <Input label="Cargo" value={contato.cargo} onChange={(event) => updateContato(contato.id, { cargo: event.target.value })} />
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <Input
                        label="E-mail"
                        type="email"
                        value={contato.email}
                        onChange={(event) => updateContato(contato.id, { email: event.target.value })}
                      />
                      <Input label="Telefone" value={contato.telefone} onChange={(event) => updateContato(contato.id, { telefone: event.target.value })} />
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      <Switch
                        checked={contato.recebeEntregas}
                        onChange={(checked) => updateContato(contato.id, { recebeEntregas: checked })}
                        label={contato.recebeEntregas ? "Recebe avisos de entrega" : "Não recebe avisos"}
                      />
                      <button
                        type="button"
                        onClick={() => removeContato(contato.id)}
                        className="rounded-full p-1.5 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                        aria-label="Remover contato"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <Button type="button" variant="secondary" onClick={addContato} className="self-start">
              <Plus className="h-3.5 w-3.5" />
              Adicionar contato
            </Button>
          </>
        )}

        {effectiveTab === "comercial" && podeVerComercial && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <Select
                label="Origem (como chegou?)"
                value={draft.origem}
                onChange={(event) => updateDraft({ origem: event.target.value })}
                options={[{ value: "", label: "Não informado" }, ...origensClienteDisponiveis.map((origem) => ({ value: origem, label: origem }))]}
              />
              <Select
                label="Responsável comercial"
                value={draft.responsavelComercialId}
                onChange={(event) => updateDraft({ responsavelComercialId: event.target.value })}
                options={[{ value: "", label: "Selecionar…" }, ...responsaveisProjetoDisponiveis.map((usuario) => ({ value: usuario.id, label: usuario.nome }))]}
              />
            </div>

            <div className="flex items-center justify-between rounded-xl border border-zinc-200 bg-zinc-50/70 px-4 py-3 dark:border-zinc-700 dark:bg-zinc-800/60">
              <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Cliente referencial (case de portfólio)</p>
              <Switch checked={draft.clienteReferencial} onChange={(checked) => updateDraft({ clienteReferencial: checked })} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Fee mensal (R$)"
                type="number"
                value={draft.feeMensal ?? ""}
                onChange={(event) => updateDraft({ feeMensal: event.target.value === "" ? null : Number(event.target.value) })}
              />
              <Input
                label="Horas contratadas/mês"
                type="number"
                value={draft.horasContratadasMes ?? ""}
                onChange={(event) => updateDraft({ horasContratadasMes: event.target.value === "" ? null : Number(event.target.value) })}
              />
            </div>

            <Textarea
              label="Observações"
              rows={3}
              placeholder="Contatos-chave, particularidades, histórico…"
              value={draft.observacoes}
              onChange={(event) => updateDraft({ observacoes: event.target.value })}
            />
          </>
        )}
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSave(draft, cliente?.id)}>
          Salvar alterações
        </Button>
      </div>
    </Modal>
  );
}
