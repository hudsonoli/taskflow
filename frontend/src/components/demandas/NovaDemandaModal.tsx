"use client";

import { useEffect, useState } from "react";
import { ClipboardPlus, GitBranch, X } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Combobox } from "@/components/ui/Combobox";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { Modal } from "@/components/ui/Modal";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { RichTextEditor } from "@/components/ui/RichTextEditor";
import { Select } from "@/components/ui/Select";
import {
  prioridadeDemandaLabels,
  statusDemandaEditaveis,
  statusDemandaLabels,
} from "@/lib/demandas";
import { obterWorkflowModeloReal } from "@/lib/api-backend";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { useDiretorioWorkflowModelos } from "@/lib/diretorioWorkflowModelos";
import { workflowEtapaTipoLabels } from "@/types/workflow-modelo";
import type { WorkflowModelo } from "@/types/workflow-modelo";
import type { Demanda, DemandaFormDraft, DemandaPrioridade, DemandaStatusEditavel } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";

function createInitialDraft(demanda?: Demanda): DemandaFormDraft {
  return {
    nome: demanda?.nome ?? "",
    pit: demanda?.pit ?? "",
    projetoId: demanda?.projetoId ?? "",
    clienteId: demanda?.clienteId ?? "",
    briefing: demanda?.briefing ?? "",
    prioridade: demanda?.prioridade ?? "media",
    status: (demanda?.status ?? "planejada") as DemandaStatusEditavel,
    usuarioResponsavelIds: demanda?.usuarioResponsavelIds ?? [],
    departamentoResponsavelIds: demanda?.departamentoResponsavelIds ?? [],
    dataFimPrevista: demanda?.dataFimPrevista ?? "",
    workflowModeloId: null,
  };
}

