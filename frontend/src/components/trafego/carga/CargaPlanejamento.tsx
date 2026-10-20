import type { ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import {
  baldesDeNaoPlanejado,
  formatarMinutos,
  itensOcultos,
  linhaDoItem,
  type PoolForaDaCapacidade,
} from "@/lib/trafego-carga";
import type { CargaSemanal, PendenciaCarga, PoolSemDepartamentoCarga } from "@/types/trafego-carga";
import { CargaItensTabela } from "./CargaItensTabela";

function Secao({ titulo, descricao, children }: { titulo: string; descricao: string; children: ReactNode }) {
  return (
    <section aria-label={titulo} className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="mb-3">
        <h3 className="text-base font-semibold text-fg">{titulo}</h3>
        <p className="text-xs text-fg-subtle">{descricao}</p>
      </div>
      {children}
    </section>
  );
}

function textoEtapas(n: number): string {
  return n === 1 ? "1 etapa" : `${n} etapas`;
}

/**
 * "Precisa de planejamento": etapas FORA da ocupação (sem janela / janela incompleta). Mostra quantidade e os minutos já CONHECIDOS (etapa sem estimativa não soma zero: vira o aviso âmbar).
 * Isto nunca se mistura com "Planejado". O contrato não lista as etapas deste balde; elas aparecem no detalhe de cada pessoa/departamento.
 */
export function CargaPrecisaDePlanejamento({ dados }: { dados: Pick<CargaSemanal, "naoPlanejado"> }) {
  const baldes = baldesDeNaoPlanejado(dados).filter((balde) => balde.etapas > 0);
  return (
    <Secao titulo="Precisa de planejamento" descricao="Etapas abertas que ainda não entram na ocupação por falta de janela planejada. Não são contadas em “Planejado”.">
      <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {baldes.map((balde) => (
          <li key={balde.id} className="rounded-xl border border-line bg-surface-2 px-3.5 py-3">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-medium text-fg">{balde.titulo}</p>
              <p className="text-sm font-semibold tabular-nums text-fg">{textoEtapas(balde.etapas)}</p>
            </div>
            <p className="mt-0.5 text-xs text-fg-subtle">{balde.ajuda}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-fg-muted">
              <span>
                Minutos conhecidos: <span className="font-mono tabular-nums text-fg">{balde.minutos}</span>
              </span>
              {balde.semEstimativa > 0 && <Badge tone="amber">{balde.semEstimativa === 1 ? "1 sem estimativa" : `${balde.semEstimativa} sem estimativa`}</Badge>}
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-fg-subtle">As etapas que têm responsável ou departamento aparecem no detalhe da pessoa ou do departamento, onde dá para planejar cada uma.</p>
    </Secao>
  );
}

function BlocoPendencia({ titulo, mensagem, pendencia, onAbrirTarefa }: { titulo: string; mensagem: string; pendencia: PendenciaCarga; onAbrirTarefa: (demandaId: string) => void }) {
  const ocultos = itensOcultos(pendencia.etapasCount, pendencia.itens);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-sm font-medium text-fg">{titulo}</p>
        <Badge tone="amber">{textoEtapas(pendencia.etapasCount)}</Badge>
        <span className="text-xs text-fg-subtle">{mensagem}</span>
        {pendencia.semEstimativaCount > 0 && <Badge tone="amber">{pendencia.semEstimativaCount === 1 ? "1 sem estimativa" : `${pendencia.semEstimativaCount} sem estimativa`}</Badge>}
      </div>
      <CargaItensTabela linhas={pendencia.itens.map(linhaDoItem)} mostrarParte={false} onAbrir={onAbrirTarefa} />
      {(pendencia.truncado || ocultos > 0) && <p className="text-xs text-fg-subtle">{`Mostrando ${pendencia.itens.length} de ${pendencia.etapasCount} etapas.`}</p>}
    </div>
  );
}

/** "Pendências de planejamento": conflitos que pedem ação do gestor. Nada é movido de semana: a carga NÃO é redistribuída visualmente. */
export function CargaPendencias({ dados, onAbrirTarefa }: { dados: Pick<CargaSemanal, "pendenciasPlanejamento">; onAbrirTarefa: (demandaId: string) => void }) {
  const { janelaVencida, semDiaUtil } = dados.pendenciasPlanejamento;
  return (
    <Secao titulo="Pendências de planejamento" descricao="Janelas que pedem ação. A carga destas etapas não entra na ocupação nem é movida para outra semana.">
      <div className="flex flex-col gap-5">
        {janelaVencida.etapasCount > 0 && <BlocoPendencia titulo="Janela vencida" mensagem="Precisa replanejar." pendencia={janelaVencida} onAbrirTarefa={onAbrirTarefa} />}
        {semDiaUtil.etapasCount > 0 && <BlocoPendencia titulo="Sem dia útil" mensagem="Janela sem capacidade disponível." pendencia={semDiaUtil} onAbrirTarefa={onAbrirTarefa} />}
      </div>
    </Secao>
  );
}

/**
 * Trabalho SEM destino de capacidade: pool sem departamento e pools de departamento sem pessoas. Fica à parte — diluir estes minutos na capacidade das pessoas esconderia justamente o problema
 * (planejamento sem um lugar correto de alocação).
 */
export function CargaForaDaCapacidade({ poolSemDepartamento, poolsSemCapacidade }: { poolSemDepartamento: PoolSemDepartamentoCarga | null; poolsSemCapacidade: PoolForaDaCapacidade[] }) {
  if (poolSemDepartamento === null && poolsSemCapacidade.length === 0) return null;
  return (
    <Secao titulo="Sem destino de capacidade" descricao="Trabalho que não tem pessoa nem departamento com capacidade para recebê-lo. Não entra na capacidade das pessoas.">
      <ul className="flex flex-col gap-3">
        {poolSemDepartamento && (
          <li className="rounded-xl border border-amber-200 bg-amber-50 px-3.5 py-3 text-sm dark:border-amber-500/30 dark:bg-amber-500/10">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-amber-900 dark:text-amber-200">Sem departamento</p>
              <p className="font-semibold tabular-nums text-amber-900 dark:text-amber-200">{textoEtapas(poolSemDepartamento.etapasCount)}</p>
            </div>
            <p className="mt-0.5 text-xs text-amber-800 dark:text-amber-300">Etapas sem responsável e sem departamento: ainda não há onde alocá-las. Atribua um departamento ou responsável na tarefa para que entrem na capacidade.</p>
            <dl className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-amber-900 dark:text-amber-200">
              {poolSemDepartamento.planejadoMin !== null && (
                <div>
                  <dt className="inline">Planejado conhecido: </dt>
                  <dd className="inline font-mono tabular-nums">{formatarMinutos(poolSemDepartamento.planejadoMin)}</dd>
                </div>
              )}
              <div>
                <dt className="inline">Minutos conhecidos fora da ocupação: </dt>
                <dd className="inline font-mono tabular-nums">{formatarMinutos(poolSemDepartamento.naoPlanejadoMin + poolSemDepartamento.pendenciasPlanejamentoMin)}</dd>
              </div>
              {poolSemDepartamento.semEstimativaCount > 0 && (
                <div>
                  <dt className="inline">Sem estimativa: </dt>
                  <dd className="inline font-mono tabular-nums">{poolSemDepartamento.semEstimativaCount}</dd>
                </div>
              )}
            </dl>
          </li>
        )}
        {poolsSemCapacidade.map((pool) => (
          <li key={pool.chave} className="rounded-xl border border-line bg-surface-2 px-3.5 py-3 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-fg">{pool.nome}</p>
              <p className="font-mono text-sm tabular-nums text-fg">{formatarMinutos(pool.planejadoMin)}</p>
            </div>
            <p className="mt-0.5 text-xs text-fg-subtle">Pool do departamento sem pessoas com capacidade: o trabalho existe, mas não há quem o receba.</p>
          </li>
        ))}
      </ul>
    </Secao>
  );
}
