"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { CalendarClock } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTenantPath } from "@/lib/useTenantPath";
import { EmptyState } from "@/components/ui/EmptyState";
import { FiltrosAvancados } from "@/components/filtros/FiltrosAvancados";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { type EscopoLeituraDemanda, getDemandaReal, listarDemandasEmExecucaoNaPauta } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { podeAcessarPautaGlobal } from "@/lib/escopo-operacional";
import { filtrosPautaParaApi } from "@/lib/filtros-pauta";
import {
  adicionarDias,
  agruparPorColaborador,
  agruparPorProjeto,
  dataValida,
  manterColaboradoresFiltrados,
  MODOS_PAUTA,
  PASSO_PERIODO_PAUTA_DIAS,
  PERIODO_PAUTA_DIAS,
  VISOES_PAUTA,
  type ModoPauta,
  type VisaoPauta,
} from "@/lib/pauta-operacional";
import { resolverClienteNome, resolverProjetoNome } from "@/lib/referencias";
import { useFiltrosNaUrl } from "@/lib/useFiltrosNaUrl";
import { DemandaDetailsDrawer } from "@/components/demandas/DemandaDetailsDrawer";
import type { Demanda } from "@/types/demanda";
import type { ParametrosPautaOperacional } from "@/types/pauta-operacional";
import { PautaGantt } from "./PautaGantt";
import { PautaLista } from "./PautaLista";
import { PautaToolbar } from "./PautaToolbar";
import type { PautaContexto } from "./pautaContexto";
import { useDefinicoesFiltrosPauta } from "./useDefinicoesFiltrosPauta";
import { usePautaOperacional } from "./usePautaOperacional";

// Pauta OPERACIONAL por ETAPA (P1_PAUTA_COLABORADOR). Uma fonte: `GET /pauta/operacional` devolve ITENS neutros (etapa + responsabilidade efetiva + janela planejada);
// Colaborador (padrão) e Projeto só reagrupam o MESMO conjunto — nenhuma regra de domínio aqui. A barra usa só o planejamento da etapa; prazo nunca é geometria.
//
// Fase 7C.1 — a Pauta é a visão operacional GLOBAL da empresa, só para Atendimento, Heads e Gestão (protegida no servidor: 403 a quem não pode). Operador comum NÃO tem Pauta
// — o trabalho dele é o Meu Dia — e quem chega pela URL vê "acesso negado". Concluída, cancelada e arquivada ficam fora (o servidor garante), e etapas concluídas também.
const DEBOUNCE_BUSCA_MS = 300;

