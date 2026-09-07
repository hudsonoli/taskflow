import { Archive, Pencil, Timer } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { resolverClienteNome, resolverDepartamentoNome } from "@/lib/referencias";
import { formatarPrazo, slaPrioridadeAlvoLabels, slaStatusLabels, type SlaRegra, type SlaRegraStatus } from "@/types/sla";
import type { ClienteDiretorioItem, DepartamentoDiretorioItem } from "@/lib/api-backend";

const statusTone: Record<SlaRegraStatus, "green" | "amber" | "neutral"> = {
  ativo: "green",
  inativo: "amber",
  arquivado: "neutral",
};

export function SlaTable({
  slaRegras,
  departamentos,
  clientes,
  onEdit,
  onArquivar,
  onRestaurar,
}: {
  slaRegras: SlaRegra[];
  departamentos: DepartamentoDiretorioItem[];
  clientes: ClienteDiretorioItem[];
  onEdit: (slaRegraId: string) => void;
  onArquivar: (slaRegraId: string) => void;
  onRestaurar: (slaRegraId: string) => void;
}) {
  if (slaRegras.length === 0) {
    return (
      <EmptyState
        title="Nenhuma regra de SLA encontrada"
        description="Ajuste a busca ou os filtros, ou cadastre uma nova regra."
        icon={<Timer size={16} />}
      />
    );
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
        <table className="min-w-[960px] w-full text-left text-sm">
          <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-zinc-400 dark:bg-zinc-950/40">
            <tr>
              <th className="px-4 py-2.5">Nome</th>
              <th className="px-4 py-2.5">Escopo</th>
              <th className="px-4 py-2.5">1ª resposta</th>
              <th className="px-4 py-2.5">Resolução</th>
              <th className="px-4 py-2.5">Precedência</th>
              <th className="px-4 py-2.5">Expediente</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {slaRegras.map((regra) => {
              const prioridadeLabel = regra.prioridadeAlvo ? slaPrioridadeAlvoLabels[regra.prioridadeAlvo] : "Todas";
              const departamentoLabel = regra.departamentoId
                ? resolverDepartamentoNome(regra.departamentoId, departamentos)
                : "Todos";
              const clienteLabel = regra.clienteId ? resolverClienteNome(regra.clienteId, clientes) : "Todos";

              return (
                <tr
                  key={regra.id}
                  className={`group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5 ${
                    regra.status === "ativo" ? "" : "opacity-60"
                  }`}
                >
                  <td className="px-4 py-3">
                    <button type="button" onClick={() => onEdit(regra.id)} className="text-left">
                      <span className="font-semibold text-zinc-950 transition group-hover:text-indigo-600 dark:text-zinc-50 dark:group-hover:text-indigo-400">
                        {regra.nome}
                      </span>
                      <p className="mt-0.5 max-w-[220px] truncate text-xs text-zinc-400" title={regra.descricao ?? ""}>
                        {regra.descricao || "Sem descrição"}
                      </p>
                    </button>
                  </td>
                  <td className="px-4 py-3 text-xs leading-5 text-zinc-500 dark:text-zinc-400">
                    <div>
                      Prioridade: <span className="font-medium text-zinc-700 dark:text-zinc-300">{prioridadeLabel}</span>
                    </div>
                    <div>
                      Departamento: <span className="font-medium text-zinc-700 dark:text-zinc-300">{departamentoLabel}</span>
                    </div>
                    <div>
                      Cliente: <span className="font-medium text-zinc-700 dark:text-zinc-300">{clienteLabel}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {formatarPrazo(regra.prazoPrimeiraRespostaQuantidade, regra.prazoPrimeiraRespostaUnidade)}
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">
                    {formatarPrazo(regra.prazoResolucaoQuantidade, regra.prazoResolucaoUnidade)}
                  </td>
                  <td className="px-4 py-3 text-zinc-600 dark:text-zinc-400">{regra.prioridadeRegra}</td>
                  <td className="px-4 py-3">
                    {regra.considerarApenasExpediente ? (
                      <Badge tone="blue">Expediente</Badge>
                    ) : (
                      <Badge tone="neutral">24h</Badge>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={statusTone[regra.status]}>{slaStatusLabels[regra.status]}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {regra.status === "arquivado" ? (
                        <Button variant="secondary" onClick={() => onRestaurar(regra.id)} className="px-3 py-1.5 text-xs">
                          Restaurar
                        </Button>
                      ) : (
                        <>
                          <Button variant="secondary" onClick={() => onEdit(regra.id)} className="px-3 py-1.5 text-xs">
                            <Pencil className="h-3.5 w-3.5" />
                            Editar
                          </Button>
                          <button
                            type="button"
                            onClick={() => onArquivar(regra.id)}
                            aria-label={`Arquivar ${regra.nome}`}
                            className="rounded-full p-1.5 text-zinc-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                          >
                            <Archive className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
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
