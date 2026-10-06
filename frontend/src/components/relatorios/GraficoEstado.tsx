"use client";

import type { ReactNode } from "react";
import { Inbox } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";

/**
 * D4B — estados de um gráfico/relatório alimentado pelo servidor. Carregando e erro NUNCA
 * mostram o gráfico com dado parcial ou antigo: ou os números chegaram, ou aparece o estado.
 */
export function GraficoEstado({
  carregando,
  erro,
  children,
}: {
  carregando: boolean;
  erro: string | null;
  children: ReactNode;
}) {
  if (erro) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
        Não foi possível carregar os dados: {erro}
      </div>
    );
  }
  if (carregando) {
    return <EmptyState title="Carregando…" description="Buscando os dados no servidor." icon={<Inbox size={16} />} />;
  }
  return <>{children}</>;
}
