"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { FolderKanban } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  AGENCIA_PADRAO_ID,
  EMPRESA_PADRAO_ID,
  generateCodigoInterno,
  generateId,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
} from "@/lib/projetos-mock";
import { useAppData } from "@/lib/AppDataContext";
import type { Projeto, ProjetoFormDraft } from "@/types/projeto";
import { NovoProjetoModal } from "./NovoProjetoModal";
import { ProjetoDetailsDrawer } from "./ProjetoDetailsDrawer";
import { ProjetosStats } from "./ProjetosStats";
import { ProjetosTable } from "./ProjetosTable";
import { type ProjetoStatusFiltro, ProjetosToolbar } from "./ProjetosToolbar";

function normalize(value: string) {
  return value.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
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
    usuario: "Você",
    acao,
    dataHora: new Date().toLocaleString("pt-BR"),
    ip: "127.0.0.1",
    dispositivo: "Workspace local",
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
    historico: [createHistoricoProjeto("Projeto criado")],
  };
}

function updateProjetoFromDraft(projeto: Projeto, draft: ProjetoFormDraft): Projeto {
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
    historico: [createHistoricoProjeto("Projeto atualizado"), ...projeto.historico],
  };
}

export function ProjetosView() {
  const { projetos, setProjetos } = useAppData();
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<ProjetoStatusFiltro>("todos");
  const [creatingProject, setCreatingProject] = useState(false);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const selectedProject = projetos.find((projeto) => projeto.id === selectedProjectId);
  const editingProject = projetos.find((projeto) => projeto.id === editingProjectId);

  const filteredProjects = useMemo(
    () =>
      projetos.filter((projeto) => {
        const statusMatches = statusFilter === "todos" || projeto.status === statusFilter;
        const queryMatches = query.trim() ? matchesProjeto(projeto, query) : true;
        return statusMatches && queryMatches;
      }),
    [projetos, query, statusFilter],
  );

  function upsertProject(draft: ProjetoFormDraft, projetoId?: string) {
    if (!projetoId) {
      const newProject = createProjetoFromDraft(draft);
      setProjetos((current) => [newProject, ...current]);
      return newProject.id;
    }

    setProjetos((current) => current.map((projeto) => (projeto.id === projetoId ? updateProjetoFromDraft(projeto, draft) : projeto)));
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
    setProjetos((current) => current.map((projeto) => (projeto.id === nextProject.id ? nextProject : projeto)));
  }

  function openEdit(projetoId: string) {
    setSelectedProjectId(null);
    setEditingProjectId(projetoId);
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <FolderKanban className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Projetos</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                Raiz de cada empreendimento/campanha — as demandas se organizam a partir de um projeto.
              </p>
            </div>
          </div>
          <Badge tone="blue">Dados locais</Badge>
        </div>
      </motion.div>

      <ProjetosStats projetos={projetos} />

      <ProjetosToolbar
        query={query}
        onQueryChange={setQuery}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onNewProject={() => setCreatingProject(true)}
      />

      {filteredProjects.length === 0 ? (
        <EmptyState title="Nenhum projeto encontrado" description="Ajuste a busca ou os filtros para visualizar os projetos cadastrados." />
      ) : (
        <ProjetosTable projetos={filteredProjects} onOpenDetails={setSelectedProjectId} onEdit={openEdit} />
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
    </div>
  );
}
