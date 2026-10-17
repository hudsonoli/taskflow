import { ROTULO_TEMPO, TEXTO_AJUDA_TEMPO_OPERACIONAL, type CelulaTempo, type LinhaGargalo } from "@/lib/trafego-operacional";

/** Média com o denominador SEMPRE visível ("1h 24min" + "12 itens"); o total e o maior ficam no tooltip. */
function Celula({ celula, rotulo, mostrarMaior = false }: { celula: CelulaTempo; rotulo: string; mostrarMaior?: boolean }) {
  const vazio = celula.valor === "—";
  return (
    <td className="px-3 py-2.5 text-right align-top" title={vazio ? `${rotulo}: sem amostra no período` : `${rotulo} — total ${celula.total} · maior ${celula.maior}`}>
      {mostrarMaior ? (
        <span className="font-mono tabular-nums text-fg">{celula.maior}</span>
      ) : (
        <>
          <span className={vazio ? "text-fg-subtle" : "font-mono tabular-nums text-fg"}>{celula.valor}</span>
          {!vazio && <span className="block text-[11px] text-fg-subtle">{celula.amostra}</span>}
        </>
      )}
    </td>
  );
}

/**
 * Tempo operacional por DEFINIÇÃO de etapa no período (nome + tipo + departamentos). As colunas de tempo mostram a MÉDIA por ocorrência (Demanda × etapa) com o `n`; "Maior" é a maior
 * ocorrência em execução. São tempos do ESTADO das tarefas — não horas trabalhadas por pessoas.
 */
export function TrafegoGargalosTabela({ linhas }: { linhas: LinhaGargalo[] }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="border-b border-line bg-surface-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-fg-subtle">
            <tr>
              <th className="px-3 py-2.5">Etapa</th>
              <th className="px-3 py-2.5 text-right" title="Tarefas abertas hoje cuja etapa atual é esta">
                WIP
              </th>
              <th className="px-3 py-2.5 text-right" title={`${ROTULO_TEMPO.execucao}: média por ocorrência`}>
                Execução (média)
              </th>
              <th className="px-3 py-2.5 text-right" title={`${ROTULO_TEMPO.execucao}: maior ocorrência`}>
                Execução (maior)
              </th>
              <th className="px-3 py-2.5 text-right" title={`${ROTULO_TEMPO.pausado}: média por ocorrência`}>
                Pausado
              </th>
              <th className="px-3 py-2.5 text-right" title={`${ROTULO_TEMPO.bloqueado}: média por ocorrência`}>
                Bloqueado
              </th>
              <th className="px-3 py-2.5 text-right" title={`${ROTULO_TEMPO.aguardandoCliente}: média por ocorrência`}>
                Aguardando cliente
              </th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.chave} className="border-b border-line last:border-0 hover:bg-surface-hover">
                <td className="max-w-[16rem] px-3 py-2.5 align-top">
                  <p className="font-medium text-fg">{linha.etapa}</p>
                  <p className="text-xs text-fg-subtle">
                    {linha.departamentos}
                    {linha.tipo === "aprovacao" ? " · aprovação" : ""}
                  </p>
                </td>
                <td className="px-3 py-2.5 text-right align-top font-mono tabular-nums text-fg">{linha.wip}</td>
                <Celula celula={linha.execucao} rotulo={ROTULO_TEMPO.execucao} />
                <Celula celula={linha.execucao} rotulo={ROTULO_TEMPO.execucao} mostrarMaior />
                <Celula celula={linha.pausado} rotulo={ROTULO_TEMPO.pausado} />
                <Celula celula={linha.bloqueado} rotulo={ROTULO_TEMPO.bloqueado} />
                <Celula celula={linha.aguardandoCliente} rotulo={ROTULO_TEMPO.aguardandoCliente} />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-line bg-surface-2 px-3 py-2 text-xs text-fg-subtle">{TEXTO_AJUDA_TEMPO_OPERACIONAL}</p>
    </div>
  );
}
