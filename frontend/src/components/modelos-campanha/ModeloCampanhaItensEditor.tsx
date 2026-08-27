"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MemberSelector, type MemberOption } from "@/components/ui/MemberSelector";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioPecas } from "@/lib/diretorioPecas";
import { useDiretorioTiposTarefa } from "@/lib/diretorioTiposTarefa";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { useDiretorioWorkflowModelos } from "@/lib/diretorioWorkflowModelos";
import { criarItemModeloCampanhaVazio } from "@/lib/modeloCampanhaItens";
import { prioridadePadraoLabels, type ModeloCampanhaItemFormDraft, type PrioridadePadrao } from "@/types/modelo-campanha";

/**
 * Editor de itens de Modelo de Campanha — extraído do `ModeloCampanhaFormModal` (biblioteca,
 * Fase 2G.5B) na Fase 2G.5C3 para ser reutilizado também no snapshot aplicado num Projeto
 * (`ModeloCampanhaSection`). Os dois contextos editam exatamente a mesma forma de item
 * (`ModeloCampanhaItemFormDraft`) e as mesmas 5 referências com o mesmo padrão de
 * preservação histórica — só o container em volta (modal vs. seção de página) e o payload de
 * saída diferem, e ambos ficam fora deste componente.
 */

type TipoResponsavel = "nenhum" | "usuario" | "departamento";

function tipoResponsavelDe(item: ModeloCampanhaItemFormDraft): TipoResponsavel {
  if (item.responsavelUsuarioId) return "usuario";
  if (item.responsavelDepartamentoId) return "departamento";
  return "nenhum";
}

