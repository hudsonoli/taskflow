import { Bell, CalendarDays, Clock3 } from "lucide-react";

type ActionButtonProps = {
  label: string;
  icon: typeof Bell;
};

function ActionButton({ label, icon: Icon }: ActionButtonProps) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-transparent text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
    >
      <Icon className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
    </button>
  );
}

export function HeaderActions() {
  return (
    <div className="flex items-center gap-1">
      <ActionButton label="Agenda" icon={CalendarDays} />
      <ActionButton label="Atividades" icon={Clock3} />
    </div>
  );
}
