import type { ReactNode } from "react";
import { ConfiguracoesSidebarNav } from "@/components/configuracoes/ConfiguracoesSidebarNav";

export default function ConfiguracoesLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-stretch lg:gap-8">
      <ConfiguracoesSidebarNav />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
