import type { ReactNode } from "react";

type CadastroTableProps = {
  children: ReactNode;
  minWidth?: string;
};

export function CadastroTable({ children, minWidth = "760px" }: CadastroTableProps) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-zinc-100 bg-white shadow-sm">
      <table
        className="w-full text-left text-sm"
        style={{ minWidth }}
      >
        {children}
      </table>
    </div>
  );
}

export const cadastroTableHeaderClassName =
  "border-b border-zinc-100 bg-[#faf8f4] text-[11px] uppercase tracking-[0.04em] text-zinc-500";

export const cadastroTableHeaderCellClassName = "px-3 py-2 font-semibold";

export const cadastroTableRowClassName =
  "border-b border-zinc-100 transition-colors last:border-0 hover:bg-zinc-50 focus:bg-zinc-50 focus:outline-none";

export const cadastroTableCellClassName = "px-3 py-2 align-middle";

export type CadastroTableDensity = "compact" | "default";

/**
 * Variante de densidade das classes de célula, mantendo
 * cadastroTableHeaderCellClassName/cadastroTableCellClassName como padrão
 * inalterado. Único ponto de verdade para telas que precisarem de uma
 * tabela mais compacta, evitando reimplementar o padding localmente.
 */
export function getCadastroTableCellClassNames(
  density: CadastroTableDensity = "default"
) {
  const verticalPadding = density === "compact" ? "py-0.5" : "py-2";
  // compact usa peso mais leve no cabeçalho (régua dos badges); default
  // mantém font-semibold, igual ao original.
  const headerFontWeight = density === "compact" ? "font-medium" : "font-semibold";

  return {
    headerCell: `px-3 ${verticalPadding} ${headerFontWeight}`,
    cell: `px-3 ${verticalPadding} align-middle`,
  };
}
