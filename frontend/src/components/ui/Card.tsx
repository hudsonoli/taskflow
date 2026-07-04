type CardProps = {
  children: React.ReactNode;
};

export function Card({ children }: CardProps) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm">
      {children}
    </div>
  );
}
