"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Building2,
  CalendarClock,
  CheckCircle2,
  Gauge,
  PauseCircle,
  Send,
  ShieldAlert,
  Timer,
  UserX,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { FiltrosAvancados } from "@/components/filtros/FiltrosAvancados";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { type IndicadorItem } from "@/components/operacional/IndicadoresGrid";
import { KpiStrip } from "@/components/ui/KpiStrip";
import { TarefasLista } from "@/components/operacional/TarefasLista";
import { getResumoDepartamento, listDemandasReais, type ResumoDepartamento } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useEstadoExpediente } from "@/lib/estadoExpediente";
import { useDiretorioEquipes } from "@/lib/diretorioEquipes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { getHorasDepartamento } from "@/lib/api";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { filtrosMeuDepartamentoParaApi } from "@/lib/filtros-meu-departamento";
import { useFiltrosNaUrl } from "@/lib/useFiltrosNaUrl";
import {
  capacidadeAproximada,
  formatHoras,
  podeAcessarMeuDepartamento,
  resolverHeadDepartamento,
} from "@/lib/escopo-operacional";
import type { Demanda } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { EquipeAgoraCard } from "./EquipeAgoraCard";
import { useDefinicoesFiltrosMeuDepartamento } from "./useDefinicoesFiltrosMeuDepartamento";

const DIAS_UTEIS_SEMANA = 5;
const TAMANHO_PAGINA = 50;

// D2-B5: mesma razão do D2-B1/B2/B3/B4 — AppDataContext.demandas vem limitado a 200 itens.
// A lista consulta GET /demandas com escopo=meu-departamento (autoridade RBAC — 403 se não for
// head) + departamentoId=<departamentoHead.id> (recorte funcional singular, mesma lógica de
// resolverHeadDepartamento — nunca "todos os departamentos que ele lidera"); os 7 contadores +
// horasEstimadas + sobrecarga vêm de GET /demandas/meu-departamento/resumo, agregados no servidor
// sobre o universo INTEGRAL do departamento. Tela somente-leitura.
//
// Fase 6.1: os filtros são os AVANÇADOS compartilhados (chips, operadores, vários valores, estado na
// URL) e REFINAM a lista no servidor, antes da paginação. O departamento NÃO é filtro — é o escopo.
// Os indicadores (KPIs) continuam sendo do departamento INTEIRO, como sempre foram: os filtros
// afetam só a lista (decisão antiga e deliberada da tela, mantida).

