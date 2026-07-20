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
      <h3 className="text-base font-semibold text-zinc-950">{title}</h3>

      <p className="mx-auto mt-2 max-w-md text-sm text-zinc-500">
        {description}
      </p>
    </div>
  );
}