export function NovaDemandaModal({
  open,
  demanda,
  onClose,
  onSaveAndClose,
  onSaveAndContinue,
}: {
  open: boolean;
  demanda?: Demanda;
  onClose: () => void;
  onSaveAndClose: (draft: DemandaFormDraft, demandaId?: string) => void;
  onSaveAndContinue: (draft: DemandaFormDraft, demandaId?: string) => void;
}) {
  const { projetos } = useDiretorioProjetos();
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const { usuarios: diretorio } = useDiretorioUsuarios();
  const { workflowModelos } = useDiretorioWorkflowModelos();
  // Picker só oferece usuário ativo pra seleção (referência histórica de inativo continua
  // resolvendo em outros lugares via resolverUsuarioPorReferencia).
  const usuarios = diretorio.filter((usuario) => usuario.status === "ativo");
  const [draft, setDraft] = useState<DemandaFormDraft>(() => createInitialDraft(demanda));
  // Vínculo novo não pode ser um Projeto arquivado (mesma regra do backend, ver
  // `_ensure_projeto_valido`) — mas o Projeto já vinculado à Demanda continua aparecendo,
  // senão o campo mostraria vazio ao editar uma Demanda cujo Projeto foi arquivado depois.
  const projetosSelecionaveis = projetos.filter(
    (projeto) => projeto.status !== "arquivado" || projeto.id === draft.projetoId,
  );
  const [workflowPreview, setWorkflowPreview] = useState<WorkflowModelo | null>(null);
  const previewAtual = draft.workflowModeloId && workflowPreview?.id === draft.workflowModeloId ? workflowPreview : null;
  const carregandoWorkflow = Boolean(draft.workflowModeloId) && previewAtual === null;

  const editing = demanda !== undefined;
  const canSave = draft.nome.trim().length > 0;

  function updateDraft(patch: Partial<DemandaFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function handleProjectChange(projectId: string) {
    const projeto = projetos.find((item) => item.id === projectId);
    updateDraft({ projetoId: projectId, clienteId: projeto?.clienteId ?? draft.clienteId });
  }

  useEffect(() => {
    let cancelado = false;
    const modeloId = draft.workflowModeloId;
    if (!modeloId) {
      return;
    }
    obterWorkflowModeloReal(modeloId)
      .then((modelo) => {
        if (!cancelado) setWorkflowPreview(modelo);
      })
      .catch(() => {
        // mantém previewAtual nulo (derivado por id) até uma tentativa bem-sucedida
      });
    return () => {
      cancelado = true;
    };
  }, [draft.workflowModeloId]);

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-3xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <ClipboardPlus className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? "Editar tarefa" : "Nova tarefa"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Estruture a tarefa: dados principais, briefing, workflow e responsáveis.
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

      {/*
        "Backlog do projeto" (modelo de campanha) saiu na Fase 2E.5A: usava a projeção mock
        (`resolveModeloCampanhaPorProjeto`). `Projeto.modeloCampanha` real só existe em
        `GET /projetos/{id}` (gestor/admin — `require_admin_or_gestor`), e este modal é usado
        por qualquer perfil que possa criar demanda (Atendimento, heads e gestão — ver
        `podeCriarDemanda`), não só gestor/admin. Reintroduzir isto exige decisão de
        autorização/endpoint, não feita nesta rodada — ver relatório da Fase 2E.5A.
      */}

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <Input label="Nome" value={draft.nome} onChange={(event) => updateDraft({ nome: event.target.value })} />
        <Input
          label="PIT (opcional)"
          placeholder="Ex: C3A-0008/26"
          value={draft.pit ?? ""}
          onChange={(event) => updateDraft({ pit: event.target.value })}
        />
        <Combobox
          label="Projeto (opcional)"
          value={draft.projetoId ?? ""}
          onChange={handleProjectChange}
          options={projetosSelecionaveis.map((projeto) => ({
            value: projeto.id,
            label: projeto.status === "arquivado" ? `${projeto.nome} (arquivado)` : projeto.nome,
          }))}
          placeholder="Buscar projeto…"
          emptyLabel="Nenhum projeto encontrado"
        />
        <Combobox
          label="Cliente"
          value={draft.clienteId ?? ""}
          onChange={(clienteId) => updateDraft({ clienteId })}
          options={clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome }))}
          placeholder="Buscar cliente…"
          emptyLabel="Nenhum cliente encontrado"
        />
        <Input
          label="Prazo (data e horário)"
          type="datetime-local"
          value={draft.dataFimPrevista ?? ""}
          onChange={(event) => updateDraft({ dataFimPrevista: event.target.value })}
        />
        <Select
          label="Prioridade"
          value={draft.prioridade}
          onChange={(event) => updateDraft({ prioridade: event.target.value as DemandaPrioridade })}
          options={Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label }))}
        />
        <Select
          label="Status"
          value={draft.status}
          onChange={(event) => updateDraft({ status: event.target.value as DemandaStatusEditavel })}
          // `arquivada` fica fora: arquivar tem rota própria, com motivo obrigatório.
          options={statusDemandaEditaveis.map((value) => ({ value, label: statusDemandaLabels[value] }))}
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <MemberSelector
          label="Usuários responsáveis"
          values={draft.usuarioResponsavelIds}
          onChange={(values) => updateDraft({ usuarioResponsavelIds: values })}
          placeholder="Selecionar responsáveis…"
          options={usuarios.map((usuario) => ({
            id: usuario.id,
            nome: usuario.nome,
            subtitulo: usuario.departamentoId
              ? departamentos.find((departamento) => departamento.id === usuario.departamentoId)?.nome
              : undefined,
            corIdentificacao: usuario.corIdentificacao,
            fotoUrl: usuario.fotoUrl,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          values={draft.departamentoResponsavelIds}
          onChange={(values) => updateDraft({ departamentoResponsavelIds: values })}
          options={departamentos
            .filter((departamento) => departamento.status === "ativo")
            .map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
        />
      </div>

      <div className="mt-4">
        <span className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">Briefing</span>
        <RichTextEditor value={draft.briefing ?? ""} onChange={(html) => updateDraft({ briefing: html })} />
      </div>

      {!editing ? (
        <div className="mt-4">
          <span className="mb-1.5 block text-sm font-medium text-zinc-700 dark:text-zinc-300">
            Workflow (opcional)
          </span>
          <Combobox
            label="Modelo de workflow"
            value={draft.workflowModeloId ?? ""}
            onChange={(workflowModeloId) => updateDraft({ workflowModeloId: workflowModeloId || null })}
            options={workflowModelos.map((modelo) => ({ value: modelo.id, label: modelo.nome }))}
            placeholder="Buscar workflow…"
            emptyLabel="Nenhum workflow ativo encontrado"
          />
          {draft.workflowModeloId && (
            <div className="mt-3 rounded-2xl border border-indigo-100 bg-indigo-50/40 p-3.5 dark:border-indigo-500/20 dark:bg-indigo-500/5">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
                <GitBranch className="h-3.5 w-3.5" />
                Etapas aplicadas ao criar
              </div>
              {carregandoWorkflow ? (
                <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">Carregando etapas…</p>
              ) : (
                <ol className="mt-2 flex flex-col gap-1.5">
                  {previewAtual?.etapas.map((etapa, index) => (
                    <li key={etapa.id} className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-500 text-[10px] font-bold text-white">
                        {index + 1}
                      </span>
                      <span className="truncate">{etapa.nome}</span>
                      <Badge tone={etapa.tipo === "aprovacao" ? "amber" : "blue"}>
                        {workflowEtapaTipoLabels[etapa.tipo]}
                      </Badge>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>
      ) : demanda.workflowEtapas.length > 0 ? (
        <div className="mt-4 rounded-2xl border border-zinc-200 bg-zinc-50/60 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/30">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            <GitBranch className="h-3.5 w-3.5" />
            Workflow aplicado — {demanda.workflowEtapas.length} etapa(s)
          </div>
          <p className="mt-1.5 text-xs text-zinc-500 dark:text-zinc-400">
            Etapas já materializadas na criação. Ver detalhe e progresso na aba Workflow da tarefa.
          </p>
        </div>
      ) : null}

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" variant="secondary" disabled={!canSave} onClick={() => onSaveAndContinue(draft, demanda?.id)}>
          Salvar e continuar
        </Button>
        <Button type="button" disabled={!canSave} onClick={() => onSaveAndClose(draft, demanda?.id)}>
          Salvar e fechar
        </Button>
      </div>
    </Modal>
  );
}
