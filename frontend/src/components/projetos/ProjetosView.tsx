"use client";

import { useMemo, useState } from "react";
import { FolderKanban } from "lucide-react";
import { StatusPill } from "@/components/ui/StatusPill";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspacePage } from "@/components/workspace/WorkspacePage";
import {
  AGENCIA_PADRAO_ID,
  EMPRESA_PADRAO_ID,
  generateCodigoInterno,
  generateId,
  projetosMock,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
} from "@/lib/projetos-mock";
import type { Projeto, ProjetoFormDraft } from "@/types/projeto";
import { NovoProjetoModal } from "./NovoProjetoModal";
import { ProjetoDetailsDrawer } from "./ProjetoDetailsDrawer";
import { ProjetosStats } from "./ProjetosStats";
import { ProjetosTable } from "./ProjetosTable";
import {
  ProjetoStatusFiltro,
  ProjetosToolbar,
} from "./ProjetosToolbar";

function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function matchesProjeto(projeto: Projeto, query: string) {
  const haystack = [
    projeto.nome,
    resolveClienteProjetoNome(projeto.clienteId),
    projeto.campanha,
    resolveResponsaveisProjetoNomes(projeto.responsavelIds),
    resolveDepartamentosProjetoNomes(projeto.departamentoResponsavelIds),
    projeto.codigoInterno,
  ].join(" ");

  return normalize(haystack).includes(normalize(query));
}

function createHistoricoProjeto(acao: string) {
  return {
    id: generateId("hist-projeto"),
    usuarioId: "user-1",
    usuario: "Hudson Cunha",
    acao,
    dataHora: new Date().toLocaleString("pt-BR"),
    ip: "127.0.0.1",
    dispositivo: "Workspace mock",
  };
}

function createProjetoFromDraft(draft: ProjetoFormDraft): Projeto {
  const now = new Date().toISOString();

  return {
    id: generateId("projeto"),
    empresaId: EMPRESA_PADRAO_ID,
    agenciaId: AGENCIA_PADRAO_ID,
    clienteId: draft.clienteId,
    codigoInterno: generateCodigoInterno(),
    nome: draft.nome,
    campanha: draft.campanha,
    descricao: draft.descricao,
    status: draft.status,
    prioridade: draft.prioridade,
    responsavelIds: draft.responsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
    dataInicio: draft.dataInicio,
    dataFimPrevista: draft.dataFimPrevista,
    createdAt: now,
    updatedAt: now,
    resumo: "",
    modeloCampanhaId: generateId("modelo-campanha"),
    modeloCampanha: [],
    equipe: [],
    arquivos: [],
    historico: [createHistoricoProjeto("Projeto criado no mock local")],
  };
}

function updateProjetoFromDraft(
  projeto: Projeto,
  draft: ProjetoFormDraft
): Projeto {
  return {
    ...projeto,
    clienteId: draft.clienteId,
    nome: draft.nome,
    campanha: draft.campanha,
    descricao: draft.descricao,
    status: draft.status,
    prioridade: draft.prioridade,
    responsavelIds: draft.responsavelIds,
    departamentoResponsavelIds: draft.departamentoResponsavelIds,
    dataInicio: draft.dataInicio,
    dataFimPrevista: draft.dataFimPrevista,
    updatedAt: new Date().toISOString(),
    historico: [
      createHistoricoProjeto("Projeto atualizado no mock local"),
      ...projeto.historico,
    ],
  };
}

export function ProjetosView() {
  const [projetos, setProjetos] = useState<Projeto[]>(projetosMock);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] =
    useState<ProjetoStatusFiltro>("todos");
  const [creatingProject, setCreatingProject] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null
  );

  const selectedProject = projetos.find(
    (projeto) => projeto.id === selectedProjectId
  );
  const editingProject = projetos.find(
    (projeto) => projeto.id === editingProjectId
  );

  const filteredProjects = useMemo(
    () =>
      projetos.filter((projeto) => {
        const statusMatches =
          statusFilter === "todos" || projeto.status === statusFilter;
        const queryMatches = query.trim()
          ? matchesProjeto(projeto, query)
          : true;

        return statusMatches && queryMatches;
      }),
    [projetos, query, statusFilter]
  );

  function upsertProject(draft: ProjetoFormDraft, projetoId?: string) {
    if (!projetoId) {
      const newProject = createProjetoFromDraft(draft);
      setProjetos((current) => [newProject, ...current]);
      return newProject.id;
    }

    setProjetos((current) =>
      current.map((projeto) =>
        projeto.id === projetoId
          ? updateProjetoFromDraft(projeto, draft)
          : projeto
      )
    );

    return projetoId;
  }

  function handleSaveAndClose(draft: ProjetoFormDraft, projetoId?: string) {
    upsertProject(draft, projetoId);
    setCreatingProject(false);
    setEditingProjectId(null);
  }

  function handleSaveAndContinue(draft: ProjetoFormDraft, projetoId?: string) {
    const nextProjectId = upsertProject(draft, projetoId);

    setCreatingProject(false);
    setEditingProjectId(null);
    setSelectedProjectId(nextProjectId);
  }

  function handleProjectChange(nextProject: Projeto) {
    setProjetos((current) =>
      current.map((projeto) =>
        projeto.id === nextProject.id ? nextProject : projeto
      )
    );
  }

  function openEdit(projetoId: string) {
    setSelectedProjectId(null);
    setEditingProjectId(projetoId);
  }

  return (
    <WorkspacePage>
      <div className="rounded-3xl border border-zinc-100 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-3xl bg-blue-50 text-blue-700 ring-1 ring-blue-100">
              <FolderKanban className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
                Projetos
              </h1>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">
                Workspace operacional para organizar projetos, campanhas, equipe, modelo de campanha e histórico.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill tone="blue">Carteira operacional</StatusPill>
            <StatusPill tone="green">Mock local</StatusPill>
          </div>
        </div>
      </div>

      <ProjetosStats projetos={projetos} />

      <ProjetosToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onNewProject={() => setCreatingProject(true)}
      />

      {filteredProjects.length === 0 ? (
        <WorkspaceEmptyState
          title="Nenhum projeto encontrado"
          description="Ajuste a busca ou os filtros para visualizar os projetos cadastrados."
        />
      ) : (
        <ProjetosTable
          projetos={filteredProjects}
          onOpenDetails={setSelectedProjectId}
          onEdit={openEdit}
        />
      )}

      {creatingProject && (
        <NovoProjetoModal
          open
          onClose={() => setCreatingProject(false)}
          onSaveAndClose={handleSaveAndClose}
          onSaveAndContinue={handleSaveAndContinue}
        />
      )}

      {editingProject && (
        <NovoProjetoModal
          key={editingProject.id}
          open
          projeto={editingProject}
          onClose={() => setEditingProjectId(null)}
          onSaveAndClose={handleSaveAndClose}
          onSaveAndContinue={handleSaveAndContinue}
        />
      )}

      <ProjetoDetailsDrawer
        projeto={selectedProject}
        onClose={() => setSelectedProjectId(null)}
        onEdit={openEdit}
        onChange={handleProjectChange}
      />
    </WorkspacePage>
  );
}
