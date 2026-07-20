type CardProps = {
  children: React.ReactNode;
};

export function Card({ children }: CardProps) {
  return (
    <div className="rounded-3xl border border-zinc-100 bg-white p-6 shadow-sm">
      {children}
    </div>
  );
}
