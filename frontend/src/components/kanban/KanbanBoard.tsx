"use client";

import { DndContext, type DragEndEvent } from "@dnd-kit/core";
import { useState } from "react";
import { KanbanColumn, type KanbanTask } from "./KanbanColumn";

type KanbanColumnConfig = {
  id: string;
  title: string;
};

const columns: KanbanColumnConfig[] = [
  { id: "backlog", title: "Backlog" },
  { id: "em-andamento", title: "Em andamento" },
  { id: "revisao", title: "Revisão" },
  { id: "concluido", title: "Concluído" },
];

const initialTasks: KanbanTask[] = [
  {
    id: "task-1",
    title: "Landing Page Campanha",
    client: "Cliente Exemplo",
    project: "Campanha Institucional",
    assignee: "Criação",
    priority: "Alta",
    deadline: "08/07",
    sla: "2 dias",
    taskType: "Criação",
    rework: "Não",
    columnId: "backlog",
  },
  {
    id: "task-2",
    title: "Criar anúncios Meta",
    client: "Cliente Exemplo",
    project: "Performance",
    assignee: "Mídia",
    priority: "Media",
    deadline: "09/07",
    sla: "3 dias",
    taskType: "Mídia",
    rework: "Não",
    columnId: "backlog",
  },
  {
    id: "task-3",
    title: "Revisar identidade visual",
    client: "Cliente Exemplo",
    project: "Branding",
    assignee: "Direção de Arte",
    priority: "Alta",
    deadline: "05/07",
    sla: "1 dia",
    taskType: "Design",
    rework: "Sim",
    columnId: "em-andamento",
  },
  {
    id: "task-4",
    title: "Validar peças da campanha",
    client: "Cliente Exemplo",
    project: "Social Media",
    assignee: "Atendimento",
    priority: "Baixa",
    deadline: "10/07",
    sla: "4 dias",
    taskType: "Aprovação",
    rework: "Não",
    columnId: "revisao",
  },
  {
    id: "task-5",
    title: "Publicação de conteúdo",
    client: "Cliente Exemplo",
    project: "Redes Sociais",
    assignee: "Operação",
    priority: "Baixa",
    deadline: "Concluído",
    sla: "Finalizado",
    taskType: "Publicação",
    rework: "Não",
    columnId: "concluido",
  },
];

export function KanbanBoard() {
  const [tasks, setTasks] = useState<KanbanTask[]>(initialTasks);

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;

    if (!over) return;

    const taskId = String(active.id);
    const newColumnId = String(over.id);

    setTasks((currentTasks) =>
      currentTasks.map((task) =>
        task.id === taskId ? { ...task, columnId: newColumnId } : task
      )
    );
  }

  return (
    <DndContext onDragEnd={handleDragEnd}>
      <div className="overflow-x-auto">
        <div className="flex gap-6 pb-4">
          {columns.map((column) => (
            <KanbanColumn
              key={column.id}
              id={column.id}
              title={column.title}
              tasks={tasks.filter((task) => task.columnId === column.id)}
            />
          ))}
        </div>
      </div>
    </DndContext>
  );
}
