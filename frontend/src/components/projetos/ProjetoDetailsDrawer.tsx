"use client";

import { useState } from "react";
import { CalendarDays, FolderKanban, UsersRound } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DetailsModal } from "@/components/ui/DetailsModal";
import { Tabs } from "@/components/ui/Tabs";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { prioridadeProjetoLabels, statusProjetoLabels } from "@/lib/projetos";
import type { Projeto, ProjetoStatus } from "@/types/projeto";
import {
  ArquivosProjetoSection,
  DadosProjetoSection,
  EquipeProjetoSection,
  HistoricoProjetoSection,
  ModeloCampanhaSection,
  ResumoProjetoSection,
} from "./ProjetoFormSections";
import { ProjetoDemandasSection } from "./ProjetoDemandasSection";

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "demandas", label: "Demandas" },
  { id: "resumo", label: "Resumo" },
  { id: "modelo", label: "Modelo" },
  { id: "equipe", label: "Equipe" },
  { id: "arquivos", label: "Arquivos" },
  { id: "historico", label: "Histórico" },
];

const statusTone: Record<ProjetoStatus, BadgeTone> = {
  planejamento: "blue",
  ativo: "green",
  pausado: "amber",
  concluido: "green",
  cancelado: "neutral",
  arquivado: "red",
};

/**
 * Painel de **inspeção** do projeto — somente leitura.
 *
 * Decisão da Fase 2D, aprovada: até então as seções editavam em linha, gravando direto no
 * estado local do mock. Com persistência real isso viraria um PATCH por tecla digitada.
 *
 * O desenho adotado separa os papéis:
 * - **este drawer** inspeciona;
 * - **`NovoProjetoModal`** edita;
 * - salvar é um ato explícito, com resposta única do servidor.
 *
 * Deliberadamente **sem autosave** nesta fase. Se um dia a edição em linha voltar, ela
 * precisa de debounce e de um indicador de estado de gravação — nada disso é grátis, e
 * inventá-lo agora seria dívida sem demanda. O botão "Editar projeto" leva ao modal.
 */
export function ProjetoDetailsDrawer({
  projeto,
  onClose,
  onEdit,
}: {
  projeto?: Projeto;
  onClose: () => void;
  onEdit: (projetoId: string) => void;
}) {
  const [activeTab, setActiveTab] = useState("dados");
  const { clientes } = useDiretorioClientes();
  const { usuarios } = useDiretorioUsuarios();
  const { departamentos } = useDiretorioDepartamentos();

  const nomeCliente =
    clientes.find((cliente) => cliente.id === projeto?.clienteId)?.nome ?? "Sem cliente";
  const nomesResponsaveis =
    (projeto?.responsavelIds ?? [])
      .map((id) => usuarios.find((usuario) => usuario.id === id)?.nome ?? id)
      .join(", ") || "-";
  const nomesDepartamentos =
    (projeto?.departamentoResponsavelIds ?? [])
      .map((id) => departamentos.find((departamento) => departamento.id === id)?.nome ?? id)
      .join(", ") || "-";

  return (
    <DetailsModal
      open={projeto !== undefined}
      onClose={onClose}
      onEdit={projeto ? () => onEdit(projeto.id) : undefined}
      editLabel="Editar projeto"
      title={projeto?.nome ?? "Projeto"}
      description={projeto ? `${projeto.codigoReferencia} · ${nomeCliente}` : undefined}
      footer={
        <div className="flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      }
    >
      {projeto && (
        <div className="space-y-5">
          <div className="rounded-2xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                  <FolderKanban className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">Painel do projeto</p>
                  <h3 className="mt-1 text-lg font-semibold text-zinc-950 dark:text-zinc-50">{projeto.campanha}</h3>
                  <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{nomeCliente}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone={statusTone[projeto.status]}>{statusProjetoLabels[projeto.status]}</Badge>
                <Badge tone="blue">{prioridadeProjetoLabels[projeto.prioridade]}</Badge>
              </div>
            </div>

            <div className="mt-4 rounded-xl bg-white p-3 ring-1 ring-zinc-100 dark:bg-zinc-900 dark:ring-zinc-800">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-400">Responsáveis</p>
              <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                <UsersRound className="h-4 w-4 text-zinc-400" />
                {nomesResponsaveis}
              </p>
              <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                {nomesDepartamentos}
              </p>
            </div>

            <p className="mt-3 flex items-center gap-1.5 text-xs text-zinc-400">
              <CalendarDays className="h-3.5 w-3.5" />
              Prazo: {projeto.dataFimPrevista}
            </p>
          </div>

          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          {activeTab === "dados" && <DadosProjetoSection projeto={projeto} somenteLeitura />}
          {activeTab === "demandas" && <ProjetoDemandasSection projetoId={projeto.id} />}
          {activeTab === "resumo" && <ResumoProjetoSection projeto={projeto} somenteLeitura />}
          {activeTab === "modelo" && <ModeloCampanhaSection projeto={projeto} somenteLeitura />}
          {activeTab === "equipe" && <EquipeProjetoSection projeto={projeto} somenteLeitura />}
          {activeTab === "arquivos" && <ArquivosProjetoSection />}
          {activeTab === "historico" && <HistoricoProjetoSection />}
        </div>
      )}
    </DetailsModal>
  );
}
