type ButtonProps = {
  children: React.ReactNode;
};

export function Button({ children }: ButtonProps) {
  return (
    <button className="rounded-2xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90">
      {children}
    </button>
  );
}
