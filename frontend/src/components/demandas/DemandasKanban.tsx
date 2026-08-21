"use client";

import { useMemo, useState } from "react";
import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, type DragEndEvent, type DragStartEvent } from "@dnd-kit/core";
import { Clock, Lock } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { avaliarExpedienteOperacional, MOTIVO_INICIAR_FORA_EXPEDIENTE } from "@/lib/escopo-operacional";
import { useEstadoExpediente } from "@/lib/estadoExpediente";
import type { Demanda, DemandaStatus, DemandaStatusEditavel } from "@/types/demanda";
import { DemandaKanbanCardOverlay } from "./DemandaKanbanCard";
import { DemandaKanbanColumn } from "./DemandaKanbanColumn";

type KanbanColumnConfig = {
  id: string;
  title: string;
  description: string;
  statuses: DemandaStatusEditavel[];
  tone: BadgeTone;
};

const kanbanColumns: KanbanColumnConfig[] = [
  { id: "rascunho-planejada", title: "Rascunho/Planejada", description: "Em preparação ou programadas.", statuses: ["rascunho", "planejada"], tone: "blue" },
  { id: "em-execucao", title: "Em execução", description: "Em andamento na operação.", statuses: ["em_execucao"], tone: "green" },
  { id: "pausada-bloqueada", title: "Pausada/Bloqueada", description: "Fluxos suspensos ou com impedimento.", statuses: ["pausada", "bloqueada"], tone: "amber" },
  { id: "aguardando-cliente", title: "Aguardando cliente", description: "Aguardando retorno externo.", statuses: ["aguardando_cliente"], tone: "amber" },
  { id: "concluida", title: "Concluída", description: "Tarefas finalizadas.", statuses: ["concluida"], tone: "green" },
  { id: "cancelada", title: "Cancelada", description: "Tarefas canceladas.", statuses: ["cancelada"], tone: "neutral" },
];

export function DemandasKanban({
  demandas,
  onOpenDetails,
  onMoveDemanda,
}: {
  demandas: Demanda[];
  onOpenDetails: (demandaId: string) => void;
  onMoveDemanda: (demandaId: string, novoStatus: DemandaStatusEditavel) => void;
}) {
  const { estado } = useEstadoExpediente();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [avisoBloqueio, setAvisoBloqueio] = useState<string | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  // Enquanto `estado` não chegou (primeira busca a GET /expediente/estado) tratamos como
  // fora do expediente: é o lado seguro — não libera arrastar antes de saber o estado real.
  const expediente = estado
    ? avaliarExpedienteOperacional(estado.dentroExpediente)
    : { dentroExpediente: false, podeArrastar: false, podeIniciar: false, motivoBloqueio: undefined };

  const groupedDemands = useMemo(
    () =>
      kanbanColumns.map((column) => ({
        ...column,
        // `arquivada` não chega aqui: a listagem já a exclui e o Kanban não tem essa coluna.
        // O alargamento é só para comparar com o status vindo da API.
        demandas: demandas.filter((demanda) => (column.statuses as DemandaStatus[]).includes(demanda.status)),
      })),
    [demandas],
  );

  const activeDemanda = activeId ? demandas.find((demanda) => demanda.id === activeId) : undefined;

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const column = kanbanColumns.find((candidate) => candidate.id === over.id);
    const demanda = demandas.find((candidate) => candidate.id === active.id);
    if (!column || !demanda) return;
    if ((column.statuses as DemandaStatus[]).includes(demanda.status)) return;

    // Colunas que agrupam mais de um status (ex.: Rascunho/Planejada) usam o
    // primeiro status da lista como destino ao soltar o card.
    const novoStatus = column.statuses[0];

    // Segunda barreira, além de desabilitar o arraste: mesmo que um card chegue aqui
    // (drag iniciado dentro do expediente e solto depois do fim do turno, por exemplo),
    // iniciar fora do horário continua bloqueado.
    if (novoStatus === "em_execucao" && !expediente.podeIniciar) {
      setAvisoBloqueio(MOTIVO_INICIAR_FORA_EXPEDIENTE);
      return;
    }

    setAvisoBloqueio(null);
    onMoveDemanda(demanda.id, novoStatus);
  }

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Fluxo por status</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Arraste um card para mudar o status, ou clique para abrir os detalhes.</p>
        </div>
        {estado?.ativo && (
          <Badge tone={expediente.dentroExpediente ? "green" : "amber"}>
            <Clock className="mr-1 h-3 w-3" />
            {expediente.dentroExpediente ? "Dentro do expediente" : "Fora do expediente — quadro bloqueado"}
          </Badge>
        )}
      </div>

      {!expediente.podeArrastar && estado && (
        <div className="mb-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <p>
            {expediente.motivoBloqueio} Novas tarefas continuam podendo ser cadastradas por Atendimento, heads e
            gestão — elas entram como planejadas e só podem ser iniciadas no próximo turno.
          </p>
        </div>
      )}

      {avisoBloqueio && (
        <div
          role="status"
          className="mb-3 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
        >
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <p>{avisoBloqueio}</p>
        </div>
      )}

      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd} onDragCancel={() => setActiveId(null)}>
        <div className="overflow-x-auto pb-2">
          <div className="flex gap-3">
            {groupedDemands.map((column) => (
              <DemandaKanbanColumn
                key={column.id}
                id={column.id}
                title={column.title}
                description={column.description}
                demandas={column.demandas}
                tone={column.tone}
                onOpenDetails={onOpenDetails}
                arrastavel={expediente.podeArrastar}
                motivoBloqueio={expediente.motivoBloqueio}
              />
            ))}
          </div>
        </div>

        <DragOverlay>{activeDemanda ? <DemandaKanbanCardOverlay demanda={activeDemanda} /> : null}</DragOverlay>
      </DndContext>
    </div>
  );
}
