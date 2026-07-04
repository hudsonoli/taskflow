type StatCardProps = {
  title: string;
  value: string;
  description: string;
};

export function StatCard({
  title,
  value,
  description,
}: StatCardProps) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      <div className="text-sm font-medium text-zinc-500">
        {title}
      </div>

      <div className="mt-4 text-4xl font-bold">
        {value}
      </div>

      <div className="mt-3 text-sm text-zinc-500">
        {description}
      </div>
    </div>
  );
}
