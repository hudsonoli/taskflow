"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { AlertTriangle, CalendarClock, ClipboardCheck, Gauge, Headset, PauseCircle, PlayCircle, Send } from "lucide-react";
import { AvatarStack } from "@/components/ui/AvatarStack";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Select } from "@/components/ui/Select";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { IndicadoresGrid, type IndicadorItem } from "@/components/operacional/IndicadoresGrid";
import { DemandaDetailsDrawer } from "@/components/demandas/DemandaDetailsDrawer";
import { getResumoAtendimento, listDemandasReais, type ResumoAtendimento } from "@/lib/api-backend";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useUsuariosComIds } from "@/lib/useUsuariosComIds";
import { resolverDepartamentoNome, resolverUsuarioPorReferencia } from "@/lib/referencias";
import {
  formatPrazo,
  normalizarUsuarioId,
  statusDemandaLabels,
  statusDemandaTone,
} from "@/lib/demandas";
import { classificarTarefa, podeAcessarMinhasDemandas } from "@/lib/escopo-operacional";
import type { Demanda, DemandaStatus } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { resolverClientePorReferencia } from "@/lib/referencias";
import { rotuloDemanda } from "@/lib/referencias";

// D2-B4: mesma razão do D2-B1/B2/B3 — AppDataContext.demandas vem limitado a 200 itens
// carregados uma única vez no login. MinhasDemandasView filtrava esse array localmente
// (criador/responsável/carteira comercial) E calculava 9 indicadores agregados sobre o mesmo
// array truncado. A lista passa a consultar `GET /demandas?escopo=atendimento` (recorte já
// existente no backend — a MESMA fórmula de criador/responsável/carteira, com autorização
// real, 403 se não for Atendimento) com paginação real; os indicadores passam a vir de
// `GET /demandas/minhas/resumo`, agregados no servidor sobre o universo INTEGRAL do escopo —
// nunca sobre uma página parcial, o que só trocaria o cap global de 200 por um cap por
// usuário. AppDataContext continua alimentando mutations (patch) e outras telas.
const TAMANHO_PAGINA = 50;

type StatusFiltro = DemandaStatus | "todos";

function statusParaBackend(filtro: StatusFiltro): string | undefined {
  return filtro === "todos" ? undefined : filtro;
}

