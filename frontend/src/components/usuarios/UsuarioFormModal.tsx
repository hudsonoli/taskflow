"use client";

import { useState } from "react";
import { Calculator, Plus, Trash2, User, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { Tabs } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";
import { generateId } from "@/lib/ids";
import { formatCPF } from "@/lib/mascaras";
import { coresIdentificacaoDisponiveis, resolveCorIdentificacaoHex } from "@/lib/cores";
import { PERFIL_PARA_PERFIL_BASE } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import {
  perfilUsuarioLabels,
  podeVerDadosFinanceiros,
  type PerfilUsuario,
  type Usuario,
  type UsuarioContato,
  type UsuarioFormDraft,
} from "@/types/usuario";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";

const ufsDisponiveis = [
  "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
  "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
];

function criarContatoVazio(): UsuarioContato {
  return { id: generateId("contato-usuario"), nome: "", email: "", telefone: "", relacao: "" };
}

function formatBRL(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function createInitialDraft(usuario?: Usuario): UsuarioFormDraft {
  return {
    nome: usuario?.nome ?? "",
    email: usuario?.email ?? "",
    telefone: usuario?.telefone ?? "",
    cpf: usuario?.cpf ?? "",
    dataNascimento: usuario?.dataNascimento ?? "",
    cep: usuario?.cep ?? "",
    bairro: usuario?.bairro ?? "",
    enderecoCompleto: usuario?.enderecoCompleto ?? "",
    cidade: usuario?.cidade ?? "",
    uf: usuario?.uf ?? "",
    contatos: usuario?.contatos ?? [],
    departamentoId: usuario?.departamentoId ?? "",
    perfil: usuario?.perfil ?? "operador",
    liderDepartamento: usuario?.liderDepartamento ?? false,
    valorRecebidoMensal: usuario?.valorRecebidoMensal ?? null,
    horasTrabalhoAproximadas: usuario?.horasTrabalhoAproximadas ?? null,
    ativo: usuario?.ativo ?? true,
    observacoes: usuario?.observacoes ?? "",
    corIdentificacao: usuario?.corIdentificacao ?? coresIdentificacaoDisponiveis[0].id,
  };
}

export function UsuarioFormModal({
  open,
  usuario,
  departamentos,
  salvando = false,
  onClose,
  onSave,
}: {
  open: boolean;
  usuario?: Usuario;
  departamentos: DepartamentoDiretorioItem[];
  salvando?: boolean;
  onClose: () => void;
  onSave: (draft: UsuarioFormDraft, usuarioId?: string) => void;
}) {
  const { perfilAtual } = useAppData();
  const [draft, setDraft] = useState<UsuarioFormDraft>(() => createInitialDraft(usuario));
  const [activeTab, setActiveTab] = useState("dados");

  const editing = usuario !== undefined;
  const canSave = draft.nome.trim().length > 0 && draft.email.trim().length > 0;
  const podeVerFinanceiro = podeVerDadosFinanceiros(perfilAtual);

  const tabs = [
    { id: "dados", label: "Dados" },
    { id: "endereco", label: "Endereço" },
    { id: "contatos", label: "Contatos" },
    ...(podeVerFinanceiro ? [{ id: "financeiro", label: "Financeiro" }] : []),
  ];

  // Se a permissão mudar (ex.: troca de usuário simulado) enquanto a aba Financeiro está
  // selecionada, cai para Dados em vez de manter uma aba que a pessoa não deveria ver.
  const effectiveTab = activeTab === "financeiro" && !podeVerFinanceiro ? "dados" : activeTab;

  function updateDraft(patch: Partial<UsuarioFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function addContato() {
    updateDraft({ contatos: [...draft.contatos, criarContatoVazio()] });
  }

  function updateContato(contatoId: string, patch: Partial<UsuarioContato>) {
    updateDraft({ contatos: draft.contatos.map((contato) => (contato.id === contatoId ? { ...contato, ...patch } : contato)) });
  }

  function removeContato(contatoId: string) {
    updateDraft({ contatos: draft.contatos.filter((contato) => contato.id !== contatoId) });
  }

  const valorPorHora =
    draft.valorRecebidoMensal && draft.horasTrabalhoAproximadas
      ? draft.valorRecebidoMensal / draft.horasTrabalhoAproximadas
      : null;

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-2xl">
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
              {editing ? `Editando: ${usuario.nome}` : "Nova pessoa na equipe"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Cadastro real — login com e-mail e senha própria, gravado no banco.
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
            <Input label="Nome" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

            <div className="grid gap-4 md:grid-cols-2">
              <Input label="E-mail" type="email" value={draft.email} onChange={(event) => updateDraft({ email: event.target.value })} placeholder="pessoa@agencia.com.br" />
              <Input label="Telefone" value={draft.telefone} onChange={(event) => updateDraft({ telefone: event.target.value })} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="CPF"
                value={draft.cpf}
                onChange={(event) => updateDraft({ cpf: formatCPF(event.target.value) })}
                placeholder="000.000.000-00"
              />
              <Input
                label="Data de nascimento"
                type="date"
                value={draft.dataNascimento}
                onChange={(event) => updateDraft({ dataNascimento: event.target.value })}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Select
                label="Departamento"
                value={draft.departamentoId}
                onChange={(event) => updateDraft({ departamentoId: event.target.value })}
                options={[{ value: "", label: "Sem departamento" }, ...departamentos.map((departamento) => ({ value: departamento.id, label: departamento.nome }))]}
              />
              <div>
                <Select
                  label="Perfil"
                  value={draft.perfil}
                  onChange={(event) => updateDraft({ perfil: event.target.value as PerfilUsuario })}
                  options={Object.entries(perfilUsuarioLabels).map(([value, label]) => ({ value, label }))}
                />
                {PERFIL_PARA_PERFIL_BASE[draft.perfil] !== draft.perfil && (
                  <p className="mt-1.5 text-xs text-amber-600 dark:text-amber-400">
                    Nesta fase, o backend só tem 3 níveis reais — este perfil é gravado como{" "}
                    <strong>{perfilUsuarioLabels[PERFIL_PARA_PERFIL_BASE[draft.perfil]]}</strong>.
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-2.5">
              <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
                <Switch
                  checked={draft.ativo}
                  onChange={(checked) => updateDraft({ ativo: checked })}
                  label={draft.ativo ? "Ativo" : "Inativo"}
                  description={draft.ativo ? "Pode acessar o sistema" : "Acesso bloqueado"}
                />
              </div>

              <div
                className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900"
                title="Líderes/gerentes de departamento podem cadastrar novas demandas, independentemente do perfil."
              >
                <Switch
                  checked={draft.liderDepartamento}
                  onChange={(checked) => updateDraft({ liderDepartamento: checked })}
                  label="Líder/gerente do departamento"
                  description={draft.liderDepartamento ? "É head do departamento" : "Não é líder do departamento"}
                />
              </div>
            </div>

            <Textarea
              label="Observações"
              rows={3}
              value={draft.observacoes}
              onChange={(event) => updateDraft({ observacoes: event.target.value })}
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
                      <Input
                        label="Relação/Cargo"
                        value={contato.relacao}
                        onChange={(event) => updateContato(contato.id, { relacao: event.target.value })}
                        placeholder="ex.: Contato de emergência, Assistente"
                      />
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
                    <div className="mt-3 flex justify-end">
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

        {effectiveTab === "financeiro" && podeVerFinanceiro && (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Valor recebido (mês, R$)"
                type="number"
                value={draft.valorRecebidoMensal ?? ""}
                onChange={(event) => updateDraft({ valorRecebidoMensal: event.target.value === "" ? null : Number(event.target.value) })}
              />
              <Input
                label="Horas de trabalho aproximadas (mês)"
                type="number"
                value={draft.horasTrabalhoAproximadas ?? ""}
                onChange={(event) => updateDraft({ horasTrabalhoAproximadas: event.target.value === "" ? null : Number(event.target.value) })}
              />
            </div>

            <div className="rounded-xl border border-zinc-200 bg-zinc-50/70 p-4 dark:border-zinc-700 dark:bg-zinc-800/60">
              <div className="flex items-start gap-2">
                <Calculator className="mt-0.5 h-4 w-4 shrink-0 text-zinc-400" />
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Cruzamento recebimento x hora</p>
                  <p className="mt-1 text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                    {valorPorHora !== null ? `${formatBRL(valorPorHora)}/h` : "—"}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                    Calculado a partir do valor recebido dividido pelas horas de trabalho aproximadas.
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose} disabled={salvando}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave || salvando} onClick={() => onSave(draft, usuario?.id)}>
          {salvando ? "Salvando…" : "Salvar alterações"}
        </Button>
      </div>
    </Modal>
  );
}
