import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

const shortcuts = [
  "Novo Cliente",
  "Nova Tarefa",
  "Novo Projeto",
  "Novo Usuário",
];

export function DashboardShortcuts() {
  return (
    <Card>
      <div>
        <h3 className="text-xl font-semibold text-zinc-900">Atalhos rápidos</h3>
        <p className="mt-1 text-sm text-zinc-500">Ações frequentes do dia a dia.</p>
      </div>

      <div className="mt-6 grid gap-3">
        {shortcuts.map((shortcut) => (
          <Button key={shortcut} variant="secondary" className="justify-start">
            {shortcut}
          </Button>
        ))}
      </div>
    </Card>
  );
}
