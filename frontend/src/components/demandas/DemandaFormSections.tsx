import type { ReactNode } from "react";
import {
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  CircleDot,
  FileText,
  GitBranch,
  History,
  Plus,
  Trash2,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Select } from "@/components/ui/Select";
import { StatusPill } from "@/components/ui/StatusPill";
import { Textarea } from "@/components/ui/Textarea";
import {
  departamentosProjetoDisponiveis,
  generateId,
  prioridadeDemandaLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveProjetoDemandaNome,
  resolveResponsaveisProjetoNomes,
  responsaveisProjetoDisponiveis,
  statusDemandaLabels,
  workflowEtapaStatusLabels,
} from "@/lib/demandas-mock";
import type {
  Demanda,
  DemandaPrioridade,
  DemandaStatus,
  DemandaWorkflowEtapa,
  DemandaWorkflowEtapaStatus,
} from "@/types/demanda";

type DemandaSectionProps = {
  demanda: Demanda;
  onChange: (demanda: Demanda) => void;
};

type DemandaSectionShellProps = {
  title: string;
  description: string;
  eyebrow: string;
  icon: ReactNode;
  action?: ReactNode;
  children: ReactNode;
};

const workflowStatusTone: Record<
  DemandaWorkflowEtapaStatus,
  "neutral" | "blue" | "green" | "amber" | "red"
> = {
  pendente: "neutral",
  em_execucao: "green",
  pausada: "amber",
  concluida: "green",
};