export function MeuDepartamentoView() {
  const { usuarioAtual } = useAppData();
  const { estado: estadoExpediente } = useEstadoExpediente();
  const { clientes, carregando: carregandoClientes } = useDiretorioClientes();
  const { equipes, carregando: carregandoEquipes } = useDiretorioEquipes();
  const { departamentos } = useDiretorioDepartamentos();
  const { usuarios } = useDiretorioUsuarios();
  const { projetos, carregando: carregandoProjetos } = useDiretorioProjetos();

  const [offset, setOffset] = useState(0);

  const [horasConsumidas, setHorasConsumidas] = useState(0);
  const [carregandoHoras, setCarregandoHoras] = useState(true);
  const [erroHoras, setErroHoras] = useState<string | null>(null);

  const departamentoHead = usuarioAtual ? resolverHeadDepartamento(usuarioAtual, departamentos) : undefined;
  const definicoesFiltros = useDefinicoesFiltrosMeuDepartamento({
    departamentoId: departamentoHead?.id,
    equipes,
    clientes,
    projetos,
    diretoriosProntos: !carregandoEquipes && !carregandoClientes && !carregandoProjetos,
  });
  const { filtros, definirFiltros } = useFiltrosNaUrl(definicoesFiltros, true);
  // Atalhos de data ("hoje", "atrasado"…) viram intervalos uma vez por mudança de filtro (não a cada render).
  const parametrosFiltros = useMemo(() => filtrosMeuDepartamentoParaApi(filtros, new Date()), [filtros]);
  const podeAcessar = usuarioAtual ? podeAcessarMeuDepartamento(usuarioAtual, departamentos) : false;

  // Página do servidor — fonte autoritativa da lista exibida.
  const [demandasPagina, setDemandasPagina] = useState<Demanda[]>([]);
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [buscandoPagina, setBuscandoPagina] = useState(true);
  const [temProximaPagina, setTemProximaPagina] = useState(false);
  const [erroPagina, setErroPagina] = useState<string | null>(null);

  // Resumo agregado — universo INTEGRAL do departamento, nunca a página/filtros da lista
  // (mesma semântica de `classificacoesDept` pré-migração: os 8 selects afetam só a tabela).
  const [resumo, setResumo] = useState<ResumoDepartamento | null>(null);
  const [carregandoResumo, setCarregandoResumo] = useState(true);
  const [erroResumo, setErroResumo] = useState<string | null>(null);

  async function carregarHoras(id: string) {
    setCarregandoHoras(true);
    setErroHoras(null);
    try {
      const resultado = await getHorasDepartamento(id);
      setHorasConsumidas(resultado.horasConsumidas);
    } catch (error) {
      setErroHoras(error instanceof Error ? error.message : "Não foi possível carregar as horas (API indisponível).");
    } finally {
      setCarregandoHoras(false);
    }
  }

  useEffect(() => {
    if (!departamentoHead) return;
    const timeoutId = setTimeout(() => {
      void carregarHoras(departamentoHead.id);
    }, 0);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [departamentoHead?.id]);

  // Qualquer mudança de filtro — ou de departamento atual (Fase 5: a revalidação do contexto troca o Head) — volta à
  // primeira página. Comparado durante o RENDER (mesmo padrão das demais telas), nunca em efeito.
  const chaveContexto = `${departamentoHead?.id ?? ""}\u0000${JSON.stringify(parametrosFiltros)}`;
  const [chaveContextoVista, setChaveContextoVista] = useState(chaveContexto);
  if (chaveContexto !== chaveContextoVista) {
    setChaveContextoVista(chaveContexto);
    setOffset(0);
  }

  // Colaboradores ativos do departamento a partir do diretório (até 200): usado SÓ no cálculo de
  // capacidade abaixo — a métrica segue exatamente como estava. O filtro "Responsável" busca no
  // servidor (definição em useDefinicoesFiltrosMeuDepartamento).
  const colaboradoresOptions = departamentoHead
    ? usuarios.filter((usuario) => usuario.departamentoId === departamentoHead.id && usuario.status === "ativo")
    : [];

  // Cliente/Projeto: ANTES derivados de `tarefasDoDept` (array truncado) — corrigido para
  // diretório completo, mesma correção já aplicada em D2-B1 (busca) e D2-B2/B3
  // (paginação). Equipe já vinha de diretório completo — sem alteração.

  // Chave da busca atual — comparada durante o RENDER, mesma técnica de
  // DemandasView.tsx/PautaView.tsx/MinhasDemandasView.tsx.
  const chaveBusca = [departamentoHead?.id ?? "", JSON.stringify(parametrosFiltros), offset].join("\u0000");
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveBusca !== chaveConsultada) {
    setChaveConsultada(chaveBusca);
    setBuscandoPagina(true);
    setErroPagina(null);
  }

  useEffect(() => {
    if (!podeAcessar || !departamentoHead) return;
    let cancelado = false;
    listDemandasReais({
      ...parametrosFiltros,
      // O escopo de segurança é o do servidor (`escopo=meu-departamento`); `departamentoId` só estreita ao departamento ATUAL.
      escopo: "meu-departamento",
      departamentoId: departamentoHead.id,
      limit: TAMANHO_PAGINA,
      offset,
    })
      .then((resultado) => {
        if (cancelado) return;
        setDemandasPagina(resultado);
        setTemProximaPagina(resultado.length === TAMANHO_PAGINA);
        setErroPagina(null);
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErroPagina(error instanceof Error ? error.message : "Não foi possível carregar as tarefas do departamento.");
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      });
    return () => {
      cancelado = true;
    };
  }, [podeAcessar, departamentoHead, parametrosFiltros, offset]);

  useEffect(() => {
    if (!podeAcessar || !departamentoHead) return;
    let cancelado = false;
    getResumoDepartamento(departamentoHead.id)
      .then((resultado) => {
        if (cancelado) return;
        setResumo(resultado);
        setErroResumo(null);
        setCarregandoResumo(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErroResumo(error instanceof Error ? error.message : "Não foi possível carregar os indicadores.");
        setCarregandoResumo(false);
      });
    return () => {
      cancelado = true;
    };
  }, [podeAcessar, departamentoHead]);

  const valorIndicador = (valor: number | undefined): number | string => {
    if (carregandoResumo) return "…";
    if (erroResumo || valor === undefined) return "—";
    return valor;
  };

  // `null` (não `0`) enquanto o estado ainda não chegou — `0` é um valor real (hoje não é
  // dia útil) e não pode ser confundido com "sem dado ainda" (ver capacidadeAproximada).
  const horasUteisHoje = estadoExpediente?.horasUteisHoje ?? null;
  const capacidadeTotal = capacidadeAproximada(horasUteisHoje, colaboradoresOptions.length, DIAS_UTEIS_SEMANA);
  const capacidadeDisponivel = Math.max(0, capacidadeTotal - horasConsumidas);

  function formatHorasIndicador(valor: number | undefined): string {
    if (carregandoResumo) return "…";
    if (erroResumo || valor === undefined) return "—";
    return formatHoras(valor);
  }

  const indicadores: IndicadorItem[] = [
    { key: "novas", title: "Novas", value: valorIndicador(resumo?.novas), description: "Rascunho ou planejada.", icon: <CalendarClock size={16} />, tone: "blue" },
    { key: "sem-responsavel", title: "Sem responsável", value: valorIndicador(resumo?.semResponsavel), description: "Precisam de atribuição.", icon: <UserX size={16} />, tone: "amber" },
    { key: "andamento", title: "Em andamento", value: valorIndicador(resumo?.emAndamento), description: "Em execução agora.", icon: <Gauge size={16} />, tone: "green" },
    { key: "pausadas", title: "Pausadas", value: valorIndicador(resumo?.pausadas), description: "Pausadas ou bloqueadas.", icon: <PauseCircle size={16} />, tone: "amber" },
    { key: "aguardando", title: "Aguardando", value: valorIndicador(resumo?.aguardando), description: "Aguardando retorno do cliente.", icon: <Send size={16} />, tone: "amber" },
    { key: "atrasadas", title: "Atrasadas", value: valorIndicador(resumo?.atrasadas), description: "Prazo da etapa atual vencido.", icon: <AlertTriangle size={16} />, tone: "red" },
    { key: "concluidas", title: "Concluídas", value: valorIndicador(resumo?.concluidas), description: "Finalizadas.", icon: <CheckCircle2 size={16} />, tone: "green" },
    { key: "horas-estimadas", title: "Horas estimadas (aprox.)", value: formatHorasIndicador(resumo?.horasEstimadasTotal), description: "Soma do workflow — estimativa derivada.", icon: <Timer size={16} />, tone: "neutral" },
    { key: "horas-consumidas", title: "Horas consumidas", value: carregandoHoras ? "…" : formatHoras(horasConsumidas), description: "Sessões de trabalho reais do departamento.", icon: <Timer size={16} />, tone: "neutral" },
    { key: "capacidade-disponivel", title: "Capacidade disponível (aprox.)", value: formatHoras(capacidadeDisponivel), description: "Capacidade aproximada da semana menos consumido.", icon: <Gauge size={16} />, tone: "blue" },
    {
      key: "sobrecarregados",
      title: "Colaboradores sobrecarregados",
      value: valorIndicador(resumo?.colaboradoresSobrecarregados),
      description: "Estimativa acima da capacidade aproximada.",
      icon: <ShieldAlert size={16} />,
      tone: (resumo?.colaboradoresSobrecarregados ?? 0) > 0 ? "red" : "neutral",
    },
  ];

  if (!usuarioAtual) return null;

  if (!podeAcessar || !departamentoHead) {
    return (
      <div className="flex flex-col gap-6">
        <Cabecalho nomeDepartamento={undefined} />
        <AcessoNegado
          titulo="Você não é Head de nenhum departamento"
          descricao="Esta visão é destinada aos responsáveis formais por um departamento. Fale com a Gestão se isso não estiver correto."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Cabecalho nomeDepartamento={departamentoHead.nome} />

      <KpiStrip
        ariaLabel="Indicadores do departamento"
        itens={indicadores.map(({ key, title, value, description, icon, tone }) => ({ key, label: title, value, description, icon, tone }))}
      />
      {erroResumo && <p className="text-xs text-red-600">{erroResumo}</p>}

      {erroHoras && departamentoHead && (
        <EstadoErro
          mensagem={`${erroHoras} — horas consumidas ficaram indisponíveis.`}
          onRetry={() => void carregarHoras(departamentoHead.id)}
        />
      )}

      {/* Quem está trabalhando agora (sessões reais). `key`: ao trocar o departamento atual, recomeça sem dados do anterior. */}
      <EquipeAgoraCard key={departamentoHead.id} departamentoId={departamentoHead.id} />

      <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
        <p className="mb-3 text-sm font-semibold text-fg">Filtros</p>
        <FiltrosAvancados definicoes={definicoesFiltros} filtros={filtros} onChange={definirFiltros} />
      </div>

      {carregandoInicial ? (
        <p className="text-sm text-fg-subtle">Carregando tarefas do departamento…</p>
      ) : (
        <div className={buscandoPagina ? "opacity-60 transition-opacity" : "transition-opacity"}>
          <TarefasLista
            demandas={demandasPagina}
            clientes={clientes}
            emptyTitle={erroPagina ? "Não foi possível carregar" : "Nenhuma tarefa encontrada"}
            emptyDescription={erroPagina ?? "Ajuste os filtros para visualizar tarefas do departamento."}
          />
        </div>
      )}

      {erroPagina && demandasPagina.length > 0 && <p className="text-xs text-red-600">{erroPagina}</p>}

      {!carregandoInicial && (demandasPagina.length > 0 || offset > 0) && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-fg-subtle">
            {offset > 0 ? `Itens ${offset + 1}–${offset + demandasPagina.length}` : `${demandasPagina.length} item(ns)`}
          </span>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={offset === 0 || buscandoPagina}
              onClick={() => setOffset((atual) => Math.max(0, atual - TAMANHO_PAGINA))}
            >
              Anterior
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={!temProximaPagina || buscandoPagina}
              onClick={() => setOffset((atual) => atual + TAMANHO_PAGINA)}
            >
              Próxima
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function Cabecalho({ nomeDepartamento }: { nomeDepartamento: string | undefined }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
      className="rounded-xl border border-line bg-surface p-4 shadow-sm"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-fg">Meu Departamento</h1>
            <p className="mt-1 text-sm leading-6 text-fg-muted">
              {nomeDepartamento ? `Visão operacional de ${nomeDepartamento}.` : "Visão restrita a Heads de departamento."}
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
