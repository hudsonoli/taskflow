import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { SidebarProvider } from "./SidebarContext";

type ShellProps = {
  children: React.ReactNode;
};

export function Shell({ children }: ShellProps) {
  return (
    <main className="min-h-screen bg-[#f4f1ec] text-zinc-900">
      <SidebarProvider>
        <div className="flex min-h-screen min-w-0">
          <Sidebar />

          <section className="min-w-0 flex-1 overflow-x-hidden">
            <Header />
            {children}
          </section>
        </div>
      </SidebarProvider>
    </main>
  );
}
