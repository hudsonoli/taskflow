import type { ReactNode } from "react";

export type EntityFormProps = {
  children: ReactNode;
};

/**
 * Container puro de layout: grid de 12 colunas, gap padronizado. Nada além
 * disso — sem prop de densidade/colunas, sem escape hatch para voltar ao
 * padrão fixo md:grid-cols-2 (entity-component-api.md, seção 5).
 *
 * Cada campo é posicionado por quem o declara, envolvendo o controle num
 * wrapper de span utilitário, ex.:
 *   <div className="col-span-12 md:col-span-4"><Input label="..." /></div>
 */
export function EntityForm({ children }: EntityFormProps) {
  return <div className="grid grid-cols-12 gap-x-3 gap-y-2">{children}</div>;
}
