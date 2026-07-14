import type { ReactNode } from "react";
import { EntityFieldRow } from "@/components/ui/EntityFieldRow";

export type EntityPeekSummaryItem = {
  label: string;
  value: ReactNode;
};

export type EntityPeekProps = {
  summary: EntityPeekSummaryItem[];
  tags?: ReactNode;
  relations?: ReactNode;
  history?: ReactNode;
};

/**
 * Corpo do EntityDrawer em modo peek — composição somente-leitura. Não
 * recebe nenhuma prop de mutação/onChange por contrato: edição inline não é
 * possível por construção, não apenas por convenção (entity-component-api.md,
 * seção 3).
 */
export function EntityPeek({ summary, tags, relations, history }: EntityPeekProps) {
  return (
    <div className="min-h-0 min-w-0 flex-1 space-y-4 overflow-y-auto overflow-x-hidden px-3 py-2.5">
      {tags}

      <dl className="grid grid-cols-1 gap-3">
        {summary.map((item) => (
          <EntityFieldRow
            key={item.label}
            label={item.label}
            value={item.value}
            density="compact"
          />
        ))}
      </dl>

      {relations}
      {history}
    </div>
  );
}
