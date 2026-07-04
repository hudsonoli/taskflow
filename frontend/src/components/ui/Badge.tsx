type BadgeProps = {
  children: React.ReactNode;
};

export function Badge({ children }: BadgeProps) {
  return (
    <span className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700">
      {children}
    </span>
  );
}
