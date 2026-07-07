import { Bell, CalendarDays, Clock3 } from "lucide-react";

type ActionButtonProps = {
  label: string;
  icon: typeof Bell;
  badge?: string;
};

function ActionButton({ label, icon: Icon, badge }: ActionButtonProps) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      className="relative flex h-11 w-11 items-center justify-center rounded-2xl border border-zinc-200 bg-white text-zinc-600 shadow-sm transition hover:bg-zinc-100"
    >
      <Icon className="h-5 w-5" strokeWidth={2} aria-hidden="true" />
      {badge ? (
        <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
          {badge}
        </span>
      ) : null}
    </button>
  );
}

export function HeaderActions() {
  return (
    <div className="flex items-center gap-2">
      <ActionButton label="Notificações" icon={Bell} badge="3" />
      <ActionButton label="Agenda" icon={CalendarDays} />
      <ActionButton label="Atividades" icon={Clock3} />
    </div>
  );
}
