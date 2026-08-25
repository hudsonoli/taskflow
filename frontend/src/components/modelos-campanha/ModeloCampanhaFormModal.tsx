"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Layers3, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MemberSelector, type MemberOption } from "@/components/ui/MemberSelector";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { Textarea } from "@/components/ui/Textarea";
import { generateId } from "@/lib/ids";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioPecas } from "@/lib/diretorioPecas";
import { useDiretorioTiposTarefa } from "@/lib/diretorioTiposTarefa";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { useDiretorioWorkflowModelos } from "@/lib/diretorioWorkflowModelos";
import {
  prioridadePadraoLabels,
  type ModeloCampanha,
  type ModeloCampanhaFormDraft,
  type ModeloCampanhaItem,
  type ModeloCampanhaItemFormDraft,
  type PrioridadePadrao,
} from "@/types/modelo-campanha";

type TipoResponsavel = "nenhum" | "usuario" | "departamento";

function tipoResponsavelDe(item: ModeloCampanhaItemFormDraft): TipoResponsavel {
  if (item.responsavelUsuarioId) return "usuario";
  if (item.responsavelDepartamentoId) return "departamento";
  return "nenhum";
}

/**
 * Opções de um `<Select>` a partir de um diretório real ativo-only ({id,nome}). Sem
 * resolução histórica no backend: se o valor atual do item saiu da lista (arquivado/inativo
 * desde que foi vinculado), a opção é reconstruída a partir do nome já salvo no próprio item
 * (`*Nome`, resolvido pelo backend) — nunca oferecida para NOVO vínculo (só aparece quando é
 * o valor já selecionado), nunca sobrescreve o id/nome guardados. Mesmo padrão de
 * `opcoesComFallbackHistorico` em ProjetoFormSections.tsx (Fase 2E), adaptado com uma opção
 * "vazio" pois aqui a referência é sempre opcional.
 */
function opcoesComFallbackHistorico(
  valorAtual: string | null,
  nomeAtual: string | null,
  itens: { id: string; nome: string }[],
  carregando: boolean,
  erro: string | null,
  rotuloRecurso: string,
  rotuloVazio: string,
): { value: string; label: string }[] {
  const vazio = { value: "", label: rotuloVazio };
  if (carregando) {
    return valorAtual ? [{ value: valorAtual, label: `${nomeAtual ?? rotuloRecurso} (carregando…)` }] : [vazio];
  }
  if (erro) {
    return valorAtual
      ? [{ value: valorAtual, label: `${nomeAtual ?? rotuloRecurso} (falha ao carregar ${rotuloRecurso})` }]
      : [{ value: "", label: `Falha ao carregar ${rotuloRecurso}` }];
  }
  const options = itens.map((item) => ({ value: item.id, label: item.nome }));
  const atualNaLista = valorAtual ? itens.some((item) => item.id === valorAtual) : true;
  if (valorAtual && !atualNaLista) {
    return [vazio, { value: valorAtual, label: `${nomeAtual ?? "Registro"} (indisponível)` }, ...options];
  }
  return [vazio, ...options];
}

function createItem(): ModeloCampanhaItemFormDraft {
  return {
    clientKey: generateId("item-modelo-campanha"),
    nome: "Novo item",
    briefingPadrao: "",
    prioridadePadrao: "media",
    pecaId: null,
    pecaNome: null,
    tipoTarefaId: null,
    tipoTarefaNome: null,
    workflowModeloId: null,
    workflowModeloNome: null,
    responsavelUsuarioId: null,
    responsavelUsuarioNome: null,
    responsavelDepartamentoId: null,
    responsavelDepartamentoNome: null,
  };
}

