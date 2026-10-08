"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getAgoraTrafegoSessoes, getCargaTrafegoSessoes, getIndicadoresTrafegoSessoes, getResumoTrafegoSessoes } from "@/lib/api";
import {
  getResumoOperacional,
  listDiretorioClientes,
  listDiretorioDemandas,
  listDiretorioProjetos,
  type ClienteDiretorioItem,
  type ProjetoDiretorioItem,
  type ResumoOperacional,
} from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { podeAcessarCentralTrafego } from "@/lib/escopo-operacional";
import { filtrosTrafegoParaApi } from "@/lib/filtros-trafego";
import { cargaComRelogio, periodoParaDataInicio, resumoDeIndicadores } from "@/lib/trafego";
import { useFiltrosNaUrl } from "@/lib/useFiltrosNaUrl";
import { useNow } from "@/lib/useNow";
import type { DemandaDiretorio } from "@/types/demanda";
import type { TrafegoAgoraLinha, TrafegoCarga, TrafegoFiltersState, TrafegoIndicadores } from "@/types/trafego";
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
import { useDefinicoesFiltrosTrafego } from "./useDefinicoesFiltrosTrafego";

// D2-D3C3 — tamanho da página de "Quem está trabalhando agora" (+ "Carregar mais").
const TAMANHO_PAGINA_AGORA = 50;

const PERIODOS_VALIDOS: ReadonlyArray<TrafegoFiltersState["periodo"]> = ["hoje", "24h", "7d", "30d"];
const PERIODO_PADRAO: TrafegoFiltersState["periodo"] = "24h";

/** Período vindo da URL: só os quatro valores conhecidos; qualquer outro volta ao padrão (nunca confia no parâmetro). */
function periodoDaUrl(valor: string | null): TrafegoFiltersState["periodo"] {
  return PERIODOS_VALIDOS.find((periodo) => periodo === valor) ?? PERIODO_PADRAO;
}

