"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Ban, Hourglass, Layers } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { listDiretorioClientes, listDiretorioProjetos, type ClienteDiretorioItem, type ProjetoDiretorioItem } from "@/lib/api-backend";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import {
  PERIODOS_GARGALOS,
  PERIODO_GARGALOS_PADRAO,
  TEXTO_SEM_DADOS_SUFICIENTES,
  TEXTO_VAZIO_FILA,
  TEXTO_VAZIO_GARGALOS,
  avisoCobertura,
  avisoFilaSemEtapa,
  formatarDataCurta,
  gargalosVazio,
  intervaloDoPeriodo,
  linhasDaFila,
  linhasDeGargalo,
  mediaComAmostra,
  periodoGargalosDaUrl,
  type PeriodoGargalosId,
} from "@/lib/trafego-operacional";
import { useFiltrosNaUrl } from "@/lib/useFiltrosNaUrl";
import type { ParametrosGargalosOperacionais } from "@/types/trafego-operacional";
import { BotaoAtualizar, TrafegoAvisoAtualizacao, TrafegoErroLocal, TrafegoSkeleton } from "./TrafegoEstados";
import { TrafegoFilaTabela } from "./TrafegoFilaTabela";
import { TrafegoGargalosFiltros } from "./TrafegoGargalosFiltros";
import { TrafegoGargalosTabela } from "./TrafegoGargalosTabela";
import { useTrafegoGargalos } from "./useTrafegoOperacional";

// Parâmetros de URL próprios (prefixo `g`): não colidem com o `periodo`/filtros avançados da visão "Tempo pessoal".
const P_PERIODO = "gperiodo";
const P_DEPARTAMENTO = "gdepartamento";
const P_CLIENTE = "gcliente";
const P_PROJETO = "gprojeto";

function Resumo({ icone, titulo, valor, ajuda }: { icone: ReactNode; titulo: string; valor: number; ajuda: string }) {
  return (
    <li className="flex items-center gap-3 rounded-xl border border-line bg-surface px-3.5 py-3 shadow-sm">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-fg-muted dark:bg-zinc-800">{icone}</span>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{titulo}</p>
        <p className="text-xl font-semibold tabular-nums leading-tight text-fg">{valor}</p>
        <p className="text-xs text-fg-subtle">{ajuda}</p>
      </div>
    </li>
  );
}

/**
 * GARGALOS — "onde o fluxo está travando?". UMA requisição principal (`/trafego/operacional/gargalos`), refeita ao entrar na aba, ao mudar filtro e no botão Atualizar (sem polling).
 * As opções de cliente/projeto/departamento são os diretórios que o app já usa. Tempo operacional ≠ pessoal: tudo aqui é tempo das TAREFAS em cada estado.
 */
