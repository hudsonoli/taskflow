type EmptyStateProps = {
  title: string;
  description: string;
};

export function EmptyState({
  title,
  description,
}: EmptyStateProps) {
  return (
    <div className="rounded-3xl border border-dashed border-zinc-200 bg-[#faf8f4] p-10 text-center">
      <h3 className="text-lg font-semibold">{title}</h3>

      <p className="mt-2 text-sm text-zinc-500">
        {description}
      </p>
    </div>
  );
}