export function TrafegoView() {
  const { usuarioAtual } = useAppData();
  const { departamentos } = useDiretorioDepartamentos();
  // Filtros avançados + período + busca de Demanda vivem na URL (refresh, link compartilhado e "voltar" preservam a tela).
  // Cliente/projeto são diretórios carregados uma vez; o usuário é buscado no servidor pelo próprio filtro.
  const [clientes, setClientes] = useState<ClienteDiretorioItem[]>([]);
  const [projetos, setProjetos] = useState<ProjetoDiretorioItem[]>([]);
  const [diretoriosProntos, setDiretoriosProntos] = useState(false);
  const definicoesFiltros = useDefinicoesFiltrosTrafego({ departamentos, clientes, projetos, diretoriosProntos });
  const { filtros, definirFiltros, param, definirParam } = useFiltrosNaUrl(definicoesFiltros, true);
  const periodo = periodoDaUrl(param("periodo"));
  const demandaQuery = param("q") ?? "";
  // Atalhos de data ("hoje", "atrasado") viram intervalos aqui, uma vez por mudança de filtro (não a cada render).
  const filtrosApi = useMemo(() => filtrosTrafegoParaApi(filtros, new Date()), [filtros]);
  // D2-C — diretório para vincular uma sessão NOVA: semântica de `/diretorio` (não
  // arquivada), carregado uma vez, independente de filtro/período.
  const [diretorioNovaSessao, setDiretorioNovaSessao] = useState<DemandaDiretorio[]>([]);
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
  // D2-D3C3 — "Quem está trabalhando agora": listagem paginada no servidor (`/trafego/agora`), já com
  // nomes de usuário/departamento/Demanda — nunca mais a lista de 100 sessões nem diretórios do
  // cliente. `agora === null` é "carregando"; a falha da primeira página (`erroAgora`) e a do
  // "carregar mais" (`erroMaisAgora`) são separadas para um erro de página não apagar a tabela.
  // `chaveAgoraRef` identifica a consulta vigente (filtros + versão): resposta de uma consulta
  // anterior — inclusive um "carregar mais" em voo quando os filtros mudam — é descartada.
  const [agora, setAgora] = useState<{ linhas: TrafegoAgoraLinha[]; total: number } | null>(null);
  const [erroAgora, setErroAgora] = useState<string | null>(null);
  const [carregandoAgora, setCarregandoAgora] = useState(true);
  const [carregandoMaisAgora, setCarregandoMaisAgora] = useState(false);
  const [erroMaisAgora, setErroMaisAgora] = useState<string | null>(null);
  const chaveAgoraRef = useRef("");
  // Incrementado por `atualizar` (botão Atualizar, iniciar/fechar sessão): refaz indicadores,
  // carga E "agora" (primeira página).
  const [versaoIndicadores, setVersaoIndicadores] = useState(0);
  const now = useNow(1000);

  // D2-D3A — resumo operacional de Demandas, refeito a cada troca de período (o servidor
  // não recebe filtro nenhum além de `periodoInicio`, então trocar usuário/departamento/
  // status/busca na UI não precisa refetch — só o período afeta `recebidas`/
  // `concluidasNoPeriodo`). `cancelado` evita que uma resposta de um período antigo (troca
  // rápida hoje → 24h → 7d) sobrescreva a mais nova.
  useEffect(() => {
    let cancelado = false;
    getResumoOperacional(periodoParaDataInicio[periodo]())
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
  }, [periodo]);

  // D2-D3B — "Horas executadas", refeito a cada troca de período (mesma dependência de
  // `resumoOperacional` acima — o servidor só recebe `periodoInicio`). `cancelado` evita que
  // uma resposta de um período antigo sobrescreva a mais nova.
  useEffect(() => {
    let cancelado = false;
    getResumoTrafegoSessoes(periodoParaDataInicio[periodo]())
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
  }, [periodo]);

  // D2-D3C1 — indicadores, refeitos quando QUALQUER filtro muda (período, status, usuários,
  // departamentos, busca de demanda) ou quando uma sessão é aberta/fechada/atualizada
  // (`versaoIndicadores`). Debounce curto por causa da busca digitada. `cancelado` evita que uma
  // resposta antiga (troca rápida de filtro) sobrescreva a mais nova.
  useEffect(() => {
    let cancelado = false;
    const timeout = setTimeout(() => {
      getIndicadoresTrafegoSessoes({
        ...filtrosApi,
        periodoInicio: periodoParaDataInicio[periodo](),
        demandaQuery,
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
  }, [periodo, filtrosApi, demandaQuery, versaoIndicadores]);

  // D2-D3C2 — carga, refeita quando usuários, departamentos ou a busca de demanda mudam, ou em
  // `atualizar`. NÃO depende de período/status (nunca afetaram os rankings). Debounce e
  // `cancelado` pelas mesmas razões do efeito dos indicadores.
  useEffect(() => {
    let cancelado = false;
    const timeout = setTimeout(() => {
      getCargaTrafegoSessoes({ ...filtrosApi, demandaQuery })
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
  }, [filtrosApi, demandaQuery, versaoIndicadores]);

  // D2-D3C3 — "agora" (primeira página), refeito quando usuários, departamentos ou a busca de
  // demanda mudam, ou em `atualizar`. NÃO depende de período/status (nunca afetaram a tabela).
  // Trocar filtro/atualizar volta à primeira página. Debounce e `cancelado` como nos efeitos acima.
  useEffect(() => {
    let cancelado = false;
    chaveAgoraRef.current = JSON.stringify([filtrosApi, demandaQuery, versaoIndicadores]);
    const timeout = setTimeout(() => {
      setCarregandoAgora(true);
      setErroMaisAgora(null);
      getAgoraTrafegoSessoes({
        ...filtrosApi,
        demandaQuery,
        limit: TAMANHO_PAGINA_AGORA,
        offset: 0,
      })
        .then((pagina) => {
          if (cancelado) return;
          const recebidoEm = Date.now();
          setAgora({ linhas: pagina.items.map((item) => ({ ...item, recebidoEm })), total: pagina.total });
          setErroAgora(null);
        })
        .catch((error) => {
          if (cancelado) return;
          setErroAgora(error instanceof Error ? error.message : "Não foi possível carregar as sessões em execução.");
        })
        .finally(() => {
          if (!cancelado) setCarregandoAgora(false);
        });
    }, 250);
    return () => {
      cancelado = true;
      clearTimeout(timeout);
    };
  }, [filtrosApi, demandaQuery, versaoIndicadores]);

  // "Carregar mais": próxima página a partir de quantas linhas já estão na tela. Se os filtros
  // mudarem (ou houver `atualizar`) enquanto a página está em voo, ela é descartada.
  const carregarMaisAgora = useCallback(() => {
    if (!agora) return;
    const chaveDoClique = chaveAgoraRef.current;
    setCarregandoMaisAgora(true);
    setErroMaisAgora(null);
    getAgoraTrafegoSessoes({
      ...filtrosApi,
      demandaQuery,
      limit: TAMANHO_PAGINA_AGORA,
      offset: agora.linhas.length,
    })
      .then((pagina) => {
        if (chaveAgoraRef.current !== chaveDoClique) return;
        const recebidoEm = Date.now();
        setAgora((atual) => {
          if (!atual) return atual;
          const jaNaTela = new Set(atual.linhas.map((linha) => linha.sessaoId));
          const novas = pagina.items.filter((item) => !jaNaTela.has(item.sessaoId)).map((item) => ({ ...item, recebidoEm }));
          return { linhas: [...atual.linhas, ...novas], total: pagina.total };
        });
      })
      .catch((error) => {
        if (chaveAgoraRef.current !== chaveDoClique) return;
        setErroMaisAgora(error instanceof Error ? error.message : "Não foi possível carregar mais sessões.");
      })
      .finally(() => setCarregandoMaisAgora(false));
  }, [agora, filtrosApi, demandaQuery]);

  // Atualização completa: indicadores + carga + "agora". Usada pelo botão de refresh e por toda
  // ação que muda sessões (iniciar, encerrar) — nada fica para trás do que o servidor tem.
  const atualizar = useCallback(() => {
    setVersaoIndicadores((versao) => versao + 1);
  }, []);

  // D2-C — diretório de vínculo (autocomplete de "Iniciar sessão"): não arquivada, escopo
  // padrão da listagem, carregado uma vez — não depende de filtro/período de sessões.
  useEffect(() => {
    // Opções dos filtros de Cliente/Projeto: listas completas, carregadas uma vez. Falha aqui não derruba a tela
    // (os filtros ficam sem opções, mas o resto funciona). `diretoriosProntos` evita "Indisponível" enquanto carrega.
    let cancelado = false;
    Promise.all([
      listDiretorioClientes().then((lista) => !cancelado && setClientes(lista)),
      listDiretorioProjetos().then((lista) => !cancelado && setProjetos(lista)),
    ])
      .catch(() => {})
      .finally(() => {
        if (!cancelado) setDiretoriosProntos(true);
      });
    return () => {
      cancelado = true;
    };
  }, []);

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
        <TrafegoHeader onRefresh={atualizar} refreshing={carregandoAgora} />
        <AcessoNegado
          titulo="Central de Tráfego restrita à gestão autorizada"
          descricao="Esta visão reúne carga, capacidade e demandas de toda a operação — disponível apenas para perfis de gestão autorizados nesta fase."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <TrafegoHeader onRefresh={atualizar} refreshing={carregandoAgora} />
      <TrafegoIniciarSessao onCreated={atualizar} demandas={diretorioNovaSessao} />
      <TrafegoFilters
        periodo={periodo}
        onPeriodoChange={(proximo) => definirParam("periodo", proximo === PERIODO_PADRAO ? null : proximo)}
        demandaQuery={demandaQuery}
        onDemandaQueryChange={(texto) => definirParam("q", texto)}
        definicoes={definicoesFiltros}
        filtros={filtros}
        onFiltrosChange={definirFiltros}
      />

      {erroIndicadores && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
          {erroIndicadores}
        </div>
      )}
      <TrafegoResumoCards resumo={resumo} erro={erroIndicadores} />
      <TempoOperacionalCard resumo={resumo} erro={erroIndicadores} />

      <TrafegoIndicadoresDemandas
        resumo={resumoOperacional}
        erro={erroResumoOperacional}
        horasExecutadas={horasExecutadas}
        erroHorasExecutadas={erroHorasExecutadas}
      />
      <TrafegoAgoraTable
        linhas={agora?.linhas ?? null}
        total={agora?.total ?? 0}
        erro={erroAgora}
        now={now}
        onChanged={atualizar}
        onCarregarMais={carregarMaisAgora}
        carregandoMais={carregandoMaisAgora}
        erroMais={erroMaisAgora}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <TrafegoCargaUsuarios cargas={cargaUsuarios} erro={erroCarga} />
        <TrafegoCargaDepartamentos cargas={cargaDepartamentos} erro={erroCarga} />
        <TrafegoCargaEquipes cargas={cargaEquipes} erro={erroCarga} />
      </div>
    </div>
  );
}