export function TrafegoGargalosVisao({ etapa, onLimparEtapa }: { etapa: { id: string; nome: string } | null; onLimparEtapa: () => void }) {
  const { param, definirParam } = useFiltrosNaUrl([], true);
  const periodo: PeriodoGargalosId = periodoGargalosDaUrl(param(P_PERIODO));
  const departamentoId = param(P_DEPARTAMENTO) ?? "";
  const clienteId = param(P_CLIENTE) ?? "";
  const projetoId = param(P_PROJETO) ?? "";

  const { departamentos } = useDiretorioDepartamentos();
  const [clientes, setClientes] = useState<ClienteDiretorioItem[]>([]);
  const [projetos, setProjetos] = useState<ProjetoDiretorioItem[]>([]);
  const [versao, setVersao] = useState(0);

  // Opções de filtro: diretórios carregados uma vez. Falha aqui não derruba a tela (os filtros ficam sem opções).
  useEffect(() => {
    let cancelado = false;
    listDiretorioClientes()
      .then((lista) => !cancelado && setClientes(lista))
      .catch(() => {});
    listDiretorioProjetos()
      .then((lista) => !cancelado && setProjetos(lista))
      .catch(() => {});
    return () => {
      cancelado = true;
    };
  }, []);

  // O período é "os últimos N dias até agora": recalculado só quando um filtro muda ou em Atualizar — nunca a cada render (o fim mudaria a chave da consulta).
  const parametros = useMemo<ParametrosGargalosOperacionais>(
    () => ({
      ...intervaloDoPeriodo(periodo, new Date()),
      departamentoId: departamentoId || null,
      clienteId: clienteId || null,
      projetoId: projetoId || null,
      workflowEtapaId: etapa?.id ?? null,
    }),
    // `versao` força um período novo ao clicar em Atualizar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [periodo, departamentoId, clienteId, projetoId, etapa?.id, versao],
  );
  const estado = useTrafegoGargalos(parametros);
  const { dados, carregando, atualizando, erro } = estado;
  const atualizar = () => setVersao((v) => v + 1);

  const filtrosAtivos = Boolean(departamentoId || clienteId || projetoId || etapa);
  const cobertura = dados ? avisoCobertura(dados, (iso) => formatarDataCurta(iso)) : null;
  const rotuloPeriodo = PERIODOS_GARGALOS.find((p) => p.id === periodo)?.label ?? "";

  const linhasTempo = dados ? linhasDeGargalo(dados.etapas, dados.fila) : [];
  const linhasFila = dados ? linhasDaFila(dados.fila) : [];
  const semEtapa = dados?.semEtapa;
  const avisoFila = dados ? avisoFilaSemEtapa(dados.filaSemEtapa) : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-fg-muted">Onde as tarefas passam mais tempo e onde a fila se acumula.</p>
        <BotaoAtualizar onClick={atualizar} atualizando={atualizando} />
      </div>

      <TrafegoGargalosFiltros
        periodo={periodo}
        onPeriodo={(proximo) => definirParam(P_PERIODO, proximo === PERIODO_GARGALOS_PADRAO ? null : proximo)}
        departamentoId={departamentoId}
        onDepartamento={(id) => definirParam(P_DEPARTAMENTO, id || null)}
        departamentos={departamentos.filter((d) => d.status === "ativo").map((d) => ({ value: d.id, label: d.nome }))}
        clienteId={clienteId}
        onCliente={(id) => definirParam(P_CLIENTE, id || null)}
        clientes={clientes.filter((c) => c.status === "ativo").map((c) => ({ value: c.id, label: c.nome }))}
        projetoId={projetoId}
        onProjeto={(id) => definirParam(P_PROJETO, id || null)}
        projetos={projetos.map((p) => ({ value: p.id, label: p.nome }))}
        etapa={etapa}
        onLimparEtapa={onLimparEtapa}
      />

      {carregando && dados === null ? (
        <TrafegoSkeleton kpis={0} linhas={5} />
      ) : dados === null ? (
        <TrafegoErroLocal mensagem={erro ?? "Não foi possível carregar os gargalos."} onTentarNovamente={atualizar} />
      ) : (
        <>
          {erro && <TrafegoAvisoAtualizacao mensagem={erro} onTentarNovamente={atualizar} />}
          {cobertura && (
            <p role="note" className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs text-fg-muted">
              {cobertura}
            </p>
          )}

          <ul aria-label="Situação atual" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Resumo icone={<Ban size={16} />} titulo="Bloqueadas agora" valor={dados.atual.bloqueadas} ajuda="tarefas neste estado" />
            <Resumo icone={<Hourglass size={16} />} titulo="Aguardando cliente agora" valor={dados.atual.aguardandoCliente} ajuda="tarefas neste estado" />
            <Resumo icone={<Layers size={16} />} titulo="WIP total" valor={dados.atual.wip} ajuda="tarefas abertas no fluxo" />
          </ul>

          <section aria-label="Tempo por etapa" className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-fg">Tempo por etapa</h3>
                <p className="text-xs text-fg-subtle">{rotuloPeriodo}</p>
              </div>
              {dados.etapasTotal > linhasTempo.length && <Badge tone="neutral">{`${linhasTempo.length} de ${dados.etapasTotal}`}</Badge>}
            </div>
            {gargalosVazio(dados) ? (
              <EmptyState title={filtrosAtivos ? TEXTO_SEM_DADOS_SUFICIENTES : TEXTO_VAZIO_GARGALOS} description="Os intervalos operacionais começam a ser medidos a partir da data indicada acima." />
            ) : (
              <>
                {linhasTempo.length > 0 ? <TrafegoGargalosTabela linhas={linhasTempo} /> : <p className="text-sm text-fg-subtle">Nenhuma etapa com tempo medido no período.</p>}
                {semEtapa && semEtapa.n > 0 && (
                  <p className="mt-3 text-xs text-fg-subtle">
                    Tarefas sem etapa (sem workflow ou com workflow concluído): {semEtapa.n} {semEtapa.n === 1 ? "ocorrência" : "ocorrências"} · tempo em execução médio{" "}
                    {mediaComAmostra(semEtapa.tempoExecucaoMedioSegundos, semEtapa.nExecucao).valor} ({mediaComAmostra(semEtapa.tempoExecucaoMedioSegundos, semEtapa.nExecucao).amostra}).
                  </p>
                )}
              </>
            )}
          </section>

          <section aria-label="Fila atual" className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-fg">Fila atual por etapa</h3>
                <p className="text-xs text-fg-subtle">Tarefas abertas agora (independe do período).</p>
              </div>
              {dados.filaTotal > linhasFila.length && <Badge tone="neutral">{`${linhasFila.length} de ${dados.filaTotal}`}</Badge>}
            </div>
            {linhasFila.length === 0 ? <EmptyState title={filtrosAtivos ? TEXTO_SEM_DADOS_SUFICIENTES : TEXTO_VAZIO_FILA} description="Tarefas abertas aparecem aqui assim que entram numa etapa." /> : <TrafegoFilaTabela linhas={linhasFila} />}
            {avisoFila && <p className="mt-3 text-xs text-fg-subtle">{avisoFila}</p>}
          </section>
        </>
      )}
    </div>
  );
}
