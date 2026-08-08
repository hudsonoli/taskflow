import { Pencil } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { resolverDepartamentoNome } from "@/lib/referencias";
import { slaPrioridadeAlvoLabels, type SlaRegra } from "@/types/sla";
import type { ClienteDiretorioItem } from "@/lib/api-backend";
import type { DepartamentoDiretorioItem } from "@/lib/api-backend";

const prioridadeTone: Record<SlaRegra["prioridade"], BadgeTone> = {
  todas: "neutral",
  baixa: "blue",
  media: "amber",
  alta: "red",
};

export function SlaTable({
  slaRegras,
  departamentos,
  clientes,
  onEdit,
}: {
  slaRegras: SlaRegra[];
  departamentos: DepartamentoDiretorioItem[];
  clientes: ClienteDiretorioItem[];
  onEdit: (slaRegraId: string) => void;
}) {
  if (slaRegras.length === 0) {
    return <EmptyState title="Nenhuma regra de SLA encontrada" description="Ajuste a busca ou cadastre uma nova regra." />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-1 border-b border-zinc-100 px-4 py-3 dark:border-zinc-800 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-zinc-950 dark:text-zinc-50">Regras de SLA</h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">Prazos de resposta e resolução por prioridade, departamento ou cliente.</p>
        </div>
        <span className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">{slaRegras.length} registro(s)</span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[880px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              <th className="px-4 py-2.5">Regra</th>
              <th className="px-4 py-2.5">Prioridade</th>
              <th className="px-4 py-2.5">Escopo</th>
              <th className="px-4 py-2.5">1ª resposta</th>
              <th className="px-4 py-2.5">Resolução</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {slaRegras.map((regra) => {
              const departamento = regra.departamentoId ? resolverDepartamentoNome(regra.departamentoId, departamentos) : null;
              const cliente = regra.clienteId ? clientes.find((item) => item.id === regra.clienteId)?.nome : null;
              const escopo = [departamento, cliente].filter(Boolean).join(" · ") || "Toda a operação";

              return (
                <tr key={regra.id} className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${regra.ativo ? "" : "opacity-60"}`}>
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => onEdit(regra.id)} className="text-left">
                      <span className="font-semibold text-zinc-950 transition group-hover:text-indigo-600 dark:text-zinc-50 dark:group-hover:text-indigo-400">
                        {regra.nome}
                      </span>
                      <p className="mt-0.5 max-w-[280px] truncate text-xs text-zinc-400" title={regra.descricao}>
                        {regra.descricao || "Sem descrição"}
                      </p>
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={prioridadeTone[regra.prioridade]}>{slaPrioridadeAlvoLabels[regra.prioridade]}</Badge>
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{escopo}</td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{regra.prazoPrimeiraRespostaHoras}h</td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{regra.prazoResolucaoHoras}h</td>
                  <td className="px-4 py-3">
                    {regra.ativo ? <Badge tone="green">Ativa</Badge> : <Badge tone="neutral">Inativa</Badge>}
                  </td>
                  <td className="px-4 py-3">
                    <Button variant="secondary" onClick={() => onEdit(regra.id)} className="px-3 py-1.5 text-xs">
                      <Pencil className="h-3.5 w-3.5" />
                      Editar
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
