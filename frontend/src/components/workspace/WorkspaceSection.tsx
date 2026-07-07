type WorkspaceSectionProps = {
  title: string;
  description?: string;
  children: React.ReactNode;
};

export function WorkspaceSection({
  title,
  description,
  children,
}: WorkspaceSectionProps) {
  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-6 shadow-sm">
      <div>
        <h2 className="text-lg font-semibold text-zinc-900">{title}</h2>

        {description && (
          <p className="mt-1 text-sm text-zinc-500">{description}</p>
        )}
      </div>

      <div className="mt-6">{children}</div>
    </section>
  );
}
