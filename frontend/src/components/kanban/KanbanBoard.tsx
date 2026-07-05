import { KanbanColumn } from "./KanbanColumn";

const mockData = {
  backlog: [
    {
      id: "1",
      title: "Landing Page Campanha",
      client: "Cliente Exemplo",
      priority: "Alta",
    },
    {
      id: "2",
      title: "Criar anúncios Meta",
      client: "Cliente Exemplo",
      priority: "Média",
    },
  ],

  andamento: [
    {
      id: "3",
      title: "Revisar identidade visual",
      client: "Cliente Exemplo",
      priority: "Alta",
    },
  ],

  revisao: [
    {
      id: "4",
      title: "Validar peças da campanha",
      client: "Cliente Exemplo",
      priority: "Baixa",
    },
  ],

  concluido: [
    {
      id: "5",
      title: "Publicação de conteúdo",
      client: "Cliente Exemplo",
      priority: "Baixa",
    },
  ],
};

export function KanbanBoard() {
  return (
    <div className="overflow-x-auto">
      <div className="flex gap-6 pb-4">
        <KanbanColumn
          title="Backlog"
          tasks={mockData.backlog}
        />

        <KanbanColumn
          title="Em andamento"
          tasks={mockData.andamento}
        />

        <KanbanColumn
          title="Revisão"
          tasks={mockData.revisao}
        />

        <KanbanColumn
          title="Concluído"
          tasks={mockData.concluido}
        />
      </div>
    </div>
  );
}
