"use client";

import { useCallback, useEffect, useState } from "react";
import { getCargaTrafegoSessoes, getIndicadoresTrafegoSessoes, getResumoTrafegoSessoes, listSessoesTrabalho } from "@/lib/api";
import { getDemandasPorIds, getResumoOperacional, listDiretorioDemandas, type ResumoOperacional } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { podeAcessarCentralTrafego } from "@/lib/escopo-operacional";
import { cargaComRelogio, filterSessoes, periodoParaDataInicio, resumoDeIndicadores } from "@/lib/trafego";
import { useNow } from "@/lib/useNow";
import type { DemandaDiretorio } from "@/types/demanda";
import type { SessaoTrabalho } from "@/types/sessao-trabalho";
import type { TrafegoCarga, TrafegoFiltersState, TrafegoIndicadores } from "@/types/trafego";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { TempoOperacionalCard } from "./TempoOperacionalCard";
import { TrafegoAgoraTable } from "./TrafegoAgoraTable";
import { TrafegoCargaDepartamentos } from "./TrafegoCargaDepartamentos";
import { TrafegoCargaEquipes } from "./TrafegoCargaEquipes";
import { TrafegoCargaUsuarios } from "./TrafegoCargaUsuarios";
import { TrafegoFilters } from "./TrafegoFilters";
import { TrafegoHeader } from "./TrafegoHeader";
import { TrafegoIndicadoresDemandas } from "./TrafegoIndicadoresDemandas";
import { TrafegoIniciarSessao } from "./TrafegoIniciarSessao";
import { TrafegoResumoCards } from "./TrafegoResumoCards";

const initialFilters: TrafegoFiltersState = {
  usuarioIds: [],
  departamentoIds: [],
  demandaQuery: "",
  status: "todos",
  periodo: "24h",
};

