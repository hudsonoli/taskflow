import { Info } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { TEXTO_TRUNCADA, type LinhaFila } from "@/lib/trafego-operacional";

const TOM_ESTADO: Record<LinhaFila["estados"][number]["id"], BadgeTone> = {
  emExecucao: "blue",
  pausadas: "neutral",
  bloqueadas: "red",
  aguardandoCliente: "amber",
  planejadas: "neutral",
};

/**
 * Fila ATUAL (WIP) por definição de etapa: quantas tarefas abertas estão nela, há quanto tempo está a mais antiga NA ETAPA e em que estados. Idade na etapa ≠ idade no estado: devolver a
 * tarefa à etapa anterior recomeça a contagem. Quando a medição começou com a tarefa já na etapa, a idade real pode ser maior (tooltip) — informação, não erro.
 */
export function TrafegoFilaTabela({ linhas }: { linhas: LinhaFila[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-line bg-surface-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-fg-subtle">
            <tr>
              <th className="px-3 py-2.5">Etapa</th>
              <th className="px-3 py-2.5 text-right">WIP</th>
              <th className="px-3 py-2.5 text-right" title="Há quanto tempo a tarefa mais antiga está nesta etapa">
                Mais antiga há
              </th>
              <th className="px-3 py-2.5">Estados atuais</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.chave} className="border-b border-line last:border-0 hover:bg-surface-hover">
                <td className="max-w-[16rem] px-3 py-2.5 align-top">
                  <p className="font-medium text-fg">{linha.etapa}</p>
                  <p className="text-xs text-fg-subtle">{linha.departamentos}</p>
                </td>
                <td className="px-3 py-2.5 text-right align-top font-mono tabular-nums text-fg">{linha.wip}</td>
                <td className="px-3 py-2.5 text-right align-top" title={`No estado atual há ${linha.idadeEstadoMaisAntigo} (a mais antiga neste estado)`}>
                  <span className="inline-flex items-center justify-end gap-1 font-mono tabular-nums text-fg">
                    {linha.truncada && (
                      <span title={TEXTO_TRUNCADA} aria-label={TEXTO_TRUNCADA} className="text-fg-subtle">
                        <Info className="h-3.5 w-3.5" aria-hidden />
                      </span>
                    )}
                    {linha.truncada ? `≥ ${linha.maisAntigaHa}` : linha.maisAntigaHa}
                  </span>
                </td>
                <td className="px-3 py-2.5 align-top">
                  <div className="flex flex-wrap gap-1.5">
                    {linha.estados.map((estado) => (
                      <Badge key={estado.id} tone={TOM_ESTADO[estado.id]}>
                        {estado.n} {estado.rotulo}
                      </Badge>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
