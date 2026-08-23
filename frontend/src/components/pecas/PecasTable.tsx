import { Pencil } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { formatBRL, formatHoursMinutes, valorSindicatoTotalCentavos } from "@/lib/pecas";
import type { Peca } from "@/types/peca";

export function PecasTable({
  pecas,
  podeVerValor,
  onEdit,
}: {
  pecas: Peca[];
  podeVerValor: boolean;
  onEdit: (pecaId: string) => void;
}) {
  if (pecas.length === 0) {
    return <EmptyState title="Nenhuma peça encontrada" description="Ajuste a busca ou os filtros." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Catálogo de peças</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Modelos reutilizáveis de peças e serviços.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
          {pecas.length} registro(s)
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1080px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              <th className="px-4 py-2.5">Peça</th>
              <th className="px-4 py-2.5">Categoria</th>
              <th className="px-4 py-2.5 text-right">Tempo estimado</th>
              {podeVerValor && <th className="px-4 py-2.5 text-right">Valor sindicato</th>}
              <th className="px-4 py-2.5 text-right">Tempo médio</th>
              <th className="px-4 py-2.5 text-right">Tempo calculado (sistema)</th>
              {podeVerValor && <th className="px-4 py-2.5 text-right">Valor</th>}
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {pecas.map((peca) => (
              <tr key={peca.id} className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${peca.status === "ativo" ? "" : "opacity-60"}`}>
                <td className="max-w-64 truncate px-4 py-3 font-semibold text-zinc-900 dark:text-zinc-100" title={peca.nome}>
                  {peca.nome}
                </td>
                <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{peca.categoriaNome || "-"}</td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-400">
                  {peca.tempoEstimadoMinutos ? `${formatHoursMinutes(peca.tempoEstimadoMinutos)}h` : "-"}
                </td>
                {podeVerValor && (
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-400">
                    {peca.sindicatoAtivo && valorSindicatoTotalCentavos(peca) > 0
                      ? formatBRL(valorSindicatoTotalCentavos(peca))
                      : "-"}
                  </td>
                )}
                <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-400">
                  {peca.tempoMedioMinutos ? `${formatHoursMinutes(peca.tempoMedioMinutos)}h` : "-"}
                </td>
                <td
                  className="px-4 py-3 text-right font-mono tabular-nums text-zinc-400 dark:text-zinc-500"
                  title="Calculado a partir de sessões de trabalho vinculadas a esta peça — ainda não disponível nesta fase."
                >
                  {peca.tempoCalculadoExecucaoMinutos ? `${formatHoursMinutes(peca.tempoCalculadoExecucaoMinutos)}h` : "—"}
                </td>
                {podeVerValor && (
                  <td className="px-4 py-3 text-right font-mono tabular-nums text-zinc-600 dark:text-zinc-400">
                    {peca.valorTabelaCentavos ? formatBRL(peca.valorTabelaCentavos) : "-"}
                  </td>
                )}
                <td className="px-4 py-3">
                  {peca.status === "ativo" ? (
                    <Badge tone="green">Ativa</Badge>
                  ) : peca.status === "inativo" ? (
                    <Badge tone="neutral">Inativa</Badge>
                  ) : (
                    <Badge tone="neutral">Arquivada</Badge>
                  )}
                </td>
                <td className="px-4 py-3">
                  <Button variant="secondary" onClick={() => onEdit(peca.id)} className="px-3 py-1.5 text-xs">
                    <Pencil className="h-3.5 w-3.5" />
                    Editar
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