function itemParaDraft(item: ModeloCampanhaItem): ModeloCampanhaItemFormDraft {
  return {
    id: item.id,
    // O id do servidor já é uma chave única e estável — reaproveitado como clientKey, sem
    // gerar outro identificador para o mesmo item.
    clientKey: item.id,
    nome: item.nome,
    briefingPadrao: item.briefingPadrao ?? "",
    prioridadePadrao: item.prioridadePadrao,
    pecaId: item.pecaId,
    pecaNome: item.pecaNome,
    tipoTarefaId: item.tipoTarefaId,
    tipoTarefaNome: item.tipoTarefaNome,
    workflowModeloId: item.workflowModeloId,
    workflowModeloNome: item.workflowModeloNome,
    responsavelUsuarioId: item.responsavelUsuarioId,
    responsavelUsuarioNome: item.responsavelUsuarioNome,
    responsavelDepartamentoId: item.responsavelDepartamentoId,
    responsavelDepartamentoNome: item.responsavelDepartamentoNome,
  };
}

function createInitialDraft(modelo?: ModeloCampanha): ModeloCampanhaFormDraft {
  return {
    nome: modelo?.nome ?? "",
    descricao: modelo?.descricao ?? "",
    status: modelo?.status === "inativo" ? "inativo" : "ativo",
    itens: modelo ? modelo.itens.map(itemParaDraft) : [createItem()],
  };
}

