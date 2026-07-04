type SectionProps = {
  title: string;
  children: React.ReactNode;
};

export function Section({
  title,
  children,
}: SectionProps) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">
        {title}
      </h2>

      {children}
    </div>
  );
}