export function PautaView() {
  const router = useRouter();
  const tp = useTenantPath();
  const { demandas, setDemandas, usuarioAtual, setDemandaParaAbrir } = useAppData();
  const { departamentos, carregando: carregandoDepartamentos } = useDiretorioDepartamentos();
  const { clientes, carregando: carregandoClientes } = useDiretorioClientes();
  const { projetos, carregando: carregandoProjetos } = useDiretorioProjetos();
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedDemandId, setSelectedDemandId] = useState<string | null>(null);

  // Mesma regra de papel do servidor (Atendimento, Head, Gestão). Só decidida com os departamentos carregados (Head e Atendimento
  // dependem deles): a consulta espera, e quem não pode nunca dispara a busca.
  const podeAcessar = usuarioAtual ? podeAcessarPautaGlobal(usuarioAtual, departamentos) : false;
  const pronto = Boolean(usuarioAtual) && !carregandoDepartamentos && podeAcessar;

  const definicoesFiltros = useDefinicoesFiltrosPauta({
    departamentos,
    clientes,
    projetos,
    diretoriosProntos: !carregandoDepartamentos && !carregandoClientes && !carregandoProjetos,
  });
  // Estado da Pauta na URL (filtros, busca, agrupamento, apresentação, início do período): ids/datas estáveis, refresh preserva, inválido ignorado.
  const { filtros, definirFiltros, param, definirParam } = useFiltrosNaUrl(definicoesFiltros, podeAcessar);
  const query = param("q") ?? "";
  const visao: VisaoPauta = VISOES_PAUTA.find((valor) => valor === param("visao")) ?? "colaborador";
  const modo: ModoPauta = MODOS_PAUTA.find((valor) => valor === param("modo")) ?? "gantt";
  const inicioDaUrl = dataValida(param("inicio")) ? (param("inicio") as string) : null;
  const setQuery = (texto: string) => definirParam("q", texto);
  const setVisao = (valor: VisaoPauta) => definirParam("visao", valor === "colaborador" ? null : valor);
  const setModo = (valor: ModoPauta) => definirParam("modo", valor === "gantt" ? null : valor);
  const parametrosFiltros = useMemo(() => filtrosPautaParaApi(filtros), [filtros]);

  useEffect(() => {
    const timeout = setTimeout(() => setDebouncedQuery(query.trim()), DEBOUNCE_BUSCA_MS);
    return () => clearTimeout(timeout);
  }, [query]);

  // Incrementado após mutation bem-sucedida no detalhe: força a releitura mesmo com filtros iguais (a etapa/planejamento pode ter mudado).
  const [versao, setVersao] = useState(0);
  const parametros = useMemo<ParametrosPautaOperacional | null>(
    () =>
      pronto
        ? { ...(inicioDaUrl ? { inicio: inicioDaUrl, fim: adicionarDias(inicioDaUrl, PERIODO_PAUTA_DIAS - 1) } : {}), ...parametrosFiltros, busca: debouncedQuery || undefined }
        : null,
    [pronto, inicioDaUrl, parametrosFiltros, debouncedQuery],
  );
  const pauta = usePautaOperacional(parametros, versao);
  const dados = pauta.dados;

  // Demandas com sessão ativa agora (selo discreto); falha não derruba a pauta. Refeito só após mutação, nunca por tecla digitada.
  const [emExecucaoIds, setEmExecucaoIds] = useState<ReadonlySet<string>>(new Set());
  useEffect(() => {
    if (!pronto) return;
    let cancelado = false;
    listarDemandasEmExecucaoNaPauta()
      .catch(() => [] as string[])
      .then((ativas) => {
        if (!cancelado) setEmExecucaoIds(new Set(ativas));
      });
    return () => {
      cancelado = true;
    };
  }, [pronto, versao]);

  const contexto = useMemo<PautaContexto>(() => {
    const nomesPessoas = new Map((dados?.pessoas ?? []).map((pessoa) => [pessoa.id, pessoa.nome]));
    return {
      visao,
      nomeCliente: (clienteId) => (clienteId ? resolverClienteNome(clienteId, clientes) : null),
      nomeProjeto: (projetoId) => (projetoId ? resolverProjetoNome(projetoId, projetos) : null),
      nomeDepartamento: (departamentoId) => departamentos.find((departamento) => departamento.id === departamentoId)?.nome ?? "Departamento indisponível",
      nomePessoa: (usuarioId) => nomesPessoas.get(usuarioId) ?? "Usuário indisponível",
      emExecucaoIds,
      onOpenDetails: setSelectedDemandId,
    };
  }, [visao, dados, clientes, projetos, departamentos, emExecucaoIds]);

  const grupos = useMemo(() => {
    if (!dados) return [];
    return visao === "colaborador"
      ? manterColaboradoresFiltrados(agruparPorColaborador(dados.itens, dados.pessoas), parametrosFiltros.usuarioIds)
      : agruparPorProjeto(dados.itens, (projetoId) => resolverProjetoNome(projetoId, projetos));
  }, [dados, visao, projetos, parametrosFiltros.usuarioIds]);

  function deslocarPeriodo(dias: number) {
    const base = inicioDaUrl ?? dados?.meta.inicio;
    if (base) definirParam("inicio", adicionarDias(base, dias));
  }

  // D2-C — mesmo padrão de DemandasView.tsx: GET /demandas/{id} só se o id não está no contexto (a Pauta não carrega Demandas inteiras). `cancelado` protege troca de seleção.
  const [fallbackDemand, setFallbackDemand] = useState<Demanda | null>(null);
  useEffect(() => {
    if (!selectedDemandId) return;
    if (demandas.some((demanda) => demanda.id === selectedDemandId)) return;
    let cancelado = false;
    getDemandaReal(selectedDemandId, "pauta")
      .then((demanda) => {
        if (!cancelado) setFallbackDemand(demanda);
      })
      .catch(() => {
        // Inexistente/fora do escopo: drawer permanece fechado.
      });
    return () => {
      cancelado = true;
    };
  }, [selectedDemandId, demandas, versao]);

  // Fase 7C.1 — o detalhe aberto pela Pauta é SOMENTE LEITURA por padrão (ler pela Pauta global não dá escrita). Só vira editável se a
  // demanda também está no escopo-BASE de quem olha (a consulta sem `escopo` devolve 200; fora dele, 404): é a mesma autoridade do
  // servidor, que continua decidindo cada escrita. Enquanto a sonda não responde (ou falha), fica em leitura.
  const [acessoEscrita, setAcessoEscrita] = useState<{ demandaId: string; editavel: boolean } | null>(null);
  useEffect(() => {
    if (!selectedDemandId) return;
    let cancelado = false;
    getDemandaReal(selectedDemandId)
      .then(() => {
        if (!cancelado) setAcessoEscrita({ demandaId: selectedDemandId, editavel: true });
      })
      .catch(() => {
        if (!cancelado) setAcessoEscrita({ demandaId: selectedDemandId, editavel: false });
      });
    return () => {
      cancelado = true;
    };
  }, [selectedDemandId]);
  const modoLeitura: EscopoLeituraDemanda | undefined =
    acessoEscrita?.demandaId === selectedDemandId && acessoEscrita.editavel ? undefined : "pauta";

  // O contexto cobre o intervalo entre o patch síncrono de uma mutation e o refetch; o fallback só entra se o contexto não resolveu.
  const selectedDemand = demandas.find((demanda) => demanda.id === selectedDemandId) ?? (fallbackDemand?.id === selectedDemandId ? fallbackDemand : undefined);

  function handleDemandChange(nextDemand: Demanda) {
    // Só patch de contexto (outras telas ainda dependem dele) + releitura da Pauta: a mutação pode mudar etapa, responsável ou planejamento e mover a etapa de grupo/posição —
    // só o servidor sabe decidir isso corretamente.
    setDemandas((current) => current.map((demanda) => (demanda.id === nextDemand.id ? nextDemand : demanda)));
    setVersao((tick) => tick + 1);
  }

  // Pauta não duplica o modal de edição — "Editar" leva para Tarefas com a tarefa já aberta.
  function handleEdit(demandaId: string) {
    setSelectedDemandId(null);
    setDemandaParaAbrir({ demandaId });
    router.push(tp("tarefas"));
  }

  if (!usuarioAtual) return null;

  // Operador comum não tem Pauta (tem o Meu Dia). Espera os departamentos antes de negar: Head e Atendimento dependem deles.
  if (carregandoDepartamentos) return <p className="text-sm text-fg-subtle">Carregando…</p>;
  if (!podeAcessar) {
    return (
      <div className="flex flex-col gap-6">
        <AcessoNegado
          titulo="A Pauta é restrita ao Atendimento, Heads e Gestão"
          descricao="Para acompanhar o seu trabalho, use o Meu dia. Fale com a Gestão se você precisa desta visão."
        />
      </div>
    );
  }

  const truncadas = dados ? [dados.totais.planejadas, dados.totais.incompletas, dados.totais.naoPlanejadas].filter((balde) => balde.truncado) : [];

  return (
    <div className="flex flex-col gap-6">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
        className="rounded-xl border border-line bg-surface p-4 shadow-sm"
      >
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
              <CalendarClock className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h1 className="text-lg font-semibold tracking-tight text-fg">Pauta</h1>
              <p className="mt-0.5 max-w-3xl text-xs leading-5 text-fg-muted">
                Agenda operacional por etapa: quem está responsável, quando e em qual cliente/projeto. A barra mostra o planejamento da etapa (não o prazo); etapa sem planejamento, planejamento
                incompleto e trabalho sem pessoa definida continuam visíveis.
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <PautaToolbar
        query={query}
        onQueryChange={setQuery}
        visao={visao}
        onVisaoChange={setVisao}
        modo={modo}
        onModoChange={setModo}
        periodoInicio={dados?.meta.inicio ?? null}
        periodoFim={dados?.meta.fim ?? null}
        onPeriodoAnterior={() => deslocarPeriodo(-PASSO_PERIODO_PAUTA_DIAS)}
        onPeriodoSeguinte={() => deslocarPeriodo(PASSO_PERIODO_PAUTA_DIAS)}
        onPeriodoHoje={() => definirParam("inicio", null)}
        filtrosAvancados={<FiltrosAvancados definicoes={definicoesFiltros} filtros={filtros} onChange={definirFiltros} />}
      />

      {pauta.carregando && !dados ? (
        <p className="text-sm text-fg-subtle">Carregando pauta…</p>
      ) : pauta.erro && !dados ? (
        <EmptyState title="Não foi possível carregar a pauta" description={pauta.erro} icon={<CalendarClock size={16} />} />
      ) : dados ? (
        <div className={pauta.atualizando ? "flex flex-col gap-3 opacity-60 transition-opacity" : "flex flex-col gap-3 transition-opacity"}>
          {(dados.totais.planejadasAntes > 0 || dados.totais.planejadasDepois > 0) && (
            <p className="text-xs text-fg-subtle">
              {dados.totais.planejadasAntes > 0 && `${dados.totais.planejadasAntes} ${dados.totais.planejadasAntes === 1 ? "etapa planejada" : "etapas planejadas"} antes deste período`}
              {dados.totais.planejadasAntes > 0 && dados.totais.planejadasDepois > 0 && " · "}
              {dados.totais.planejadasDepois > 0 && `${dados.totais.planejadasDepois} ${dados.totais.planejadasDepois === 1 ? "etapa planejada" : "etapas planejadas"} depois`}
            </p>
          )}
          {truncadas.length > 0 && (
            <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
              Há mais etapas do que cabem nesta tela ({truncadas.map((balde) => `${balde.devolvidos} de ${balde.total}`).join(", ")}). Refine os filtros ou o período para ver todas.
            </p>
          )}
          {modo === "lista" ? (
            <PautaLista grupos={grupos} contexto={contexto} />
          ) : (
            <PautaGantt grupos={grupos} periodoInicio={dados.meta.inicio} periodoFim={dados.meta.fim} hoje={dados.meta.hoje} contexto={contexto} />
          )}
        </div>
      ) : null}

      {pauta.erro && dados && <p className="text-xs text-red-600">{pauta.erro}</p>}

      <DemandaDetailsDrawer
        key={selectedDemand?.id}
        demanda={selectedDemand}
        onClose={() => setSelectedDemandId(null)}
        onEdit={handleEdit}
        onChange={handleDemandChange}
        modoLeitura={modoLeitura}
      />
    </div>
  );
}
