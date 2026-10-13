"use client";

import { AlertTriangle, Ban, ChevronDown, ChevronRight, Clock, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import type { DepartamentoDiretorioItem, UsuarioDiretorioItem } from "@/lib/api-backend";
import { formatPrazo, statusDemandaLabels, statusDemandaTone, workflowEtapaStatusLabels } from "@/lib/demandas";
import {
  fluxoDaTarefa,
  responsaveisDaTarefa,
  trabalhandoAgoraNaTarefa,
  type ProjetoComTarefas,
  type TrabalhandoAgora,
} from "@/lib/projetos-progresso";
import { primeiroNome } from "@/lib/member-selector";
import { rotuloDemanda } from "@/lib/referencias";
import type { Demanda } from "@/types/demanda";
import { BarraStatusProjeto } from "./BarraStatusProjeto";
import { FluxoEtapas } from "./FluxoEtapas";

type Usuarios = Record<string, UsuarioDiretorioItem> | null;

/** Colunas do desktop (lg): TAREFA | STATUS | FLUXO | ETAPA ATUAL | RESPONSÁVEIS | PRAZO. Abaixo disso cada linha vira um cartão empilhado (sem rolagem horizontal). */
export const COLUNAS_PROGRESSO = "lg:grid-cols-[minmax(0,2.2fr)_minmax(0,1.1fr)_minmax(0,1.4fr)_minmax(0,1.5fr)_minmax(0,1.6fr)_minmax(0,1fr)]";

const CABECALHOS = ["Tarefa", "Status", "Fluxo", "Etapa atual", "Responsáveis", "Prazo"];

/** Cabeçalho das colunas — só no layout em grade. */
export function CabecalhoColunas() {
  return (
    <div className={clsx("hidden gap-4 border-b border-line bg-surface-2 px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle lg:grid", COLUNAS_PROGRESSO)}>
      {CABECALHOS.map((cabecalho) => (
        <span key={cabecalho}>{cabecalho}</span>
      ))}
    </div>
  );
}

function RotuloCampo({ children }: { children: string }) {
  // Nome do campo só quando a linha está empilhada (no xl o cabeçalho das colunas já diz).
  return <span className="mb-0.5 block text-[10px] font-semibold uppercase tracking-wide text-fg-subtle lg:hidden">{children}</span>;
}

function ChipStatus({ status }: { status: Demanda["status"] }) {
  const icone = status === "bloqueada" ? <Ban className="mr-1 h-3 w-3" aria-hidden /> : status === "aguardando_cliente" ? <Clock className="mr-1 h-3 w-3" aria-hidden /> : null;
  return (
    <Badge tone={statusDemandaTone[status]}>
      {icone}
      {statusDemandaLabels[status]}
    </Badge>
  );
}

/** Avatar do responsável. "Agora" = tem sessão de trabalho ativa NESTA tarefa — marcado com texto (não só cor) e com leitura para tecnologia assistiva. Não abre seleção. */
function ResponsavelAvatar({ nome, usuario, agora, rotuloExtra }: { nome: string; usuario?: UsuarioDiretorioItem; agora: boolean; rotuloExtra?: string }) {
  return (
    <span className="flex min-w-0 items-center gap-1.5" title={`${nome}${agora ? " — trabalhando agora" : ""}${rotuloExtra ? ` — ${rotuloExtra}` : ""}`}>
      <span className="relative shrink-0">
        <Avatar nome={nome} corIdentificacao={usuario?.corIdentificacao ?? ""} fotoUrl={usuario?.fotoUrl} className={clsx("h-7 w-7 rounded-full text-[10px]", agora && "ring-2 ring-emerald-500 ring-offset-1 ring-offset-surface")} />
      </span>
      <span className="min-w-0">
        <span className="block truncate text-xs font-medium text-fg">{primeiroNome(nome) || "Carregando…"}</span>
        {agora && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-1.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" aria-hidden />
            Agora
            <span className="sr-only"> — trabalhando nesta tarefa neste momento</span>
          </span>
        )}
        {!agora && rotuloExtra && <span className="block truncate text-[10px] text-fg-subtle">{rotuloExtra}</span>}
      </span>
    </span>
  );
}

