"use client";

import { useState } from "react";
import { ClipboardPlus, Sparkles, X } from "lucide-react";
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
  departamentosProjetoDisponiveis,
  normalizarUsuarioId,
  prioridadeDemandaLabels,
  resolveModeloCampanhaPorProjeto,
  statusDemandaEditaveis,
  statusDemandaLabels,
} from "@/lib/demandas";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { normalizarReferenciasParaCodigoInterno } from "@/lib/referencias";
import { resolverDepartamentoNome } from "@/lib/referencias";
import type { Demanda, DemandaFormDraft, DemandaPrioridade, DemandaStatusEditavel } from "@/types/demanda";
import { RecursoIndisponivel } from "./RecursoIndisponivel";
import { useDiretorioClientes } from "@/lib/diretorioClientes";

// `createInitialWorkflow` saiu na Fase 2E.1: montava uma etapa inicial para um campo que não
// tem tabela. Volta em 2E.2, junto do editor de etapas.

function createInitialDraft(demanda?: Demanda): DemandaFormDraft {
  const projectId = demanda?.projetoId ?? "";

  return {
    nome: demanda?.nome ?? "",
    pit: demanda?.pit ?? "",
    projetoId: projectId,
    clienteId: demanda?.clienteId ?? "",
    briefing: demanda?.briefing ?? "",
    prioridade: demanda?.prioridade ?? "media",
    status: (demanda?.status ?? "planejada") as DemandaStatusEditavel,
    usuarioResponsavelIds: demanda?.usuarioResponsavelIds ?? [],
    departamentoResponsavelIds: demanda?.departamentoResponsavelIds ?? [departamentosProjetoDisponiveis[0].id],
    dataFimPrevista: demanda?.dataFimPrevista ?? "",
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
  const { projetos } = useAppData();
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const diretorio = useDiretorioUsuarios().usuarios;
  // Picker só oferece usuário ativo pra seleção (referência histórica de inativo continua
  // resolvendo em outros lugares via resolverUsuarioPorReferencia).
  const usuarios = diretorio.filter((usuario) => usuario.status === "ativo");
  const [draft, setDraft] = useState<DemandaFormDraft>(() => createInitialDraft(demanda));
  const [briefingRevision, setBriefingRevision] = useState(0);

  const editing = demanda !== undefined;
  const canSave = draft.nome.trim().length > 0;
  const modeloCampanha = resolveModeloCampanhaPorProjeto(draft.projetoId);

  function updateDraft(patch: Partial<DemandaFormDraft>) {
    setDraft((current) => ({ ...current, ...patch }));
  }

  function handleProjectChange(projectId: string) {
    const projeto = projetos.find((item) => item.id === projectId);
    updateDraft({ projetoId: projectId, clienteId: projeto?.clienteId ?? draft.clienteId });
  }

  function usarModeloCampanha(itemId: string) {
    const item = modeloCampanha.find((modelo) => modelo.id === itemId);
    if (!item) return;
    updateDraft({
      nome: item.nomeDemanda,
      briefing: item.briefingBase,
      prioridade: item.prioridadePadrao,
      departamentoResponsavelIds: [item.responsavelOuSetorSugeridoId],
    });
    setBriefingRevision((revision) => revision + 1);
  }

  // `aplicarModelo` saiu na Fase 2E.1 junto do editor de etapas: aplicar um modelo de
  // workflow só faz sentido se houver onde gravar as etapas resultantes.

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
              Cadastro local para estruturar tarefas, briefing, workflow e responsáveis.
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

      {!editing && modeloCampanha.length > 0 && (
        <div className="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-4 dark:border-indigo-500/20 dark:bg-indigo-500/5">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-500" />
            <p className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Backlog do projeto</p>
          </div>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
            Este projeto tem demandas padrão no modelo de campanha — use uma para já sair com nome, briefing e prioridade preenchidos.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {modeloCampanha.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => usarModeloCampanha(item.id)}
                className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-white px-3 py-1.5 text-xs font-medium text-indigo-700 transition hover:bg-indigo-100 dark:border-indigo-500/30 dark:bg-zinc-900 dark:text-indigo-300 dark:hover:bg-indigo-500/10"
              >
                {item.nomeDemanda}
                <Badge tone="blue">{item.tipoTarefaNome}</Badge>
              </button>
            ))}
          </div>
        </div>
      )}

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
          options={projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome }))}
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
          values={normalizarReferenciasParaCodigoInterno(draft.usuarioResponsavelIds.map(normalizarUsuarioId), diretorio)}
          onChange={(values) => updateDraft({ usuarioResponsavelIds: values })}
          placeholder="Selecionar responsáveis…"
          options={usuarios.map((usuario) => ({
            // Enquanto Demanda continuar mock, o valor gravado é o codigoInterno (não o
            // UUID real) — ver lib/referencias.ts / docs/padrao-arquivamento.md.
            id: usuario.codigoInterno,
            nome: usuario.nome,
            subtitulo: resolverDepartamentoNome(usuario.departamentoId ?? "", departamentos),
            corIdentificacao: usuario.corIdentificacao,
            fotoUrl: usuario.fotoUrl,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          values={draft.departamentoResponsavelIds}
          onChange={(values) => updateDraft({ departamentoResponsavelIds: values })}
          options={departamentosProjetoDisponiveis.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
        />
      </div>

      <div className="mt-4">
        <span className="mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300">Briefing</span>
        <RichTextEditor key={briefingRevision} value={draft.briefing ?? ""} onChange={(html) => updateDraft({ briefing: html })} />
      </div>

      {/* O editor de etapas e o seletor de modelo de workflow não são renderizados nesta
          fase: não há tabela para gravá-las, e um formulário que aceita e descarta é pior
          que um que não existe. Ver RecursoIndisponivel. */}
      <div className="mt-4">
        <RecursoIndisponivel recurso="Etapas de workflow" fase="Fase 2E.2" />
      </div>

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