/**
 * Opções de um `<Select>` a partir de um diretório real ativo-only ({id,nome}). O rótulo da
 * opção correspondente ao vínculo atual do item nunca é recalculado a partir do diretório —
 * usa sempre `nomeAtual` (o nome já salvo no próprio item, seja histórico/snapshot ou apenas o
 * último nome resolvido), mesmo quando a entidade continua ativa na lista mas foi renomeada
 * depois do vínculo. Só passa a refletir o diretório quando o próprio usuário troca a seleção
 * (o `onChange` de cada Select busca o nome atual só nesse momento). Se o vínculo atual saiu da
 * lista (arquivado/inativo), a opção é reconstruída como "(indisponível)" e nunca oferecida
 * para um NOVO vínculo — só aparece quando é o valor já selecionado.
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
  const options = itens.map((item) =>
    item.id === valorAtual && nomeAtual ? { value: item.id, label: nomeAtual } : { value: item.id, label: item.nome },
  );
  const atualNaLista = valorAtual ? itens.some((item) => item.id === valorAtual) : true;
  if (valorAtual && !atualNaLista) {
    return [vazio, { value: valorAtual, label: `${nomeAtual ?? "Registro"} (indisponível)` }, ...options];
  }
  return [vazio, ...options];
}

export function ModeloCampanhaItensEditor({
  itens,
  onItensChange,
  somenteLeitura = false,
}: {
  itens: ModeloCampanhaItemFormDraft[];
  onItensChange: (itens: ModeloCampanhaItemFormDraft[]) => void;
  somenteLeitura?: boolean;
}) {
  const { pecas, carregando: carregandoPecas, erro: erroPecas } = useDiretorioPecas();
  const { tiposTarefa, carregando: carregandoTiposTarefa, erro: erroTiposTarefa } = useDiretorioTiposTarefa();
  const { workflowModelos, carregando: carregandoWorkflows, erro: erroWorkflows } = useDiretorioWorkflowModelos();
  const { usuarios, carregando: carregandoUsuarios, erro: erroUsuarios } = useDiretorioUsuarios();
  const { departamentos, carregando: carregandoDepartamentos, erro: erroDepartamentos } = useDiretorioDepartamentos();

  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(() => new Set());
  // Ver docstring equivalente no ModeloCampanhaFormModal original: o tipo de responsável não
  // é um campo do item, é derivado de qual id está preenchido. Este override guarda a
  // intenção explícita do usuário enquanto os dois ids ainda estão vazios — sem ele, escolher
  // "Usuário" antes de escolher a pessoa reverteria sozinho pra "Nenhum" a cada render.
  const [tipoResponsavelOverride, setTipoResponsavelOverride] = useState<Record<string, TipoResponsavel>>({});

  const todasExpandidas = itens.length > 0 && itens.every((item) => expandedKeys.has(item.clientKey));

  const usuariosAtivos = usuarios
    .filter((usuario) => usuario.status === "ativo")
    .map((usuario) => ({ id: usuario.id, nome: usuario.nome, corIdentificacao: usuario.corIdentificacao, fotoUrl: usuario.fotoUrl }));

  // Departamento aceita ativo OU inativo em novo vínculo — só arquivado é recusado (mesma
  // regra do backend, tanto em ModeloCampanhaService quanto em ProjetoModeloCampanhaService).
  const departamentosElegiveis = departamentos
    .filter((departamento) => departamento.status !== "arquivado")
    .map((departamento) => ({ id: departamento.id, nome: departamento.nome }));

  function updateItem(clientKey: string, patch: Partial<ModeloCampanhaItemFormDraft>) {
    onItensChange(itens.map((item) => (item.clientKey === clientKey ? { ...item, ...patch } : item)));
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
    setExpandedKeys(todasExpandidas ? new Set() : new Set(itens.map((item) => item.clientKey)));
  }

  function addItem() {
    const novoItem = criarItemModeloCampanhaVazio();
    onItensChange([...itens, novoItem]);
    setExpandedKeys((current) => new Set(current).add(novoItem.clientKey));
  }

  function removeItem(clientKey: string) {
    onItensChange(itens.filter((item) => item.clientKey !== clientKey));
  }

  function moveItem(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= itens.length) return;
    const proximo = [...itens];
    [proximo[index], proximo[target]] = [proximo[target], proximo[index]];
    onItensChange(proximo);
  }

  function tipoResponsavelEfetivo(item: ModeloCampanhaItemFormDraft): TipoResponsavel {
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
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Itens</p>
        {itens.length > 0 && (
          <button
            type="button"
            onClick={toggleExpandirTudo}
            className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
          >
            {todasExpandidas ? "Recolher tudo" : "Expandir tudo"}
          </button>
        )}
      </div>

      <div className="space-y-3">
        {itens.map((item, index) => {
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
                  {!somenteLeitura && (
                    <>
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
                        disabled={index === itens.length - 1}
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
                    </>
                  )}
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
                    disabled={somenteLeitura}
                    onChange={(event) => updateItem(item.clientKey, { nome: event.target.value })}
                  />

                  <Textarea
                    label="Briefing padrão"
                    rows={3}
                    value={item.briefingPadrao}
                    disabled={somenteLeitura}
                    onChange={(event) => updateItem(item.clientKey, { briefingPadrao: event.target.value })}
                  />

                  <div className="grid gap-3 sm:grid-cols-2">
                    <Select
                      label="Prioridade padrão"
                      value={item.prioridadePadrao}
                      disabled={somenteLeitura}
                      onChange={(event) => updateItem(item.clientKey, { prioridadePadrao: event.target.value as PrioridadePadrao })}
                      options={Object.entries(prioridadePadraoLabels).map(([value, label]) => ({ value, label }))}
                    />
                    <Select
                      label="Peça (opcional)"
                      value={item.pecaId ?? ""}
                      disabled={somenteLeitura || carregandoPecas || Boolean(erroPecas)}
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
                      disabled={somenteLeitura || carregandoTiposTarefa || Boolean(erroTiposTarefa)}
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
                      disabled={somenteLeitura || carregandoWorkflows || Boolean(erroWorkflows)}
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
                      disabled={somenteLeitura}
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
                          disabled={somenteLeitura || carregandoDepartamentos || Boolean(erroDepartamentos)}
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

      {!somenteLeitura && (
        <Button type="button" variant="secondary" onClick={addItem} className="self-center px-4 py-2 text-xs">
          <Plus className="h-3.5 w-3.5" />
          Novo item
        </Button>
      )}
    </div>
  );
}