function Responsaveis({ demanda, usuarios, departamentos, agora }: { demanda: Demanda; usuarios: Usuarios; departamentos: DepartamentoDiretorioItem[]; agora: TrabalhandoAgora }) {
  const responsaveis = responsaveisDaTarefa(demanda);
  const vivo = trabalhandoAgoraNaTarefa(demanda.id, agora, responsaveis);
  const nomeDe = (id: string) => usuarios?.[id]?.nome ?? "";
  const MAX = 3;
  const visiveis = responsaveis.usuarioIds.slice(0, MAX);
  const restantes = responsaveis.usuarioIds.length - visiveis.length;
  return (
    <div className="flex min-w-0 flex-col gap-1">
      {responsaveis.origem === "workflow_concluido" ? (
        <span className="text-xs text-fg-subtle">—</span>
      ) : responsaveis.semResponsavel ? (
        <span className="text-xs text-fg-subtle">Sem responsável</span>
      ) : responsaveis.usuarioIds.length > 0 ? (
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {visiveis.map((id) => (
            <ResponsavelAvatar key={id} nome={nomeDe(id)} usuario={usuarios?.[id]} agora={vivo.responsaveisAgora.includes(id)} />
          ))}
          {restantes > 0 && <span className="self-center text-xs font-medium text-fg-muted" title={responsaveis.usuarioIds.slice(MAX).map(nomeDe).join(", ")}>+{restantes}</span>}
        </div>
      ) : (
        <div className="flex flex-wrap gap-1">
          {responsaveis.departamentoIds.map((id) => (
            <Badge key={id}>{departamentos.find((departamento) => departamento.id === id)?.nome ?? "Departamento"}</Badge>
          ))}
        </div>
      )}
      {/* Quem trabalha na tarefa mas NÃO é responsável da etapa atual: indicador separado, sem afirmar que é responsável. */}
      {vivo.outrosAgora.length > 0 && (
        <span className="flex flex-wrap items-center gap-1 text-[11px] text-fg-muted">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" aria-hidden />
          Também trabalhando agora: {vivo.outrosAgora.map((id) => nomeDe(id) || "usuário").join(", ")}
        </span>
      )}
      {/* Só sabemos QUE há alguém trabalhando (perfil sem acesso às pessoas): sem nome, sem afirmar responsável. */}
      {agora.fonte === "demandas" && vivo.alguemAgora && (
        <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" aria-hidden />
          Em execução agora
        </span>
      )}
    </div>
  );
}

function EtapaAtual({ demanda }: { demanda: Demanda }) {
  const fluxo = fluxoDaTarefa(demanda);
  if (fluxo.tipo === "sem_workflow") return <span className="text-xs text-fg-subtle">—</span>;
  if (fluxo.todasConcluidas || !fluxo.atual) return <span className="text-xs text-fg-muted">Todas as etapas concluídas</span>;
  const etapa = fluxo.atual;
  return (
    <div className="min-w-0">
      <span className="block truncate text-xs font-medium text-fg" title={etapa.nome}>
        {etapa.nome}
      </span>
      <span className="flex flex-wrap items-center gap-1 text-[11px] text-fg-muted">
        {workflowEtapaStatusLabels[etapa.status]}
        {etapa.tipo === "aprovacao" && (
          <span className="inline-flex items-center gap-0.5 rounded-full bg-violet-50 px-1.5 font-semibold text-violet-700 dark:bg-violet-500/10 dark:text-violet-300">
            <ShieldCheck className="h-3 w-3" aria-hidden />
            Aprovação
          </span>
        )}
      </span>
    </div>
  );
}

function Prazo({ demanda, atrasada }: { demanda: Demanda; atrasada: boolean }) {
  return atrasada ? (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-600 dark:text-red-400" title="Prazo da etapa atual vencido">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden />
      {formatPrazo(demanda.prazoEtapaAtual)}
      <span className="font-medium">Atrasada</span>
    </span>
  ) : (
    <span className="text-xs text-fg-muted">{formatPrazo(demanda.prazoEtapaAtual)}</span>
  );
}

/** Uma tarefa. A linha inteira abre o painel de detalhes que já existe (`DemandaDetailsDrawer`); aqui nada se edita. */
function LinhaTarefa({ demanda, atrasada, usuarios, departamentos, agora, onAbrir }: { demanda: Demanda; atrasada: boolean; usuarios: Usuarios; departamentos: DepartamentoDiretorioItem[]; agora: TrabalhandoAgora; onAbrir: (demanda: Demanda) => void }) {
  return (
    <li
      role="button"
      tabIndex={0}
      aria-label={`Abrir tarefa ${rotuloDemanda(demanda)} ${demanda.nome}`}
      onClick={() => onAbrir(demanda)}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onAbrir(demanda);
        }
      }}
      className={clsx(
        "grid cursor-pointer grid-cols-1 gap-3 border-b border-line px-4 py-3 text-left transition last:border-b-0 hover:bg-surface-2 focus-visible:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-indigo-500 sm:grid-cols-2 lg:items-center lg:gap-4",
        COLUNAS_PROGRESSO,
      )}
    >
      <div className="min-w-0 sm:col-span-2 lg:col-span-1">
        <RotuloCampo>Tarefa</RotuloCampo>
        <span className="block text-[11px] font-semibold text-fg-subtle">{rotuloDemanda(demanda)}</span>
        <span className="block truncate text-sm font-medium text-fg" title={demanda.nome}>
          {demanda.nome}
        </span>
      </div>
      <div>
        <RotuloCampo>Status</RotuloCampo>
        <ChipStatus status={demanda.status} />
      </div>
      <div>
        <RotuloCampo>Fluxo</RotuloCampo>
        <FluxoEtapas fluxo={fluxoDaTarefa(demanda)} />
      </div>
      <div className="min-w-0">
        <RotuloCampo>Etapa atual</RotuloCampo>
        <EtapaAtual demanda={demanda} />
      </div>
      <div className="min-w-0">
        <RotuloCampo>Responsáveis</RotuloCampo>
        <Responsaveis demanda={demanda} usuarios={usuarios} departamentos={departamentos} agora={agora} />
      </div>
      <div>
        <RotuloCampo>Prazo</RotuloCampo>
        <Prazo demanda={demanda} atrasada={atrasada} />
      </div>
    </li>
  );
}