export function MinhasDemandasView() {
  const { demandas, setDemandas, usuarioAtual, setDemandaParaAbrir } = useAppData();
  const { clientes } = useDiretorioClientes();
  const { departamentos } = useDiretorioDepartamentos();
  const router = useRouter();
  const [statusFiltro, setStatusFiltro] = useState<StatusFiltro>("todos");
  const [selecionadaId, setSelecionadaId] = useState<string | null>(null);

  const podeAcessar = usuarioAtual ? podeAcessarMinhasDemandas(usuarioAtual, departamentos) : false;

  // Página do servidor — fonte autoritativa da lista exibida.
  const [offset, setOffset] = useState(0);
  const [demandasPagina, setDemandasPagina] = useState<Demanda[]>([]);
  const [carregandoInicial, setCarregandoInicial] = useState(true);
  const [buscandoPagina, setBuscandoPagina] = useState(true);
  const [temProximaPagina, setTemProximaPagina] = useState(false);
  const [erroPagina, setErroPagina] = useState<string | null>(null);
  const { usuarios } = useUsuariosComIds(demandasPagina.flatMap((demanda) => demanda.usuarioResponsavelIds));
  // Incrementado após mutation bem-sucedida — força refetch da página atual E do resumo,
  // mesmo quando filtros não mudaram (ver handleDemandChange).
  const [refetchTick, setRefetchTick] = useState(0);

  // Indicadores agregados — universo integral, nunca a página atual. Não recebem
  // `statusFiltro`: o resumo sempre foi calculado antes do filtro do dropdown, e isso não
  // muda com a migração (ver diagnóstico D2-B4).
  const [resumo, setResumo] = useState<ResumoAtendimento | null>(null);
  const [carregandoResumo, setCarregandoResumo] = useState(true);
  const [erroResumo, setErroResumo] = useState<string | null>(null);

  function alterarStatusFiltro(valor: StatusFiltro) {
    setStatusFiltro(valor);
    setOffset(0); // troca de status sempre volta pra primeira página
  }

  // Chave da busca atual — comparada durante o RENDER (não dentro do efeito): setState
  // síncrono no corpo do efeito é o padrão que react-hooks/set-state-in-effect rejeita neste
  // projeto — mesma técnica de DemandasView.tsx/PautaView.tsx.
  const chaveBusca = `${statusFiltro}\u0000${offset}\u0000${refetchTick}`;
  const [chaveConsultada, setChaveConsultada] = useState<string | null>(null);
  if (chaveBusca !== chaveConsultada) {
    setChaveConsultada(chaveBusca);
    setBuscandoPagina(true);
    setErroPagina(null);
  }

  useEffect(() => {
    // `!podeAcessar` renderiza AcessoNegado antes de qualquer leitura destes estados — não há
    // necessidade de setState aqui (e setState síncrono no corpo do efeito é o padrão que
    // react-hooks/set-state-in-effect rejeita neste projeto).
    if (!podeAcessar) return;
    let cancelado = false;
    listDemandasReais({
      escopo: "atendimento",
      status: statusParaBackend(statusFiltro),
      limit: TAMANHO_PAGINA,
      offset,
    })
      .then((resultado) => {
        if (cancelado) return; // resposta obsoleta — outra busca já foi disparada depois desta
        // Página ficou vazia (ex.: uma mutation tirou o último item dela do filtro atual) —
        // volta uma página automaticamente, mesmo padrão de DemandasView.tsx.
        if (resultado.length === 0 && offset > 0) {
          setOffset((atual) => Math.max(0, atual - TAMANHO_PAGINA));
          return;
        }
        setDemandasPagina(resultado);
        setTemProximaPagina(resultado.length === TAMANHO_PAGINA);
        setErroPagina(null);
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      })
      .catch((error) => {
        if (cancelado) return;
        setErroPagina(error instanceof Error ? error.message : "Não foi possível carregar suas demandas.");
        setBuscandoPagina(false);
        setCarregandoInicial(false);
      });
    return () => {
      cancelado = true;
    };
  }, [podeAcessar, statusFiltro, offset, refetchTick]);

  useEffect(() => {
    if (!podeAcessar) return;
    let cancelado = false;
    getResumoAtendimento()
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
  }, [podeAcessar, refetchTick]);

  // Página remota é a fonte de verdade; contexto só cobre o intervalo entre o patch síncrono
  // de uma mutation e o refetch assíncrono terminar.
  const selecionada = demandasPagina.find((demanda) => demanda.id === selecionadaId) ?? demandas.find((demanda) => demanda.id === selecionadaId);

  function handleDemandChange(demandaAtualizada: Demanda) {
    // Patch de contexto (outras telas ainda dependem dele) + refetch — NUNCA patch local da
    // página: a mutation pode mudar responsável/cliente/status/prazo e fazer a demanda
    // entrar, sair ou mudar de indicador — só um refetch decide isso corretamente.
    setDemandas((current) => current.map((item) => (item.id === demandaAtualizada.id ? demandaAtualizada : item)));
    setRefetchTick((tick) => tick + 1);
  }

  const valorIndicador = (valor: number | undefined): number | string => {
    if (carregandoResumo) return "…";
    if (erroResumo || valor === undefined) return "—";
    return valor;
  };

  const indicadores: IndicadorItem[] = [
    { key: "criadas", title: "Criadas", value: valorIndicador(resumo?.criadas), description: "No seu escopo de atendimento.", icon: <Headset size={16} />, tone: "blue" },
    { key: "nao-iniciadas", title: "Não iniciadas", value: valorIndicador(resumo?.naoIniciadas), description: "Rascunho ou planejada.", icon: <CalendarClock size={16} />, tone: "neutral" },
    { key: "em-execucao", title: "Em execução", value: valorIndicador(resumo?.emExecucao), description: "Em andamento agora.", icon: <PlayCircle size={16} />, tone: "green" },
    { key: "aguardando-cliente", title: "Aguardando cliente", value: valorIndicador(resumo?.aguardandoCliente), description: "Retorno externo pendente.", icon: <Send size={16} />, tone: "amber" },
    { key: "aguardando-atendimento", title: "Aguardando atendimento", value: valorIndicador(resumo?.aguardandoAtendimento), description: "Bloqueadas — ação interna pendente.", icon: <PauseCircle size={16} />, tone: "amber" },
    { key: "pausadas", title: "Pausadas", value: valorIndicador(resumo?.pausadas), description: "Fluxo suspenso.", icon: <PauseCircle size={16} />, tone: "amber" },
    { key: "atrasadas", title: "Atrasadas", value: valorIndicador(resumo?.atrasadas), description: "Prazo da etapa atual vencido.", icon: <AlertTriangle size={16} />, tone: "red" },
    { key: "dentro-prazo", title: "Dentro do prazo", value: valorIndicador(resumo?.dentroDoPrazo), description: "Ativas, sem atraso.", icon: <Gauge size={16} />, tone: "green" },
    { key: "concluidas", title: "Concluídas", value: valorIndicador(resumo?.concluidas), description: "Finalizadas.", icon: <ClipboardCheck size={16} />, tone: "green" },
  ];

  // "Editar" não duplica modal — edição completa acontece no módulo Tarefas.
  function handleEdit(demandaId: string) {
    setSelecionadaId(null);
    setDemandaParaAbrir({ demandaId, aba: "dados" });
    router.push("/tarefas");
  }

  if (!usuarioAtual) return null;

  if (!podeAcessar) {
    return (
      <div className="flex flex-col gap-6">
        <Cabecalho />
        <AcessoNegado
          titulo="Visão restrita ao Atendimento"
          descricao="Minhas Demandas mostra as tarefas criadas, sob sua responsabilidade ou de clientes atendidos por você — disponível para quem está no departamento Atendimento."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Cabecalho />

      <IndicadoresGrid itens={indicadores} colunas={3} />
      {erroResumo && <p className="text-xs text-red-600">{erroResumo}</p>}

      <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
        <div className="max-w-xs">
          <Select
            label="Status"
            value={statusFiltro}
            onChange={(event) => alterarStatusFiltro(event.target.value as StatusFiltro)}
            options={[{ value: "todos", label: "Todos" }, ...Object.entries(statusDemandaLabels).map(([value, label]) => ({ value, label }))]}
          />
        </div>
      </div>

      {carregandoInicial ? (
        <p className="text-sm text-fg-subtle">Carregando suas demandas…</p>
      ) : erroPagina && demandasPagina.length === 0 ? (
        <EmptyState title="Não foi possível carregar" description={erroPagina} />
      ) : demandasPagina.length === 0 ? (
        <EmptyState title="Nenhuma demanda encontrada" description="Ajuste o filtro para visualizar suas demandas." />
      ) : (
        <div className={buscandoPagina ? "opacity-60 transition-opacity" : "transition-opacity"}>
          <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-[1100px] w-full text-left text-sm">
                <thead className="bg-zinc-50/80 text-xs font-semibold uppercase tracking-[0.12em] text-fg-subtle dark:bg-zinc-950/40">
                  <tr>
                    {["Título", "Cliente", "Depto. executor", "Responsável", "Status", "Prazo", "Previsão", "Última atualização", "Pendência"].map(
                      (coluna) => (
                        <th key={coluna} className="px-4 py-2.5">
                          {coluna}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                  {demandasPagina.map((demanda) => {
                    const classificacao = classificarTarefa(demanda);
                    const cliente = resolverClientePorReferencia(demanda.clienteId, clientes);
                    const responsaveis = demanda.usuarioResponsavelIds
                      .map((id) => resolverUsuarioPorReferencia(normalizarUsuarioId(id), usuarios))
                      .filter((usuario): usuario is (typeof usuarios)[number] => Boolean(usuario));

                    const pendencia =
                      demanda.status === "aguardando_cliente"
                        ? { texto: "Aguardando retorno do cliente", origem: "Origem: cliente" }
                        : demanda.status === "bloqueada"
                          ? { texto: "Bloqueio interno", origem: "Origem: interna" }
                          : null;

                    return (
                      <tr key={demanda.id} className="group transition hover:bg-indigo-50/30 dark:hover:bg-indigo-500/5">
                        <td className="px-4 py-3">
                          <button
                            type="button"
                            onClick={() => setSelecionadaId(demanda.id)}
                            className="max-w-[220px] text-left font-semibold text-fg transition hover:text-indigo-600 dark:hover:text-indigo-400"
                          >
                            <span className="block truncate">{demanda.nome}</span>
                            <span className="mt-0.5 block truncate text-xs font-medium text-fg-subtle">{rotuloDemanda(demanda)}</span>
                          </button>
                        </td>
                        <td className="max-w-[140px] truncate px-4 py-3 text-fg-muted">{cliente?.nome ?? "Sem cliente"}</td>
                        <td className="max-w-[160px] truncate px-4 py-3 text-fg-muted">
                          {demanda.departamentoResponsavelIds.length === 0
                            ? "-"
                            : demanda.departamentoResponsavelIds
                                .map((id) => resolverDepartamentoNome(id, departamentos))
                                .join(", ")}
                        </td>
                        <td className="px-4 py-3">
                          <AvatarStack pessoas={responsaveis} max={2} size="h-7 w-7" />
                        </td>
                        <td className="px-4 py-3">
                          <Badge tone={statusDemandaTone[demanda.status]}>{statusDemandaLabels[demanda.status]}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <span className={classificacao.atrasada ? "font-semibold text-red-600" : "text-fg-muted"}>
                            {formatPrazo(demanda.prazoEtapaAtual)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-fg-muted">{formatPrazo(demanda.dataFimPrevista)}</td>
                        <td className="px-4 py-3 text-xs text-fg-muted">
                          {new Date(demanda.updatedAt).toLocaleDateString("pt-BR")}
                        </td>
                        <td className="px-4 py-3 text-xs">
                          {pendencia ? (
                            <div>
                              <p className="font-medium text-zinc-700 dark:text-zinc-200">{pendencia.texto}</p>
                              <p className="text-fg-subtle">{pendencia.origem}</p>
                            </div>
                          ) : (
                            <span className="text-fg-subtle">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
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

      <DemandaDetailsDrawer
        key={selecionada?.id}
        demanda={selecionada}
        onClose={() => setSelecionadaId(null)}
        onChange={handleDemandChange}
        onEdit={handleEdit}
      />
    </div>
  );
}

function Cabecalho() {
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
            <Headset className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-fg">Minhas Demandas</h1>
            <p className="mt-1 text-sm leading-6 text-fg-muted">
              Demandas criadas por você, sob sua responsabilidade, ou de clientes que você atende.
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
