export type WorkspaceStat = {
  label: string;
  value: React.ReactNode;
  description?: string;
};

type WorkspaceStatsProps = {
  stats: WorkspaceStat[];
};

export function WorkspaceStats({ stats }: WorkspaceStatsProps) {
  return (
    <div className="grid gap-5 md:grid-cols-3">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-3xl border border-zinc-100 bg-white p-6 shadow-sm"
        >
          <p className="text-sm text-zinc-500">{stat.label}</p>
          <p className="mt-3 text-3xl font-bold text-zinc-900">
            {stat.value}
          </p>

          {stat.description && (
            <p className="mt-2 text-sm text-zinc-500">{stat.description}</p>
          )}
        </div>
      ))}
    </div>
  );
}
