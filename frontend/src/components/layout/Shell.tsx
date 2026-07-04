import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

type ShellProps = {
  children: React.ReactNode;
};

export function Shell({ children }: ShellProps) {
  return (
    <main className="min-h-screen bg-[#f4f1ec] text-zinc-900">
      <div className="flex min-h-screen">
        <Sidebar />

        <section className="flex-1">
          <Header />
          {children}
        </section>
      </div>
    </main>
  );
}
