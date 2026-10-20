import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { LinhaItem, SeloItem } from "@/lib/trafego-carga";

const TOM_SELO: Record<SeloItem["tom"], BadgeTone> = { neutro: "neutral", ambar: "amber", vermelho: "red" };

/**
 * Etapas que compõem um número (pendências e detalhe). Sem UUID, sem chave técnica, sem financeiro. "Janela" é planejamento — não é prazo. A ação "Planejar"/"Abrir tarefa" abre a Demanda
 * existente (mesmo mecanismo das Notificações), na aba onde a estimativa e a janela da etapa são editadas.
 * `mostrarParte` liga a coluna "Nesta semana" (só faz sentido no detalhe de um alvo).
 */
export function CargaItensTabela({ linhas, mostrarParte, onAbrir }: { linhas: LinhaItem[]; mostrarParte: boolean; onAbrir: (demandaId: string) => void }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="border-b border-line bg-surface-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-fg-subtle">
            <tr>
              <th className="px-3 py-2.5">Tarefa</th>
              <th className="px-3 py-2.5">Etapa</th>
              <th className="px-3 py-2.5 text-right">Estimativa</th>
              {mostrarParte && <th className="px-3 py-2.5 text-right">Nesta semana</th>}
              <th className="px-3 py-2.5" title="Janela planejada da etapa — planejamento, não prazo">
                Janela planejada
              </th>
              <th className="px-3 py-2.5">Estado</th>
              <th className="px-3 py-2.5">Origem</th>
              <th className="px-3 py-2.5 text-right">
                <span className="sr-only">Ação</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.chave} className="border-b border-line last:border-0 hover:bg-surface-hover">
                <td className="max-w-[18rem] px-3 py-2.5 align-top">
                  <p className="truncate font-medium text-fg" title={linha.demanda}>
                    {linha.demanda}
                  </p>
                  {(linha.cliente || linha.projeto) && <p className="truncate text-xs text-fg-subtle">{[linha.cliente, linha.projeto].filter(Boolean).join(" · ")}</p>}
                </td>
                <td className="px-3 py-2.5 align-top text-fg-muted">{linha.etapa}</td>
                <td className="px-3 py-2.5 text-right align-top font-mono tabular-nums text-fg">{linha.estimativa}</td>
                {mostrarParte && (
                  <td className="px-3 py-2.5 text-right align-top font-mono tabular-nums text-fg">
                    {linha.naSemana ?? <span className="text-fg-subtle">—</span>}
                    {linha.totalDaEtapaNaSemana && <span className="block font-sans text-[11px] text-fg-subtle">de {linha.totalDaEtapaNaSemana} na etapa</span>}
                  </td>
                )}
                <td className="whitespace-nowrap px-3 py-2.5 align-top text-fg-muted">{linha.janela}</td>
                <td className="px-3 py-2.5 align-top">
                  <div className="flex flex-wrap gap-1">
                    {linha.selos.map((selo) => (
                      <Badge key={selo.id} tone={TOM_SELO[selo.tom]}>
                        {selo.texto}
                      </Badge>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2.5 align-top text-fg-muted">
                  {linha.origem}
                  {linha.dividido && <span className="block text-xs text-fg-subtle">{linha.dividido}</span>}
                </td>
                <td className="px-3 py-2.5 text-right align-top">
                  <Button variant="ghost" onClick={() => onAbrir(linha.demandaId)}>
                    {linha.precisaPlanejar ? "Planejar" : "Abrir tarefa"}
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