function DemandaSectionShell({
  title,
  description,
  eyebrow,
  icon,
  action,
  children,
}: DemandaSectionShellProps) {
  return (
    <section className="rounded-3xl border border-zinc-100 bg-white p-4 shadow-sm sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-700 ring-1 ring-blue-100">
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <SectionHeader
            eyebrow={eyebrow}
            title={title}
            description={description}
            action={action}
          />
        </div>
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function updateDemanda(
  demanda: Demanda,
  patch: Partial<Demanda>,
  onChange: (demanda: Demanda) => void
) {
  onChange({ ...demanda, ...patch, updatedAt: new Date().toISOString() });
}

export function DadosDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  return (
    <DemandaSectionShell
      eyebrow="Dados"
      title="Dados principais"
      description="Dados principais da demanda e prazo da etapa atual."
      icon={<ClipboardList className="h-5 w-5" />}
    >
      <div className="mb-5 flex flex-wrap gap-2">
        <StatusPill tone="blue">{prioridadeDemandaLabels[demanda.prioridade]}</StatusPill>
        <StatusPill tone="green">{statusDemandaLabels[demanda.status]}</StatusPill>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input label="Código" value={demanda.codigoInterno} disabled />
        <Input
          label="Projeto"
          value={resolveProjetoDemandaNome(demanda.projetoId)}
          disabled
        />
        <Input
          label="Cliente"
          value={resolveClienteProjetoNome(demanda.clienteId)}
          disabled
        />
        <Input
          label="Prazo atual"
          type="date"
          value={demanda.prazoEtapaAtual}
          onChange={(event) =>
            updateDemanda(
              demanda,
              { prazoEtapaAtual: event.target.value },
              onChange
            )
          }
        />
        <Select
          label="Prioridade"
          value={demanda.prioridade}
          onChange={(event) =>
            updateDemanda(
              demanda,
              { prioridade: event.target.value as DemandaPrioridade },
              onChange
            )
          }
          options={Object.entries(prioridadeDemandaLabels).map(
            ([value, label]) => ({ value, label })
          )}
        />
        <Select
          label="Status"
          value={demanda.status}
          onChange={(event) =>
            updateDemanda(
              demanda,
              { status: event.target.value as DemandaStatus },
              onChange
            )
          }
          options={Object.entries(statusDemandaLabels).map(([value, label]) => ({
            value,
            label,
          }))}
        />
      </div>
    </DemandaSectionShell>
  );
}

export function BriefingDemandaSection({
  demanda,
  onChange,
}: DemandaSectionProps) {
  return (
    <DemandaSectionShell
      eyebrow="Briefing"
      title="Briefing"
      description="Editor simples nesta fase. Rich text será avaliado futuramente."
      icon={<FileText className="h-5 w-5" />}
    >
      <Textarea
        label="Briefing"
        rows={10}
        value={demanda.briefing}
        onChange={(event) =>
          updateDemanda(demanda, { briefing: event.target.value }, onChange)
        }
      />
    </DemandaSectionShell>
  );
}

function createWorkflowEtapa(ordem: number): DemandaWorkflowEtapa {
  return {
    id: generateId("etapa-demanda"),
    nome: "Nova etapa",
    ordem,
    usuarioResponsavelIds: [],
    departamentoResponsavelIds: [],
    prazoHoras: 8,
    status: "pendente",
  };
}

export function WorkflowDemandaSection({
  demanda,
  onChange,
}: DemandaSectionProps) {
  function updateEtapa(etapaId: string, patch: Partial<DemandaWorkflowEtapa>) {
    updateDemanda(
      demanda,
      {
        workflowEtapas: demanda.workflowEtapas.map((etapa) =>
          etapa.id === etapaId ? { ...etapa, ...patch } : etapa
        ),
      },
      onChange
    );
  }

  function removeEtapa(etapaId: string) {
    const nextEtapas = demanda.workflowEtapas
      .filter((etapa) => etapa.id !== etapaId)
      .map((etapa, index) => ({ ...etapa, ordem: index + 1 }));

    updateDemanda(
      demanda,
      {
        workflowEtapas: nextEtapas,
        etapaAtualId:
          demanda.etapaAtualId === etapaId
            ? nextEtapas[0]?.id ?? ""
            : demanda.etapaAtualId,
      },
      onChange
    );
  }

  const totalEtapas = demanda.workflowEtapas.length;
  const etapasConcluidas = demanda.workflowEtapas.filter(
    (etapa) => etapa.status === "concluida"
  ).length;
  const progressoEtapas = totalEtapas
    ? Math.round((etapasConcluidas / totalEtapas) * 100)
    : 0;
  const etapaAtual = demanda.workflowEtapas.find(
    (etapa) => etapa.id === demanda.etapaAtualId
  );

  return (
    <DemandaSectionShell
      eyebrow="Workflow"
      title="Workflow"
      description="Etapas mock por demanda. Não há motor real, Kanban ou drag-and-drop nesta fase."
      icon={<GitBranch className="h-5 w-5" />}
      action={
        <Button
          type="button"
          onClick={() =>
            updateDemanda(
              demanda,
              {
                workflowEtapas: [
                  ...demanda.workflowEtapas,
                  createWorkflowEtapa(demanda.workflowEtapas.length + 1),
                ],
              },
              onChange
            )
          }
          className="inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Adicionar etapa
        </Button>
      }
    >
      <div className="mb-5 rounded-3xl border border-zinc-100 bg-zinc-50/70 p-4">
        <div className="grid gap-3 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">
              Fluxo da demanda
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StatusPill tone="blue">
                {totalEtapas} etapa(s)
              </StatusPill>
              <StatusPill tone={etapaAtual ? workflowStatusTone[etapaAtual.status] : "neutral"}>
                {etapaAtual ? etapaAtual.nome : "Sem etapa atual"}
              </StatusPill>
              <StatusPill tone="green">
                {etapasConcluidas} concluída(s)
              </StatusPill>
            </div>
          </div>

          {totalEtapas > 0 && (
            <div className="rounded-2xl bg-white p-3 ring-1 ring-zinc-100">
              <ProgressBar
                value={progressoEtapas}
                tone="green"
                label="Etapas concluídas"
              />
            </div>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {demanda.workflowEtapas.map((etapa) => {
          const etapaAtualSelecionada = demanda.etapaAtualId === etapa.id;

          return (
            <div
              key={etapa.id}
              className={`rounded-3xl border p-4 shadow-sm transition hover:border-zinc-200 hover:shadow-md ${
                etapaAtualSelecionada
                  ? "border-blue-200 bg-blue-50/40"
                  : "border-zinc-100 bg-zinc-50/60"
              }`}
            >
              <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div
                    className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl ring-1 ${
                      etapaAtualSelecionada
                        ? "bg-blue-600 text-white ring-blue-600"
                        : etapa.status === "concluida"
                          ? "bg-emerald-50 text-emerald-700 ring-emerald-100"
                          : "bg-white text-zinc-500 ring-zinc-100"
                    }`}
                  >
                    {etapa.status === "concluida" ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : (
                      <CircleDot className="h-5 w-5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill tone={workflowStatusTone[etapa.status]}>
                        Etapa {etapa.ordem}
                      </StatusPill>
                      {etapaAtualSelecionada && (
                        <StatusPill tone="blue">Etapa atual</StatusPill>
                      )}
                    </div>
                    <p className="mt-2 text-base font-semibold text-zinc-950">
                      {etapa.nome}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-500">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 font-medium ring-1 ring-zinc-100">
                        <CalendarDays className="h-3.5 w-3.5" />
                        {etapa.prazoHoras}h
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 font-medium ring-1 ring-zinc-100">
                        <UsersRound className="h-3.5 w-3.5" />
                        {resolveResponsaveisProjetoNomes(etapa.usuarioResponsavelIds) || "Sem usuário"}
                      </span>
                    </div>
                  </div>
                </div>

                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => removeEtapa(etapa.id)}
                  className="inline-flex items-center gap-2"
                >
                  <Trash2 className="h-4 w-4" />
                  Remover etapa
                </Button>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <Input
                  label="Nome da etapa"
                  value={etapa.nome}
                  onChange={(event) =>
                    updateEtapa(etapa.id, { nome: event.target.value })
                  }
                />
                <Input
                  label="Prazo em horas"
                  type="number"
                  min={1}
                  value={etapa.prazoHoras}
                  onChange={(event) =>
                    updateEtapa(etapa.id, {
                      prazoHoras: Number(event.target.value),
                    })
                  }
                />
                <Select
                  label="Status da etapa"
                  value={etapa.status}
                  onChange={(event) =>
                    updateEtapa(etapa.id, {
                      status: event.target.value as DemandaWorkflowEtapaStatus,
                    })
                  }
                  options={Object.entries(workflowEtapaStatusLabels).map(
                    ([value, label]) => ({ value, label })
                  )}
                />
                <Select
                  label="Etapa atual"
                  value={demanda.etapaAtualId === etapa.id ? etapa.id : ""}
                  onChange={() =>
                    updateDemanda(demanda, { etapaAtualId: etapa.id }, onChange)
                  }
                  options={[
                    { value: "", label: "Não" },
                    { value: etapa.id, label: "Sim" },
                  ]}
                />
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <MultiSelect
                  label="Usuários da etapa"
                  placeholder="Selecione usuários"
                  values={etapa.usuarioResponsavelIds}
                  onChange={(values) =>
                    updateEtapa(etapa.id, { usuarioResponsavelIds: values })
                  }
                  options={responsaveisProjetoDisponiveis.map((responsavel) => ({
                    value: responsavel.id,
                    label: responsavel.nome,
                  }))}
                />
                <MultiSelect
                  label="Departamentos da etapa"
                  placeholder="Selecione departamentos"
                  values={etapa.departamentoResponsavelIds}
                  onChange={(values) =>
                    updateEtapa(etapa.id, {
                      departamentoResponsavelIds: values,
                    })
                  }
                  options={departamentosProjetoDisponiveis.map((departamento) => ({
                    value: departamento.id,
                    label: departamento.nome,
                  }))}
                />
              </div>

              <div className="mt-4 rounded-2xl bg-white p-3 text-xs text-zinc-500 ring-1 ring-zinc-100">
                Departamentos: {resolveDepartamentosProjetoNomes(etapa.departamentoResponsavelIds) || "Sem departamento"}
              </div>
            </div>
          );
        })}
      </div>
    </DemandaSectionShell>
  );
}

export function ResponsaveisDemandaSection({
  demanda,
  onChange,
}: DemandaSectionProps) {
  return (
    <DemandaSectionShell
      eyebrow="Responsáveis"
      title="Responsáveis"
      description="Responsáveis principais por ID. Nomes são derivados apenas para exibição."
      icon={<UsersRound className="h-5 w-5" />}
    >
      <div className="grid gap-4 md:grid-cols-2">
        <MultiSelect
          label="Usuários responsáveis"
          placeholder="Selecione usuários"
          values={demanda.usuarioResponsavelIds}
          onChange={(values) =>
            updateDemanda(demanda, { usuarioResponsavelIds: values }, onChange)
          }
          options={responsaveisProjetoDisponiveis.map((responsavel) => ({
            value: responsavel.id,
            label: responsavel.nome,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          placeholder="Selecione departamentos"
          values={demanda.departamentoResponsavelIds}
          onChange={(values) =>
            updateDemanda(
              demanda,
              { departamentoResponsavelIds: values },
              onChange
            )
          }
          options={departamentosProjetoDisponiveis.map((departamento) => ({
            value: departamento.id,
            label: departamento.nome,
          }))}
        />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Input
          label="Usuários selecionados"
          value={resolveResponsaveisProjetoNomes(demanda.usuarioResponsavelIds)}
          disabled
        />
        <Input
          label="Departamentos selecionados"
          value={resolveDepartamentosProjetoNomes(
            demanda.departamentoResponsavelIds
          )}
          disabled
        />
      </div>
    </DemandaSectionShell>
  );
}

export function HistoricoDemandaSection({ demanda }: { demanda: Demanda }) {
  return (
    <DemandaSectionShell
      eyebrow="Histórico"
      title="Histórico"
      description="Eventos mock preparados para auditoria futura."
      icon={<History className="h-5 w-5" />}
    >
      <div className="space-y-3">
        {demanda.historico.map((evento) => (
          <div
            key={evento.id}
            className="rounded-3xl border border-zinc-100 bg-zinc-50/60 p-4"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex gap-3">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-blue-500" />
                <div>
                  <p className="font-semibold text-zinc-950">{evento.acao}</p>
                  <p className="mt-1 text-sm text-zinc-500">
                    {evento.usuario} · {evento.dataHora}
                  </p>
                </div>
              </div>
              <StatusPill tone="neutral">{evento.dispositivo}</StatusPill>
            </div>
            <p className="mt-3 text-sm text-zinc-500">IP: {evento.ip}</p>
          </div>
        ))}
      </div>
    </DemandaSectionShell>
  );
}
