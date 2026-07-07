import { currentUser } from "@/lib/conta-mock";
import { Card } from "@/components/ui/Card";

const today = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "full",
});

function getGreeting(hour = new Date().getHours()) {
  if (hour < 12) return "Bom dia";
  if (hour < 18) return "Boa tarde";
  return "Boa noite";
}

export function DashboardGreeting() {
  return (
    <Card>
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-zinc-400">
          {today.format(new Date())}
        </p>
        <h2 className="text-3xl font-semibold text-zinc-900">
          {getGreeting()}, {currentUser.nome}
        </h2>
        <p className="max-w-3xl text-sm leading-6 text-zinc-500">
          Aqui está um resumo do que merece atenção hoje no TaskFloww.
        </p>
      </div>
    </Card>
  );
}