function ChipAlerta({ quantidade, singular, plural, tom, icone }: { quantidade: number; singular: string; plural: string; tom: "red" | "amber"; icone: React.ReactNode }) {
  if (quantidade === 0) return null;
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold", tom === "red" ? "bg-red-50 text-red-700 dark:bg-red-500/10 dark:text-red-400" : "bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400")}>
      {icone}
      {quantidade} {quantidade === 1 ? singular : plural}
    </span>
  );
}

export function ProjetoProgressoGrupo({
  grupo,
  clienteNome,
  aberto,
  onAlternar,
  tarefasTotal,
  estaAtrasada,
  usuarios,
  departamentos,
  agora,
  onAbrirTarefa,
}: {
  grupo: ProjetoComTarefas;
  clienteNome: string;
  aberto: boolean;
  onAlternar: () => void;
  /** tarefas do projeto antes dos filtros de linha (para "mostrando X de Y") */
  tarefasTotal: number;
  estaAtrasada: (demanda: Demanda) => boolean;
  usuarios: Usuarios;
  departamentos: DepartamentoDiretorioItem[];
  agora: TrabalhandoAgora;
  onAbrirTarefa: (demanda: Demanda) => void;
}) {
  const { projeto, resumo, tarefas } = grupo;
  const idLista = `projeto-progresso-${projeto.id}`;
  return (
    <section className="overflow-hidden rounded-2xl border border-line bg-surface shadow-sm" aria-label={`Projeto ${projeto.nome}`}>
      <div className="flex flex-col gap-3 px-4 py-3">
        <button
          type="button"
          onClick={onAlternar}
          aria-expanded={aberto}
          aria-controls={idLista}
          className="-mx-2 -my-1 flex items-start gap-2 rounded-lg px-2 py-1 text-left transition hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500"
        >
          {aberto ? <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-fg-muted" aria-hidden /> : <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-fg-muted" aria-hidden />}
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-baseline gap-x-2">
              <span className="truncate text-sm font-semibold text-fg">{projeto.nome}</span>
              <span className="text-[11px] font-semibold text-fg-subtle">{projeto.codigoReferencia}</span>
            </span>
            <span className="block truncate text-xs text-fg-muted">{clienteNome}</span>
          </span>
          <span className="shrink-0 text-right">
            <span className="block text-sm font-semibold text-fg">{resumo.percentual === null ? "—" : `${resumo.percentual}%`}</span>
            <span className="block whitespace-nowrap text-[11px] text-fg-muted">
              {resumo.total === 0 ? "Sem tarefas" : `${resumo.concluidas} / ${resumo.total} tarefas concluídas`}
            </span>
          </span>
        </button>
        {(resumo.bloqueadas > 0 || resumo.atrasadas > 0 || resumo.aguardandoCliente > 0) && (
          <div className="flex flex-wrap gap-1.5 pl-6">
            <ChipAlerta quantidade={resumo.bloqueadas} singular="bloqueada" plural="bloqueadas" tom="red" icone={<Ban className="h-3 w-3" aria-hidden />} />
            <ChipAlerta quantidade={resumo.atrasadas} singular="atrasada" plural="atrasadas" tom="red" icone={<AlertTriangle className="h-3 w-3" aria-hidden />} />
            <ChipAlerta quantidade={resumo.aguardandoCliente} singular="aguardando cliente" plural="aguardando cliente" tom="amber" icone={<Clock className="h-3 w-3" aria-hidden />} />
          </div>
        )}
        <div className="pl-6">
          <BarraStatusProjeto resumo={resumo} />
        </div>
      </div>

      {aberto && (
        <div id={idLista} className="border-t border-line">
          {tarefas.length === 0 ? (
            <p className="px-4 py-4 text-xs text-fg-muted">
              {tarefasTotal === 0 ? "Este projeto ainda não tem tarefas." : "Nenhuma tarefa deste projeto corresponde aos filtros."}
            </p>
          ) : (
            <>
              <CabecalhoColunas />
              <ul>
                {tarefas.map((demanda) => (
                  <LinhaTarefa key={demanda.id} demanda={demanda} atrasada={estaAtrasada(demanda)} usuarios={usuarios} departamentos={departamentos} agora={agora} onAbrir={onAbrirTarefa} />
                ))}
              </ul>
              {tarefas.length < tarefasTotal && <p className="border-t border-line px-4 py-2 text-[11px] text-fg-muted">Mostrando {tarefas.length} de {tarefasTotal} tarefas (filtros ativos). O resumo acima considera todas.</p>}
            </>
          )}
        </div>
      )}
    </section>
  );
}
