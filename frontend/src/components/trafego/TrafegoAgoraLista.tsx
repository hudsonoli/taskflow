import { Inbox } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { EmptyState } from "@/components/ui/EmptyState";
import { TEXTO_RESPONSAVEIS, TEXTO_TEMPO_NO_ESTADO, TEXTO_VAZIO_AGORA, linhaDoAgora } from "@/lib/trafego-operacional";
import type { TrafegoOperacionalAgora } from "@/types/trafego-operacional";

/**
 * "Em execução agora": tarefas NESTE ESTADO. A coluna de tempo é o tempo da TAREFA no estado atual (tooltip explícito) — nunca horas de alguém — e os responsáveis são a atribuição
 * atual, não quem está trabalhando. Sem polling por segundo: `agoraMs` avança a cada 30 s a partir da idade que o servidor mediu.
 */
export function TrafegoAgoraLista({
  dados,
  recebidoEmMs,
  agoraMs,
  onVerGargalosDaEtapa,
}: {
  dados: TrafegoOperacionalAgora;
  recebidoEmMs: number;
  agoraMs: number;
  onVerGargalosDaEtapa?: (etapa: { id: string; nome: string }) => void;
}) {
  const linhas = dados.emExecucao.map((demanda) => linhaDoAgora(demanda, { fuso: dados.fusoEmpresa, recebidoEmMs, agoraMs }));

  return (
    <section aria-label="Em execução agora" className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-fg">Em execução agora</h3>
          <p className="text-xs text-fg-subtle">Tarefas neste estado, as mais críticas primeiro.</p>
        </div>
        <Badge tone="blue">{dados.emExecucaoTotal}</Badge>
      </div>

      {linhas.length === 0 ? (
        <EmptyState title={TEXTO_VAZIO_AGORA} description="Os demais indicadores continuam acima." icon={<Inbox size={16} />} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-line">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="border-b border-line bg-surface-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-fg-subtle">
                <tr>
                  <th className="px-4 py-2.5">Demanda</th>
                  <th className="px-4 py-2.5">Cliente / Projeto</th>
                  <th className="px-4 py-2.5">Etapa atual</th>
                  <th className="px-4 py-2.5" title={TEXTO_RESPONSAVEIS}>
                    Responsáveis
                  </th>
                  <th className="px-4 py-2.5 text-right" title={TEXTO_TEMPO_NO_ESTADO}>
                    Há quanto tempo
                  </th>
                  <th className="px-4 py-2.5">Prazo</th>
                </tr>
              </thead>
              <tbody>
                {linhas.map((linha) => (
                  <tr key={linha.demandaId} className="border-b border-line align-top last:border-0 hover:bg-surface-hover">
                    <td className="max-w-[18rem] px-4 py-2.5">
                      <p className="truncate font-medium text-fg" title={linha.titulo}>
                        {linha.titulo}
                      </p>
                      <p className="text-xs text-fg-subtle">{linha.identificador}</p>
                    </td>
                    <td className="max-w-[14rem] px-4 py-2.5">
                      {linha.cliente ? <p className="truncate text-fg">{linha.cliente}</p> : <p className="text-fg-subtle">—</p>}
                      {linha.projeto && <p className="truncate text-xs text-fg-subtle">{linha.projeto}</p>}
                    </td>
                    <td className="px-4 py-2.5">
                      {linha.etapa ? (
                        <>
                          <p className="text-fg">{linha.etapa.nome}</p>
                          <p className="text-xs text-fg-subtle">{linha.etapa.departamentos}</p>
                          {onVerGargalosDaEtapa && (
                            <button
                              type="button"
                              onClick={() => linha.etapa && onVerGargalosDaEtapa({ id: linha.etapa.id, nome: linha.etapa.nome })}
                              className="mt-0.5 text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                            >
                              Ver gargalos desta etapa
                            </button>
                          )}
                        </>
                      ) : (
                        <p className="text-fg-subtle">Sem etapa atual</p>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <AvatarStack
                        pessoas={linha.responsaveis.map((responsavel) => ({ id: responsavel.id, nome: responsavel.nome }))}
                        size="h-6 w-6"
                        max={3}
                        emptyLabel="Sem responsável"
                      />
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-sm tabular-nums text-fg" title={TEXTO_TEMPO_NO_ESTADO}>
                      {linha.tempoNoEstado}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2.5">
                      <span className={linha.atrasada ? "font-medium text-red-700 dark:text-red-400" : "text-fg-muted"}>{linha.prazo}</span>
                      {linha.atrasada && (
                        <span className="ml-1.5">
                          <Badge tone="red">Atrasada</Badge>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {dados.truncado && (
        <p className="mt-2 text-xs text-fg-subtle">
          Mostrando {linhas.length} de {dados.emExecucaoTotal}.
        </p>
      )}
    </section>
  );
}
