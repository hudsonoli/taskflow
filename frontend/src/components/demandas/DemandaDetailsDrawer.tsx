"use client";

import { useState } from "react";
import { CalendarDays, ClipboardList, FolderKanban } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { DetailsModal } from "@/components/ui/DetailsModal";
import { Tabs } from "@/components/ui/Tabs";
import { type EscopoLeituraDemanda } from "@/lib/api-backend";
import { formatPrazo, normalizarUsuarioId, prioridadeDemandaLabels, statusDemandaLabels, statusDemandaTone } from "@/lib/demandas";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { resolverProjetoNome, resolverUsuarioPorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";
import { useUsuariosComIds } from "@/lib/useUsuariosComIds";
import type { Demanda, DemandaPrioridade } from "@/types/demanda";
import { AtividadeDemandaSection } from "./AtividadeDemandaSection";
import { DemandaConclusaoBanner } from "./DemandaConclusaoBanner";
import {
  BriefingDemandaSection,
  DadosDemandaSection,
  HistoricoDemandaSection,
  ResponsaveisDemandaSection,
  WorkflowDemandaSection,
} from "./DemandaFormSections";
import { LeituraDemandaProvider } from "./leituraDemanda";

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "briefing", label: "Briefing" },
  { id: "workflow", label: "Workflow" },
  { id: "responsaveis", label: "Responsáveis" },
  { id: "atividade", label: "Atividade" },
  { id: "historico", label: "Histórico" },
];


const prioridadeTone: Record<DemandaPrioridade, BadgeTone> = {
  alta: "blue",
  media: "blue",
  baixa: "neutral",
};

export function DemandaDetailsDrawer({
  demanda,
  onClose,
  onEdit,
  onChange,
  initialTab,
  modoLeitura,
}: {
  demanda?: Demanda;
  onClose: () => void;
  onEdit: (demandaId: string) => void;
  onChange: (demanda: Demanda) => void;
  initialTab?: string;
  /**
   * Fase 7C.1 — `"pauta"`: demanda aberta pela Pauta GLOBAL, de um departamento fora do escopo-base de quem olha. O drawer vira
   * SOMENTE LEITURA: consulta o detalhe e os subrecursos com `escopo=pauta`, desabilita os campos e esconde as ações de escrita.
   * Ler pela Pauta global não é poder escrever (o servidor também recusa).
   */
  modoLeitura?: EscopoLeituraDemanda;
}) {
  const somenteLeitura = modoLeitura !== undefined;
  const [activeTab, setActiveTab] = useState(initialTab ?? "dados");
  const { usuarios } = useUsuariosComIds(demanda?.usuarioResponsavelIds ?? []);
  const { projetos } = useDiretorioProjetos();

  return (
    <LeituraDemandaProvider value={modoLeitura}>
    <DetailsModal
      open={demanda !== undefined}
      onClose={onClose}
      onEdit={demanda && !somenteLeitura ? () => onEdit(demanda.id) : undefined}
      editLabel="Editar tarefa"
      title={demanda?.nome ?? "Tarefa"}
      description={demanda ? `${rotuloDemanda(demanda)} · ${resolverProjetoNome(demanda.projetoId, projetos)}` : undefined}
      footer={
        <div className="flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      }
    >
      {demanda && (
        <div className="space-y-5">
          {somenteLeitura ? (
            <p role="status" className="rounded-xl border border-indigo-100 bg-indigo-50/60 px-3.5 py-2.5 text-xs leading-5 text-indigo-800 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-200">
              Visualização somente leitura: esta tarefa é de outro departamento. Você pode consultar o detalhe, mas não alterá-la.
            </p>
          ) : (
            <DemandaConclusaoBanner demanda={demanda} onChange={onChange} />
          )}

          <div className="rounded-2xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                  <ClipboardList className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-fg-subtle">Painel da tarefa</p>
                  <h3 className="mt-1 text-lg font-semibold text-fg">{demanda.nome}</h3>
                  <p className="mt-1 flex items-center gap-2 text-sm text-fg-muted">
                    <FolderKanban className="h-4 w-4" />
                    {resolverProjetoNome(demanda.projetoId, projetos)}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                <Badge tone={prioridadeTone[demanda.prioridade]}>{prioridadeDemandaLabels[demanda.prioridade]}</Badge>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl bg-surface p-3 ring-1 ring-zinc-100 dark:ring-zinc-800">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-fg-subtle">Prazo atual</p>
                <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-zinc-800 dark:text-zinc-100">
                  <CalendarDays className="h-4 w-4 text-fg-subtle" />
                  {formatPrazo(demanda.prazoEtapaAtual)}
                </p>
              </div>
              <div className="rounded-xl bg-surface p-3 ring-1 ring-zinc-100 dark:ring-zinc-800 sm:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-fg-subtle">Responsáveis</p>
                <div className="mt-2">
                  <AvatarStack
                    pessoas={demanda.usuarioResponsavelIds
                      .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                      .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario))
                      .map((usuario) => ({
                        id: usuario.id,
                        nome: usuario.nome,
                        corIdentificacao: usuario.corIdentificacao,
                        fotoUrl: usuario.fotoUrl,
                      }))}
                    max={5}
                    size="h-7 w-7"
                  />
                </div>
              </div>
            </div>
          </div>

          {/*
            "Resumo do projeto" saiu na Fase 2E.5A: usava a projeção mock (`resolveProjetoResumo`).
            `Projeto.resumo` real só existe em `GET /projetos/{id}` (gestor/admin — `require_admin_or_gestor`),
            rota que este drawer não pode chamar pra qualquer usuário que veja uma Demanda.
            `GET /projetos/diretorio` (todo autenticado) não carrega `resumo` de propósito — não é pra
            engordar com esse payload. Reintroduzir isto exige decisão de autorização/endpoint, não feita
            nesta rodada — ver relatório da Fase 2E.5A.
          */}

          <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

          {/* Na leitura, `fieldset disabled` desabilita nativamente todo campo/botão do conteúdo (defesa em profundidade além de os
              cartões esconderem os controles de escrita). Fora dela é só um agrupador sem efeito. */}
          <fieldset disabled={somenteLeitura} className="m-0 min-w-0 border-0 p-0">
            {activeTab === "dados" && <DadosDemandaSection demanda={demanda} onChange={onChange} />}
            {activeTab === "briefing" && <BriefingDemandaSection key={demanda.id} demanda={demanda} onChange={onChange} />}
            {activeTab === "workflow" && <WorkflowDemandaSection demanda={demanda} onChange={onChange} />}
            {activeTab === "responsaveis" && <ResponsaveisDemandaSection demanda={demanda} onChange={onChange} />}
            {activeTab === "atividade" && <AtividadeDemandaSection demanda={demanda} />}
            {activeTab === "historico" && <HistoricoDemandaSection demanda={demanda} />}
          </fieldset>
        </div>
      )}
    </DetailsModal>
    </LeituraDemandaProvider>
  );
}