export function TrafegoView() {
  const { usuarioAtual } = useAppData();
  const { usuarios } = useDiretorioUsuarios();
  const { departamentos } = useDiretorioDepartamentos();
  const [filters, setFilters] = useState<TrafegoFiltersState>(initialFilters);
  const [sessoesAtivas, setSessoesAtivas] = useState<SessaoTrabalho[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  // D2-C — diretório para vincular uma sessão NOVA: semântica de `/diretorio` (não
  // arquivada), carregado uma vez, independente de filtro/período.
  const [diretorioNovaSessao, setDiretorioNovaSessao] = useState<DemandaDiretorio[]>([]);
  // D2-C — diretório para resolver o NOME de sessões já carregadas (ativas + encerradas):
  // semântica de `GET /demandas/{id}` (arquivada incluída), resolvido em lote a partir dos
  // `demandaId` realmente presentes nas sessões — nunca mais `AppDataContext.demandas`.
  const [diretorioHistorico, setDiretorioHistorico] = useState<DemandaDiretorio[]>([]);
  // D2-D3A — indicadores baseados em Demanda, agregados no servidor sobre o universo
  // INTEGRAL permitido (admin/gestor via `require_admin_or_gestor`, nunca mais
  // `AppDataContext.demandas`). `resumoOperacional === null` distingue "carregando" de
  // "zero confirmado" — nunca fabricado no `TrafegoIndicadoresDemandas`.
  const [resumoOperacional, setResumoOperacional] = useState<ResumoOperacional | null>(null);
  const [erroResumoOperacional, setErroResumoOperacional] = useState<string | null>(null);
  // D2-D3B — "Horas executadas", agregado no servidor sobre o universo INTEGRAL de
  // SessaoTrabalho (sem cap de 100) — nunca mais `horasExecutadasPorEscopo(sessoes, {})`.
  // Estado independente do resumo de Demandas acima: falha de um não afeta o outro.
  // `horasExecutadas === null` distingue "carregando" de "zero confirmado".
  const [horasExecutadas, setHorasExecutadas] = useState<number | null>(null);
  const [erroHorasExecutadas, setErroHorasExecutadas] = useState<string | null>(null);
  // D2-D3C1 — métricas de `TrafegoResumoCards`/`TempoOperacionalCard`, agregadas no servidor
  // (`/sessoes-trabalho/trafego/indicadores`) sobre o universo INTEGRAL e já com TODOS os filtros
  // da tela — nunca mais derivadas de `sessoesAtivas`/`sessoesEncerradas` (limit=100). Estado
  // independente das listas: falha de um lado não derruba o outro. `indicadores === null`
  // distingue "carregando" de "zero confirmado". `recebidoEm` ancora o relógio das sessões
  // ativas entre dois fetches (ver `resumoDeIndicadores`).
  const [indicadores, setIndicadores] = useState<{ dados: TrafegoIndicadores; recebidoEm: number } | null>(null);
  const [erroIndicadores, setErroIndicadores] = useState<string | null>(null);
  // D2-D3C2 — cargas por usuário/departamento/equipe: agregadas no servidor sobre TODAS as ativas
  // (nunca agrupadas aqui a partir de `sessoesAtivas`, que é a lista de 100). Só usuários,
  // departamentos e busca de demanda as afetam — período e status nunca afetaram. Mesmo contrato
  // de estados dos indicadores acima (`null` = carregando, erro independente, `recebidoEm`
  // ancora o relógio das sessões ativas).
  const [carga, setCarga] = useState<{ dados: TrafegoCarga; recebidoEm: number } | null>(null);
  const [erroCarga, setErroCarga] = useState<string | null>(null);
  // Incrementado por `atualizar` (botão Atualizar, iniciar/fechar sessão): refaz indicadores E carga.
  const [versaoIndicadores, setVersaoIndicadores] = useState(0);
  const now = useNow(1000);

  // Só as sessões ATIVAS: `TrafegoAgoraTable` (D3C3 ainda não migrada) é o único consumidor da
  // lista. A lista de ENCERRADAS saiu em D2-D3C2 — depois que resumo, tempo operacional e as três
  // cargas passaram a vir do servidor, nada mais a lia (só alimentava a resolução de nomes).
  const carregar = useCallback(async () => {
    setLoading(true);
    setErro(null);
    try {
      setSessoesAtivas(await listSessoesTrabalho({ status: "ativa" }));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível conectar à API (http://localhost:8010).");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => {
      void carregar();
    }, 0);
    return () => clearTimeout(timeout);
  }, [carregar]);

  // D2-D3A — resumo operacional de Demandas, refeito a cada troca de período (o servidor
  // não recebe filtro nenhum além de `periodoInicio`, então trocar usuário/departamento/
  // status/busca na UI não precisa refetch — só o período afeta `recebidas`/
  // `concluidasNoPeriodo`). `cancelado` evita que uma resposta de um período antigo (troca
  // rápida hoje → 24h → 7d) sobrescreva a mais nova.
  useEffect(() => {
    let cancelado = false;
    getResumoOperacional(periodoParaDataInicio[filters.periodo]())
      .then((resultado) => {
        if (!cancelado) {
          setResumoOperacional(resultado);
          setErroResumoOperacional(null);
        }
      })
      .catch((error) => {
        if (!cancelado) {
          setErroResumoOperacional(error instanceof Error ? error.message : "Não foi possível carregar os indicadores.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [filters.periodo]);

  // D2-D3B — "Horas executadas", refeito a cada troca de período (mesma dependência de
  // `resumoOperacional` acima — o servidor só recebe `periodoInicio`). `cancelado` evita que
  // uma resposta de um período antigo sobrescreva a mais nova.
  useEffect(() => {
    let cancelado = false;
    getResumoTrafegoSessoes(periodoParaDataInicio[filters.periodo]())
      .then((resultado) => {
        if (!cancelado) {
          setHorasExecutadas(resultado.horasExecutadas);
          setErroHorasExecutadas(null);
        }
      })
      .catch((error) => {
        if (!cancelado) {
          setErroHorasExecutadas(error instanceof Error ? error.message : "Não foi possível carregar as horas executadas.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [filters.periodo]);

  // D2-D3C1 — indicadores, refeitos quando QUALQUER filtro muda (período, status, usuários,
  // departamentos, busca de demanda) ou quando uma sessão é aberta/fechada/atualizada
  // (`versaoIndicadores`). Debounce curto por causa da busca digitada. `cancelado` evita que uma
  // resposta antiga (troca rápida de filtro) sobrescreva a mais nova.
  useEffect(() => {
    let cancelado = false;
    const timeout = setTimeout(() => {
      getIndicadoresTrafegoSessoes({
        periodoInicio: periodoParaDataInicio[filters.periodo](),
        status: filters.status,
        usuarioIds: filters.usuarioIds,
        departamentoIds: filters.departamentoIds,
        demandaQuery: filters.demandaQuery,
      })
        .then((dados) => {
          if (cancelado) return;
          setIndicadores({ dados, recebidoEm: Date.now() });
          setErroIndicadores(null);
        })
        .catch((error) => {
          if (cancelado) return;
          setErroIndicadores(error instanceof Error ? error.message : "Não foi possível carregar os indicadores.");
        });
    }, 250);
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
  }, [filters.periodo, filters.status, filters.usuarioIds, filters.departamentoIds, filters.demandaQuery, versaoIndicadores]);

  // D2-D3C2 — carga, refeita quando usuários, departamentos ou a busca de demanda mudam, ou em
  // `atualizar`. NÃO depende de período/status (nunca afetaram os rankings). Debounce e
  // `cancelado` pelas mesmas razões do efeito dos indicadores.
  useEffect(() => {
    let cancelado = false;
    const timeout = setTimeout(() => {
      getCargaTrafegoSessoes({
        usuarioIds: filters.usuarioIds,
        departamentoIds: filters.departamentoIds,
        demandaQuery: filters.demandaQuery,
      })
        .then((dados) => {
          if (cancelado) return;
          setCarga({ dados, recebidoEm: Date.now() });
          setErroCarga(null);
        })
        .catch((error) => {
          if (cancelado) return;
          setErroCarga(error instanceof Error ? error.message : "Não foi possível carregar a carga.");
        });
    }, 250);
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
  }, [filters.usuarioIds, filters.departamentoIds, filters.demandaQuery, versaoIndicadores]);

  // Atualização completa: listas + indicadores + carga. Usada pelo botão de refresh e por toda ação que
  // muda sessões (iniciar, fechar) — os indicadores não podem ficar para trás da lista.
  const atualizar = useCallback(() => {
    setVersaoIndicadores((versao) => versao + 1);
    void carregar();
  }, [carregar]);

  // D2-C — diretório de vínculo (autocomplete de "Iniciar sessão"): não arquivada, escopo
  // padrão da listagem, carregado uma vez — não depende de filtro/período de sessões.
  useEffect(() => {
    let cancelado = false;
    listDiretorioDemandas()
      .then((diretorio) => {
        if (!cancelado) setDiretorioNovaSessao(diretorio);
      })
      .catch(() => {
        // Falha aqui não pode derrubar a tela — só o seletor de nova sessão fica vazio.
      });
    return () => {
      cancelado = true;
    };
  }, []);

  // D2-C — diretório histórico: extrai os `demandaId` realmente presentes nas sessões
  // carregadas (ativas, deduplicado) e resolve em lote via `/demandas/por-ids`
  // (arquivada incluída). `cancelado` evita que um lote antigo, ainda em voo quando o
  // usuário troca o período/filtro e novas sessões chegam, sobrescreva o diretório mais
  // novo.
  useEffect(() => {
    let cancelado = false;
    const idsUnicos = Array.from(new Set(sessoesAtivas.map((sessao) => sessao.demandaId)));
    // Sem sessões, não há `demandaId` pra resolver — nenhuma linha vai consultar o
    // diretório mesmo, então não há necessidade de zerar o estado (e fazer isso aqui
    // dispararia setState síncrono no corpo do efeito).
    if (idsUnicos.length === 0) return;
    getDemandasPorIds(idsUnicos)
      .then((diretorio) => {
        if (!cancelado) setDiretorioHistorico(diretorio);
      })
      .catch(() => {
        // Falha aqui degrada para o fallback de `resolveTrafegoDemandaNome` (mostra o id).
      });
    return () => {
      cancelado = true;
    };
  }, [sessoesAtivas]);

  const ativasFiltradas = filterSessoes(sessoesAtivas, filters, diretorioHistorico);
  const resumo = indicadores
    ? resumoDeIndicadores(indicadores.dados, (now.getTime() - indicadores.recebidoEm) / 1000)
    : null;
  const deltaCarga = carga ? (now.getTime() - carga.recebidoEm) / 1000 : 0;
  const cargaUsuarios = carga ? cargaComRelogio(carga.dados.usuarios, deltaCarga) : null;
  const cargaDepartamentos = carga ? cargaComRelogio(carga.dados.departamentos, deltaCarga) : null;
  const cargaEquipes = carga ? cargaComRelogio(carga.dados.equipes, deltaCarga) : null;

  if (!usuarioAtual) return null;

  if (!podeAcessarCentralTrafego(usuarioAtual)) {
    return (
      <div className="flex flex-col gap-6">
        <TrafegoHeader onRefresh={atualizar} refreshing={loading} />
        <AcessoNegado
          titulo="Central de Tráfego restrita à gestão autorizada"
          descricao="Esta visão reúne carga, capacidade e demandas de toda a operação — disponível apenas para perfis de gestão autorizados nesta fase."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <TrafegoHeader onRefresh={atualizar} refreshing={loading} />
      <TrafegoIniciarSessao onCreated={atualizar} demandas={diretorioNovaSessao} />
      <TrafegoFilters filters={filters} onChange={setFilters} usuarios={usuarios} departamentos={departamentos} />

      {erroIndicadores && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erroIndicadores}
        </div>
      )}
      <TrafegoResumoCards resumo={resumo} erro={erroIndicadores} />
      <TempoOperacionalCard resumo={resumo} erro={erroIndicadores} />

      {erro ? (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erro}
        </div>
      ) : (
        <>
          <TrafegoIndicadoresDemandas
            resumo={resumoOperacional}
            erro={erroResumoOperacional}
            horasExecutadas={horasExecutadas}
            erroHorasExecutadas={erroHorasExecutadas}
          />
          <TrafegoAgoraTable
            sessoes={ativasFiltradas}
            now={now}
            onChanged={atualizar}
            diretorioDemandas={diretorioHistorico}
            diretorioUsuarios={usuarios}
            diretorioDepartamentos={departamentos}
          />
        </>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <TrafegoCargaUsuarios cargas={cargaUsuarios} erro={erroCarga} />
        <TrafegoCargaDepartamentos cargas={cargaDepartamentos} erro={erroCarga} />
        <TrafegoCargaEquipes cargas={cargaEquipes} erro={erroCarga} />
      </div>
    </div>
  );
}