export function ModeloCampanhaFormModal({
  open,
  modelo,
  onClose,
  onSave,
  salvando,
  erro,
}: {
  open: boolean;
  modelo?: ModeloCampanha;
  onClose: () => void;
  onSave: (draft: ModeloCampanhaFormDraft, modeloId?: string) => void;
  salvando?: boolean;
  erro?: string | null;
}) {
  const { pecas, carregando: carregandoPecas, erro: erroPecas } = useDiretorioPecas();
  const { tiposTarefa, carregando: carregandoTiposTarefa, erro: erroTiposTarefa } = useDiretorioTiposTarefa();
  const { workflowModelos, carregando: carregandoWorkflows, erro: erroWorkflows } = useDiretorioWorkflowModelos();
  const { usuarios, carregando: carregandoUsuarios, erro: erroUsuarios } = useDiretorioUsuarios();
  const { departamentos, carregando: carregandoDepartamentos, erro: erroDepartamentos } = useDiretorioDepartamentos();

  const [draft, setDraft] = useState<ModeloCampanhaFormDraft>(() => createInitialDraft(modelo));
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => new Set());
  // O tipo de responsável (Nenhum/Usuário/Departamento) por si só não é um campo do item —
  // é derivado de qual id está preenchido (`tipoResponsavelDe`). Isso quebraria a escolha de
  // "Usuário" ANTES de escolher a pessoa: com os dois ids ainda nulos, o valor derivado
  // continuaria "nenhum" e o <Select> voltaria sozinho pra opção anterior a cada render. Este
  // estado guarda a intenção explícita do usuário por item, e SÓ é usado quando os dois ids
  // estão vazios (nenhuma referência real ainda escolhida) — no momento em que um id é
  // escolhido, `tipoResponsavelDe` volta a mandar, então o override nunca diverge do dado real.
  const [tipoResponsavelOverride, setTipoResponsavelOverride] = useState<Record<string, TipoResponsavel>>({});

  const editing = modelo !== undefined;
  const todosItensValidos = draft.itens.every((item) => item.nome.trim().length > 0);
  const canSave = draft.nome.trim().length > 0 && todosItensValidos && !salvando;
  const todasExpandidas = draft.itens.length > 0 && draft.itens.every((item) => expandedKeys.has(item.clientKey));

  const usuariosAtivos = usuarios
    .filter((usuario) => usuario.status === "ativo")
    .map((usuario) => ({ id: usuario.id, nome: usuario.nome, corIdentificacao: usuario.corIdentificacao, fotoUrl: usuario.fotoUrl }));

  // Departamento aceita ativo OU inativo em novo vínculo — só arquivado é recusado (ver
  // ModeloCampanhaService._validar_campo_referencia no backend, lambda do Departamento).
  const departamentosElegiveis = departamentos
    .filter((departamento) => departamento.status !== "arquivado")
    .map((departamento) => ({ id: departamento.id, nome: departamento.nome }));

  function updateDraft(patch: Partial<ModeloCampanhaFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function updateItem(clientKey: string, patch: Partial<ModeloCampanhaItemFormDraft>) {
    updateDraft({
      itens: draft.itens.map((item) => (item.clientKey === clientKey ? { ...item, ...patch } : item)),
    });
  }

  function toggleExpanded(clientKey: string) {
    setExpandedKeys((current) => {
      const next = new Set(current);
      if (next.has(clientKey)) next.delete(clientKey);
      else next.add(clientKey);
      return next;
    });
  }

  function toggleExpandirTudo() {
    setExpandedKeys(todasExpandidas ? new Set() : new Set(draft.itens.map((item) => item.clientKey)));
  }

  function addItem() {
    const novoItem = createItem();
    updateDraft({ itens: [...draft.itens, novoItem] });
    setExpandedKeys((current) => new Set(current).add(novoItem.clientKey));
  }

  function removeItem(clientKey: string) {
    updateDraft({ itens: draft.itens.filter((item) => item.clientKey !== clientKey) });
  }

  function moveItem(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= draft.itens.length) return;
    const proximo = [...draft.itens];
    [proximo[index], proximo[target]] = [proximo[target], proximo[index]];
    updateDraft({ itens: proximo });
  }

  function tipoResponsavelEfetivo(item: ModeloCampanhaItemFormDraft): TipoResponsavel {
    // Enquanto nenhum dos dois ids está preenchido, o dado real é ambíguo ("nenhum" e
    // "escolhi Usuário mas ainda não selecionei quem" são indistinguíveis nos dados) — o
    // override decide. Assim que um id é escolhido, ele volta a ser a única fonte de verdade.
    const derivado = tipoResponsavelDe(item);
    return derivado !== "nenhum" ? derivado : (tipoResponsavelOverride[item.clientKey] ?? "nenhum");
  }

  function setTipoResponsavel(clientKey: string, tipo: TipoResponsavel) {
    setTipoResponsavelOverride((current) => ({ ...current, [clientKey]: tipo }));
    if (tipo === "nenhum") {
      updateItem(clientKey, {
        responsavelUsuarioId: null,
        responsavelUsuarioNome: null,
        responsavelDepartamentoId: null,
        responsavelDepartamentoNome: null,
      });
    } else if (tipo === "usuario") {
      updateItem(clientKey, { responsavelDepartamentoId: null, responsavelDepartamentoNome: null });
    } else {
      updateItem(clientKey, { responsavelUsuarioId: null, responsavelUsuarioNome: null });
    }
  }

  function usuarioOptionsPara(item: ModeloCampanhaItemFormDraft): MemberOption[] {
    const atualNaLista = item.responsavelUsuarioId
      ? usuariosAtivos.some((option) => option.id === item.responsavelUsuarioId)
      : true;
    if (item.responsavelUsuarioId && !atualNaLista) {
      return [
        { id: item.responsavelUsuarioId, nome: `${item.responsavelUsuarioNome ?? "Usuário"} (indisponível)` },
        ...usuariosAtivos,
      ];
    }
    return usuariosAtivos;
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-2xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Layers3 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${modelo.nome}` : "Novo modelo de campanha"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Estrutura reutilizável de itens sugeridos para campanhas recorrentes.
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
        <Input label="Nome do modelo" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />

        <Textarea
          label="Descrição"
          rows={2}
          value={draft.descricao}
          onChange={(event) => updateDraft({ descricao: event.target.value })}
        />

        <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
          <Switch
            checked={draft.status === "ativo"}
            onChange={(checked) => updateDraft({ status: checked ? "ativo" : "inativo" })}
            label={draft.status === "ativo" ? "Ativo" : "Inativo"}
            description="Modelos inativos continuam preservados, mas ficam fora do uso corrente."
          />
        </div>

        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Itens do modelo</p>
          <button
            type="button"
            onClick={toggleExpandirTudo}
            className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {todasExpandidas ? "Recolher tudo" : "Expandir tudo"}
          </button>
        </div>

        {erro && (
          <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
            {erro}
          </p>
        )}

        <div className="space-y-3">
          {draft.itens.map((item, index) => {
            const expanded = expandedKeys.has(item.clientKey);
            const tipoResponsavel = tipoResponsavelEfetivo(item);

            return (
              <div key={item.clientKey} className="overflow-hidden rounded-2xl border border-indigo-200 dark:border-indigo-500/30">
                <div className="flex items-center gap-3 bg-indigo-50 px-3.5 py-2.5 dark:bg-indigo-500/10">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-500 text-[11px] font-bold text-white">
                    {index + 1}
                  </span>
                  <button
                    type="button"
                    onClick={() => toggleExpanded(item.clientKey)}
                    className="flex min-w-0 flex-1 items-center gap-2 text-left"
                  >
                    <span className="truncate text-sm font-semibold text-zinc-900 dark:text-zinc-100">{item.nome || "Novo item"}</span>
                    <span className="shrink-0 text-xs text-zinc-500 dark:text-zinc-400">
                      {prioridadePadraoLabels[item.prioridadePadrao]}
                    </span>
                  </button>

                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => moveItem(index, -1)}
                      disabled={index === 0}
                      aria-label="Mover para cima"
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 disabled:opacity-30 dark:hover:bg-zinc-900/40"
                    >
                      <ChevronUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => moveItem(index, 1)}
                      disabled={index === draft.itens.length - 1}
                      aria-label="Mover para baixo"
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 disabled:opacity-30 dark:hover:bg-zinc-900/40"
                    >
                      <ChevronDown className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => removeItem(item.clientKey)}
                      aria-label="Remover item"
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 hover:text-red-600 dark:hover:bg-zinc-900/40"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleExpanded(item.clientKey)}
                      aria-label={expanded ? "Recolher item" : "Expandir item"}
                      className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-white/70 dark:hover:bg-zinc-900/40"
                    >
                      <ChevronDown className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`} />
                    </button>
                  </div>
                </div>

                {expanded && (
                  <div className="flex flex-col gap-3 bg-white p-3.5 dark:bg-zinc-900">
                    <Input
                      label="Nome do item"
                      value={item.nome}
                      onChange={(event) => updateItem(item.clientKey, { nome: event.target.value })}
                    />

                    <Textarea
                      label="Briefing padrão"
                      rows={3}
                      value={item.briefingPadrao}
                      onChange={(event) => updateItem(item.clientKey, { briefingPadrao: event.target.value })}
                    />

                    <div className="grid gap-3 sm:grid-cols-2">
                      <Select
                        label="Prioridade padrão"
                        value={item.prioridadePadrao}
                        onChange={(event) => updateItem(item.clientKey, { prioridadePadrao: event.target.value as PrioridadePadrao })}
                        options={Object.entries(prioridadePadraoLabels).map(([value, label]) => ({ value, label }))}
                      />
                      <Select
                        label="Peça (opcional)"
                        value={item.pecaId ?? ""}
                        disabled={carregandoPecas || Boolean(erroPecas)}
                        onChange={(event) => {
                          const value = event.target.value || null;
                          const selecionada = pecas.find((peca) => peca.id === value);
                          updateItem(item.clientKey, { pecaId: value, pecaNome: value ? (selecionada?.nome ?? item.pecaNome) : null });
                        }}
                        options={opcoesComFallbackHistorico(item.pecaId, item.pecaNome, pecas, carregandoPecas, erroPecas, "peças", "Sem peça")}
                      />
                    </div>

                    <div className="grid gap-3 sm:grid-cols-2">
                      <Select
                        label="Tipo de tarefa (opcional)"
                        value={item.tipoTarefaId ?? ""}
                        disabled={carregandoTiposTarefa || Boolean(erroTiposTarefa)}
                        onChange={(event) => {
                          const value = event.target.value || null;
                          const selecionado = tiposTarefa.find((tipo) => tipo.id === value);
                          updateItem(item.clientKey, {
                            tipoTarefaId: value,
                            tipoTarefaNome: value ? (selecionado?.nome ?? item.tipoTarefaNome) : null,
                          });
                        }}
                        options={opcoesComFallbackHistorico(
                          item.tipoTarefaId,
                          item.tipoTarefaNome,
                          tiposTarefa,
                          carregandoTiposTarefa,
                          erroTiposTarefa,
                          "tipos de tarefa",
                          "Sem tipo de tarefa",
                        )}
                      />
                      <Select
                        label="Workflow (opcional)"
                        value={item.workflowModeloId ?? ""}
                        disabled={carregandoWorkflows || Boolean(erroWorkflows)}
                        onChange={(event) => {
                          const value = event.target.value || null;
                          const selecionado = workflowModelos.find((workflow) => workflow.id === value);
                          updateItem(item.clientKey, {
                            workflowModeloId: value,
                            workflowModeloNome: value ? (selecionado?.nome ?? item.workflowModeloNome) : null,
                          });
                        }}
                        options={opcoesComFallbackHistorico(
                          item.workflowModeloId,
                          item.workflowModeloNome,
                          workflowModelos,
                          carregandoWorkflows,
                          erroWorkflows,
                          "workflows",
                          "Sem workflow",
                        )}
                      />
                    </div>

                    <div className="rounded-xl border border-dashed border-zinc-200 p-3 dark:border-zinc-700">
                      <Select
                        label="Tipo de responsável sugerido"
                        value={tipoResponsavel}
                        onChange={(event) => setTipoResponsavel(item.clientKey, event.target.value as TipoResponsavel)}
                        options={[
                          { value: "nenhum", label: "Nenhum" },
                          { value: "usuario", label: "Usuário" },
                          { value: "departamento", label: "Departamento" },
                        ]}
                      />

                      {tipoResponsavel === "usuario" && (
                        <div className="mt-3">
                          <MemberSelector
                            label="Usuário responsável sugerido"
                            multiple={false}
                            values={item.responsavelUsuarioId ? [item.responsavelUsuarioId] : []}
                            onChange={(values) => {
                              const id = values[0] ?? null;
                              const selecionado = usuariosAtivos.find((usuario) => usuario.id === id);
                              updateItem(item.clientKey, {
                                responsavelUsuarioId: id,
                                responsavelUsuarioNome: id ? (selecionado?.nome ?? item.responsavelUsuarioNome) : null,
                              });
                            }}
                            placeholder={carregandoUsuarios ? "Carregando…" : "Selecionar usuário…"}
                            options={usuarioOptionsPara(item)}
                          />
                          {erroUsuarios && (
                            <p className="mt-1 text-xs text-red-500 dark:text-red-400">Não foi possível carregar os usuários.</p>
                          )}
                        </div>
                      )}

                      {tipoResponsavel === "departamento" && (
                        <div className="mt-3">
                          <Select
                            label="Departamento responsável sugerido"
                            value={item.responsavelDepartamentoId ?? ""}
                            disabled={carregandoDepartamentos || Boolean(erroDepartamentos)}
                            onChange={(event) => {
                              const value = event.target.value || null;
                              const selecionado = departamentosElegiveis.find((departamento) => departamento.id === value);
                              updateItem(item.clientKey, {
                                responsavelDepartamentoId: value,
                                responsavelDepartamentoNome: value ? (selecionado?.nome ?? item.responsavelDepartamentoNome) : null,
                              });
                            }}
                            options={opcoesComFallbackHistorico(
                              item.responsavelDepartamentoId,
                              item.responsavelDepartamentoNome,
                              departamentosElegiveis,
                              carregandoDepartamentos,
                              erroDepartamentos,
                              "departamentos",
                              "Sem departamento",
                            )}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <Button type="button" variant="secondary" onClick={addItem} className="self-center px-4 py-2 text-xs">
          <Plus className="h-3.5 w-3.5" />
          Novo item do modelo
        </Button>
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose} disabled={salvando}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSave(draft, modelo?.id)}>
          {salvando ? "Salvando…" : "Salvar"}
        </Button>
      </div>
    </Modal>
  );
}
