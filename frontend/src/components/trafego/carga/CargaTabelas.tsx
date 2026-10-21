import clsx from "clsx";
import { Badge } from "@/components/ui/Badge";
import type { LinhaDepartamento, LinhaPessoa } from "@/lib/trafego-carga";
import { CapacityBar } from "./CapacityBar";

const CABECALHO = "border-b border-line bg-surface-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-fg-subtle";
const NUM = "px-3 py-2.5 text-right align-middle font-mono tabular-nums";

/** "A planejar": minutos conhecidos fora da ocupação + aviso de etapas sem estimativa (sempre visível quando > 0). */
function CelulaAPlanejar({ minutos, semEstimativa }: { minutos: string | null; semEstimativa: number }) {
  if (minutos === null && semEstimativa === 0) return <span className="block text-right text-fg-subtle">—</span>;
  return (
    <div className="flex flex-col items-end gap-0.5">
      {minutos !== null && <span className="font-mono tabular-nums text-fg-muted">{minutos}</span>}
      {semEstimativa > 0 && <Badge tone="amber">{semEstimativa === 1 ? "1 sem estimativa" : `${semEstimativa} sem estimativa`}</Badge>}
    </div>
  );
}

function Disponivel({ texto, negativo }: { texto: string; negativo: boolean }) {
  return <span className={clsx(negativo ? "font-semibold text-red-600 dark:text-red-400" : "text-fg")}>{texto}</span>;
}

/**
 * PESSOAS: capacidade alocável da semana × planejado (etapas estimadas e com janela). Ordem do servidor (alfabética) — sem ranking, sem "melhor/pior". O saldo negativo aparece como é ("-3h").
 * A linha inteira abre o detalhe (UMA chamada ao abrir; nada é carregado antes).
 */
export function CargaPeopleTable({ linhas, onAbrir }: { linhas: LinhaPessoa[]; onAbrir: (linha: LinhaPessoa) => void }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className={CABECALHO}>
            <tr>
              <th className="px-3 py-2.5">Pessoa</th>
              <th className="px-3 py-2.5">Departamento</th>
              <th className="px-3 py-2.5 text-right">Capacidade</th>
              <th className="px-3 py-2.5 text-right">Planejado</th>
              <th className="px-3 py-2.5 text-right">Disponível</th>
              <th className="px-3 py-2.5 text-right" title="Planejado ÷ capacidade alocável. Pode passar de 100%.">
                Ocupação
              </th>
              <th className="px-3 py-2.5 text-right" title="Etapas conhecidas que ainda não entram na ocupação (sem janela, janela incompleta, vencida ou sem dia útil) e etapas sem estimativa">
                A planejar
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.usuarioId} className="cursor-pointer border-b border-line last:border-0 hover:bg-surface-hover" onClick={() => onAbrir(linha)}>
                <td className="px-3 py-2.5 align-middle">
                  <button
                    type="button"
                    onClick={(evento) => {
                      evento.stopPropagation();
                      onAbrir(linha);
                    }}
                    className="rounded text-left font-medium text-fg hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    aria-label={`Ver etapas de ${linha.nome}`}
                  >
                    {linha.nome}
                  </button>
                  {linha.indicacoes.length > 0 && <p className="text-[11px] text-fg-subtle">{linha.indicacoes.join(" · ")}</p>}
                </td>
                <td className="px-3 py-2.5 align-middle text-fg-muted">{linha.departamento ?? <span className="text-fg-subtle">Sem departamento</span>}</td>
                <td className={NUM}>{linha.capacidade}</td>
                <td className={NUM}>{linha.planejado}</td>
                <td className={NUM}>
                  <Disponivel texto={linha.disponivel} negativo={linha.disponivelNegativo} />
                </td>
                <td className="px-3 py-2.5 align-middle">
                  <CapacityBar ocupacao={linha.ocupacao} />
                </td>
                <td className="px-3 py-2.5 align-middle">
                  <CelulaAPlanejar minutos={linha.aPlanejar} semEstimativa={linha.semEstimativa} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * DEPARTAMENTOS: "Planejado" é o total do departamento (pessoas + pool). "Pool sem pessoa" é o trabalho do departamento que ainda não tem responsável — um SUBCONJUNTO do planejado,
 * mostrado à parte só para ficar visível; nunca é somado de novo.
 */
export function CargaDepartmentsTable({ linhas, onAbrir }: { linhas: LinhaDepartamento[]; onAbrir: (linha: LinhaDepartamento) => void }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className={CABECALHO}>
            <tr>
              <th className="px-3 py-2.5">Departamento</th>
              <th className="px-3 py-2.5 text-right">Capacidade</th>
              <th className="px-3 py-2.5 text-right" title="Total do departamento: pessoas + pool">
                Planejado
              </th>
              <th className="px-3 py-2.5 text-right" title="Trabalho do departamento ainda sem pessoa responsável. Já está incluído no Planejado.">
                Pool sem pessoa
              </th>
              <th className="px-3 py-2.5 text-right">Disponível</th>
              <th className="px-3 py-2.5 text-right" title="Planejado ÷ capacidade alocável. Pode passar de 100%.">
                Ocupação
              </th>
              <th className="px-3 py-2.5 text-right" title="Etapas conhecidas que ainda não entram na ocupação e etapas sem estimativa">
                A planejar
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.departamentoId} className="cursor-pointer border-b border-line last:border-0 hover:bg-surface-hover" onClick={() => onAbrir(linha)}>
                <td className="px-3 py-2.5 align-middle">
                  <button
                    type="button"
                    onClick={(evento) => {
                      evento.stopPropagation();
                      onAbrir(linha);
                    }}
                    className="rounded text-left font-medium text-fg hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    aria-label={`Ver etapas de ${linha.nome}`}
                  >
                    {linha.nome}
                  </button>
                  <p className="text-xs text-fg-subtle">{linha.pessoas === 0 ? "Sem pessoas com capacidade" : linha.pessoas === 1 ? "1 pessoa" : `${linha.pessoas} pessoas`}</p>
                </td>
                <td className={NUM}>{linha.capacidade}</td>
                <td className={NUM}>{linha.planejado}</td>
                <td className={NUM}>{linha.pool ?? <span className="text-fg-subtle">—</span>}</td>
                <td className={NUM}>
                  <Disponivel texto={linha.disponivel} negativo={linha.disponivelNegativo} />
                </td>
                <td className="px-3 py-2.5 align-middle">
                  <CapacityBar ocupacao={linha.ocupacao} />
                </td>
                <td className="px-3 py-2.5 align-middle">
                  <CelulaAPlanejar minutos={linha.aPlanejar} semEstimativa={linha.semEstimativa} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
