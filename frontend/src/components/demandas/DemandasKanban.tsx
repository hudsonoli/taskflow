"use client";

import { type CSSProperties, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, type DragEndEvent, type DragMoveEvent, type DragStartEvent } from "@dnd-kit/core";
import { Clock, Lock } from "lucide-react";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { avaliarExpedienteOperacional, MOTIVO_INICIAR_FORA_EXPEDIENTE } from "@/lib/escopo-operacional";
import { useEstadoExpediente } from "@/lib/estadoExpediente";
import { colunaRecolhida, colunaSobOPonteiro } from "@/lib/kanban-colunas";
import { usePreferenciaBooleana } from "@/lib/preferencia-visual";
import type { Demanda, DemandaStatus, DemandaStatusEditavel } from "@/types/demanda";
import { DemandaKanbanCardOverlay } from "./DemandaKanbanCard";
import { DemandaKanbanColumn } from "./DemandaKanbanColumn";

type KanbanColumnConfig = {
  id: string;
  title: string;
  description: string;
  statuses: DemandaStatusEditavel[];
  tone: BadgeTone;
};

const kanbanColumns: KanbanColumnConfig[] = [
  { id: "rascunho-planejada", title: "Rascunho/Planejada", description: "Em preparação ou programadas.", statuses: ["rascunho", "planejada"], tone: "blue" },
  { id: "em-execucao", title: "Em execução", description: "Em andamento na operação.", statuses: ["em_execucao"], tone: "green" },
  { id: "pausada-bloqueada", title: "Pausada/Bloqueada", description: "Fluxos suspensos ou com impedimento.", statuses: ["pausada", "bloqueada"], tone: "amber" },
  { id: "aguardando-cliente", title: "Aguardando cliente", description: "Aguardando retorno externo.", statuses: ["aguardando_cliente"], tone: "amber" },
  { id: "concluida", title: "Concluída", description: "Tarefas finalizadas.", statuses: ["concluida"], tone: "green" },
  { id: "cancelada", title: "Cancelada", description: "Tarefas canceladas.", statuses: ["cancelada"], tone: "neutral" },
];

export function DemandasKanban({
  demandas,
  onOpenDetails,
  onMoveDemanda,
  onIniciarTrabalho,
}: {
  demandas: Demanda[];
  onOpenDetails: (demandaId: string) => void;
  onMoveDemanda: (demandaId: string, novoStatus: DemandaStatusEditavel) => void;
  /** "Iniciar trabalho": soltar um card em Em execução é o comando de começar a trabalhar (o servidor decide se abre sessão pessoal: só para quem executa a etapa). */
  onIniciarTrabalho: (demandaId: string) => void;
}) {
  const { estado } = useEstadoExpediente();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [avisoBloqueio, setAvisoBloqueio] = useState<string | null>(null);

  // Preferência VISUAL (só neste navegador): colunas sem cards visíveis ficam estreitas. "Vazia" = nenhum card carregado nela, não "o status inteiro está sem tarefas" (a lista pode ser só o universo carregado).
  const [recolherVazias, setRecolherVazias] = usePreferenciaBooleana("taskflow.kanban.recolherColunasVazias", true);
  // Expandidas à mão (ou por soltura) nesta página; abertas pelo arraste que as atravessou; e a decisão CONGELADA no início do gesto (nada colapsa no meio do arraste).
  const [expandidasManual, setExpandidasManual] = useState<ReadonlySet<string>>(new Set());
  const [expandidasPorArraste, setExpandidasPorArraste] = useState<ReadonlySet<string>>(new Set());
  const [congeladas, setCongeladas] = useState<ReadonlyMap<string, boolean> | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  // Enquanto `estado` não chegou (primeira busca a GET /expediente/estado) tratamos como
  // fora do expediente: é o lado seguro — não libera arrastar antes de saber o estado real.
  const expediente = estado
    ? // `trabalhoPermitido` (Fase Expediente 2): a decisão do SERVIDOR para ESTA pessoa — janela de trabalho nominal, com as isenções (admin/gestor/sistema/override).
      avaliarExpedienteOperacional(estado.trabalhoPermitido ?? estado.dentroExpediente)
    : { dentroExpediente: false, podeArrastar: false, podeIniciar: false, motivoBloqueio: undefined };

  const groupedDemands = useMemo(
    () =>
      kanbanColumns.map((column) => ({
        ...column,
        // `arquivada` não chega aqui: a listagem já a exclui e o Kanban não tem essa coluna.
        // O alargamento é só para comparar com o status vindo da API.
        demandas: demandas.filter((demanda) => (column.statuses as DemandaStatus[]).includes(demanda.status)),
      })),
    [demandas],
  );

  const activeDemanda = activeId ? demandas.find((demanda) => demanda.id === activeId) : undefined;

  const estaRecolhida = (colunaId: string, quantidade: number) =>
    colunaRecolhida({
      recolherVazias,
      quantidade,
      expandidaManual: expandidasManual.has(colunaId),
      expandidaPorArraste: expandidasPorArraste.has(colunaId),
      congelada: congeladas ? (congeladas.get(colunaId) ?? false) : null,
    });
  const adicionar = (conjunto: ReadonlySet<string>, id: string): ReadonlySet<string> => (conjunto.has(id) ? conjunto : new Set(conjunto).add(id));

  // O trilho esmaece nas bordas em que ainda há colunas escondidas (cada lado desliga ao chegar nele): sugere a rolagem sem pintar nada à toa.
  const trilhoRef = useRef<HTMLDivElement>(null);
  const [noInicio, setNoInicio] = useState(true);
  const [noFim, setNoFim] = useState(true);
  const sincronizarBordas = useCallback(() => {
    const trilho = trilhoRef.current;
    if (!trilho) return;
    setNoInicio(trilho.scrollLeft < 8);
    setNoFim(trilho.scrollLeft + trilho.clientWidth >= trilho.scrollWidth - 8);
  }, []);
  useEffect(() => {
    sincronizarBordas();
    const trilho = trilhoRef.current;
    if (!trilho) return;
    const observador = new ResizeObserver(sincronizarBordas);
    observador.observe(trilho);
    return () => observador.disconnect();
  }, [sincronizarBordas]);
  const mascaraDasBordas: CSSProperties | undefined =
    noInicio && noFim
      ? undefined
      : (() => {
          const mascara = `linear-gradient(to right, transparent 0%, #000 ${noInicio ? "0%" : "24px"}, #000 ${noFim ? "100%" : "calc(100% - 24px)"}, transparent 100%)`;
          return { maskImage: mascara, WebkitMaskImage: mascara };
        })();

  function handleDragStart(event: DragStartEvent) {
    setActiveId(String(event.active.id));
  }

  // Recolhimento visual durante o arraste (não decide nada de negócio; o motor, os sensores e o `handleDragEnd` abaixo seguem como estavam).
  function aoComecar(event: DragStartEvent) {
    setCongeladas(new Map(groupedDemands.map((coluna) => [coluna.id, estaRecolhida(coluna.id, coluna.demandas.length)])));
    setExpandidasPorArraste(new Set());
    handleDragStart(event);
  }

  function aoArrastar(event: DragMoveEvent) {
    const ativador = event.activatorEvent as PointerEvent | undefined;
    const trilho = trilhoRef.current;
    if (!ativador || typeof ativador.clientX !== "number" || !trilho) return;
    const caixas = Array.from(trilho.querySelectorAll<HTMLElement>("[data-kanban-coluna]")).map((elemento) => {
      const r = elemento.getBoundingClientRect();
      return { id: elemento.dataset.kanbanColuna ?? "", left: r.left, right: r.right, top: r.top, bottom: r.bottom };
    });
    const sobre = colunaSobOPonteiro(ativador.clientX + event.delta.x, ativador.clientY + event.delta.y, caixas);
    // só abre quem estava recolhida; fica aberta até o fim do gesto, para a soltura não cair numa coluna que muda de largura debaixo do ponteiro
    if (sobre && congeladas?.get(sobre)) setExpandidasPorArraste((atual) => adicionar(atual, sobre));
  }

  function aoSoltar(event: DragEndEvent) {
    const alvo = event.over ? String(event.over.id) : null;
    const alvoVazio = alvo ? (groupedDemands.find((coluna) => coluna.id === alvo)?.demandas.length ?? 1) === 0 : false;
    // quem recebe o primeiro card fica aberta (sem piscar enquanto a lista atualiza)
    if (alvo && alvoVazio) setExpandidasManual((atual) => adicionar(atual, alvo));
    setCongeladas(null);
    setExpandidasPorArraste(new Set());
    handleDragEnd(event);
  }

  function aoCancelar() {
    setCongeladas(null);
    setExpandidasPorArraste(new Set());
    setActiveId(null);
  }

  function alternarRecolhimento(ligado: boolean) {
    setExpandidasManual(new Set());
    setExpandidasPorArraste(new Set());
    setRecolherVazias(ligado);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const column = kanbanColumns.find((candidate) => candidate.id === over.id);
    const demanda = demandas.find((candidate) => candidate.id === active.id);
    if (!column || !demanda) return;
    if ((column.statuses as DemandaStatus[]).includes(demanda.status)) return;

    // Colunas que agrupam mais de um status (ex.: Rascunho/Planejada) usam o
    // primeiro status da lista como destino ao soltar o card.
    const novoStatus = column.statuses[0];

    // Segunda barreira, além de desabilitar o arraste: mesmo que um card chegue aqui
    // (drag iniciado dentro do expediente e solto depois do fim do turno, por exemplo),
    // iniciar fora do horário continua bloqueado.
    if (novoStatus === "em_execucao" && !expediente.podeIniciar) {
      setAvisoBloqueio(MOTIVO_INICIAR_FORA_EXPEDIENTE);
      return;
    }

    setAvisoBloqueio(null);
    // Em Em execução NÃO é só mudar o status: é "começar a trabalhar" — comando próprio, sem confirmação, troca de foco fluida. As demais colunas seguem o PATCH de status.
    if (novoStatus === "em_execucao") onIniciarTrabalho(demanda.id);
    else onMoveDemanda(demanda.id, novoStatus);
  }

  return (
    <div className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-fg">Fluxo por status</h2>
          <p className="text-sm text-fg-muted">Arraste um card para mudar o status, ou clique para abrir os detalhes.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-fg-muted">
            <input
              type="checkbox"
              checked={recolherVazias}
              onChange={(event) => alternarRecolhimento(event.target.checked)}
              className="h-3.5 w-3.5 cursor-pointer rounded border-zinc-300 accent-indigo-600"
            />
            Recolher colunas vazias automaticamente
          </label>
          {estado?.ativo && (
            <Badge tone={expediente.dentroExpediente ? "green" : "amber"}>
              <Clock className="mr-1 h-3 w-3" />
              {expediente.dentroExpediente ? "Dentro do expediente" : "Fora do expediente — quadro bloqueado"}
            </Badge>
          )}
        </div>
      </div>

      {!expediente.podeArrastar && estado && (
        <div className="mb-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <p>
            {expediente.motivoBloqueio} Novas tarefas continuam podendo ser cadastradas por Atendimento, heads e
            gestão — elas entram como planejadas e só podem ser iniciadas no próximo turno.
          </p>
        </div>
      )}

      {avisoBloqueio && (
        <div
          role="status"
          className="mb-3 flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
        >
          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <p>{avisoBloqueio}</p>
        </div>
      )}

      <DndContext sensors={sensors} onDragStart={aoComecar} onDragMove={aoArrastar} onDragEnd={aoSoltar} onDragCancel={aoCancelar}>
        <div ref={trilhoRef} onScroll={sincronizarBordas} style={mascaraDasBordas} className="overflow-x-auto pb-2">
          <div className="flex items-start gap-3">
            {groupedDemands.map((column) => (
              <DemandaKanbanColumn
                key={column.id}
                id={column.id}
                title={column.title}
                description={column.description}
                demandas={column.demandas}
                tone={column.tone}
                onOpenDetails={onOpenDetails}
                arrastavel={expediente.podeArrastar}
                motivoBloqueio={expediente.motivoBloqueio}
                onIniciarTrabalho={onIniciarTrabalho}
                podeIniciar={expediente.podeIniciar}
                recolhida={estaRecolhida(column.id, column.demandas.length)}
                onExpandir={() => setExpandidasManual((atual) => adicionar(atual, column.id))}
              />
            ))}
          </div>
        </div>

        <DragOverlay>{activeDemanda ? <DemandaKanbanCardOverlay demanda={activeDemanda} /> : null}</DragOverlay>
      </DndContext>
    </div>
  );
}
