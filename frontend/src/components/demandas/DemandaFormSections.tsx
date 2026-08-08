"use client";

import type { ReactNode } from "react";
import { ClipboardList, FileText, GitBranch, History, UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Combobox } from "@/components/ui/Combobox";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import {
  departamentosProjetoDisponiveis,
  normalizarUsuarioId,
  prioridadeDemandaLabels,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisDemandaNomes,
  statusDemandaLabels,
} from "@/lib/demandas-mock";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { resolverDepartamentoNome } from "@/lib/referencias";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { normalizarReferenciasParaCodigoInterno } from "@/lib/referencias";
import type { Demanda, DemandaPrioridade, DemandaStatus } from "@/types/demanda";
import { RichTextEditor } from "@/components/ui/RichTextEditor";
import { DemandaArquivosCard } from "./DemandaArquivosCard";
import { DemandaChecklistCard } from "./DemandaChecklistCard";
import { EnvioClienteCard } from "./EnvioClienteCard";
import { RegistrarAjusteCard } from "./RegistrarAjusteCard";
import { WorkflowEtapasEditor } from "./WorkflowEtapasEditor";

type DemandaSectionProps = {
  demanda: Demanda;
  onChange: (demanda: Demanda) => void;
};

function SectionShell({
  title,
  description,
  icon,
  action,
  children,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">{title}</h3>
              <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{description}</p>
            </div>
            {action}
          </div>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function updateDemanda(demanda: Demanda, patch: Partial<Demanda>, onChange: (demanda: Demanda) => void) {
  onChange({ ...demanda, ...patch, updatedAt: new Date().toISOString() });
}

export function DadosDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  const { projetos, clientes } = useAppData();

  function handleProjetoChange(projetoId: string) {
    const projeto = projetos.find((item) => item.id === projetoId);
    updateDemanda(demanda, { projetoId, clienteId: projeto?.clienteId ?? demanda.clienteId }, onChange);
  }

  return (
    <SectionShell title="Dados principais" description="Dados principais da tarefa e prazo da etapa atual." icon={<ClipboardList className="h-5 w-5" />}>
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone="blue">{prioridadeDemandaLabels[demanda.prioridade]}</Badge>
        <Badge tone="green">{statusDemandaLabels[demanda.status]}</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Input label="Código" value={demanda.codigoInterno} disabled />
        <Input
          label="PIT (opcional)"
          placeholder="Ex: C3A-0008/26"
          value={demanda.pit ?? ""}
          onChange={(event) => updateDemanda(demanda, { pit: event.target.value || undefined }, onChange)}
        />
        <Combobox
          label="Projeto"
          value={demanda.projetoId}
          onChange={handleProjetoChange}
          options={projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome }))}
          placeholder="Buscar projeto…"
          emptyLabel="Nenhum projeto encontrado"
        />
        <Combobox
          label="Cliente"
          value={demanda.clienteId}
          onChange={(clienteId) => updateDemanda(demanda, { clienteId }, onChange)}
          options={clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome }))}
          placeholder="Buscar cliente…"
          emptyLabel="Nenhum cliente encontrado"
        />
        <Input
          label="Prazo atual (data e horário)"
          type="datetime-local"
          value={demanda.prazoEtapaAtual}
          onChange={(event) => updateDemanda(demanda, { prazoEtapaAtual: event.target.value }, onChange)}
        />
        <Select
          label="Prioridade"
          value={demanda.prioridade}
          onChange={(event) => updateDemanda(demanda, { prioridade: event.target.value as DemandaPrioridade }, onChange)}
          options={Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label }))}
        />
        <Select
          label="Status"
          value={demanda.status}
          onChange={(event) => updateDemanda(demanda, { status: event.target.value as DemandaStatus }, onChange)}
          options={Object.entries(statusDemandaLabels).map(([value, label]) => ({ value, label }))}
        />
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <EnvioClienteCard demanda={demanda} onChange={onChange} />
        <RegistrarAjusteCard demanda={demanda} onChange={onChange} />
      </div>
    </SectionShell>
  );
}

export function BriefingDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  return (
    <SectionShell title="Briefing" description="Use negrito, grifo e cor de fonte para destacar pontos do briefing." icon={<FileText className="h-5 w-5" />}>
      <RichTextEditor
        value={demanda.briefing}
        onChange={(html) => updateDemanda(demanda, { briefing: html }, onChange)}
      />

      <div className="mt-4 flex flex-col gap-3">
        <DemandaChecklistCard demanda={demanda} onChange={onChange} />
        <DemandaArquivosCard demanda={demanda} onChange={onChange} />
      </div>
    </SectionShell>
  );
}

export function WorkflowDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  return (
    <SectionShell title="Workflow" description="Etapas livres, ajustadas conforme o fluxo de cada tarefa." icon={<GitBranch className="h-5 w-5" />}>
      <WorkflowEtapasEditor
        etapas={demanda.workflowEtapas}
        etapaAtualId={demanda.etapaAtualId}
        onEtapasChange={(etapas) => updateDemanda(demanda, { workflowEtapas: etapas }, onChange)}
        onEtapaAtualChange={(id) => updateDemanda(demanda, { etapaAtualId: id }, onChange)}
      />
    </SectionShell>
  );
}

export function ResponsaveisDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  const { departamentos } = useDiretorioDepartamentos();
  // Picker só oferece usuário ativo; referência histórica de inativo resolve nome/avatar
  // em outros lugares via resolverUsuarioPorReferencia (ver lib/referencias.ts).
  const diretorio = useDiretorioUsuarios().usuarios;
  const usuariosAtivos = diretorio.filter((usuario) => usuario.status === "ativo");

  return (
    <SectionShell title="Responsáveis" description="Responsáveis principais por ID." icon={<UsersRound className="h-5 w-5" />}>
      <div className="grid gap-3 md:grid-cols-2">
        <MemberSelector
          label="Usuários responsáveis"
          values={normalizarReferenciasParaCodigoInterno(demanda.usuarioResponsavelIds.map(normalizarUsuarioId), diretorio)}
          onChange={(values) => updateDemanda(demanda, { usuarioResponsavelIds: values }, onChange)}
          placeholder="Selecionar responsáveis…"
          options={usuariosAtivos.map((usuario) => ({
            // Enquanto Demanda continuar mock, o valor gravado é o codigoInterno — ver
            // docs/padrao-arquivamento.md.
            id: usuario.codigoInterno,
            nome: usuario.nome,
            subtitulo: resolverDepartamentoNome(usuario.departamentoId ?? "", departamentos),
            corIdentificacao: usuario.corIdentificacao,
            fotoUrl: usuario.fotoUrl,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          values={demanda.departamentoResponsavelIds}
          onChange={(values) => updateDemanda(demanda, { departamentoResponsavelIds: values }, onChange)}
          options={departamentosProjetoDisponiveis.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
        />
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Input label="Usuários selecionados" value={resolveResponsaveisDemandaNomes(demanda.usuarioResponsavelIds, diretorio)} disabled />
        <Input label="Departamentos selecionados" value={resolveDepartamentosProjetoNomes(demanda.departamentoResponsavelIds)} disabled />
      </div>
    </SectionShell>
  );
}

export function HistoricoDemandaSection({ demanda }: { demanda: Demanda }) {
  return (
    <SectionShell title="Histórico" description="Eventos registrados para auditoria." icon={<History className="h-5 w-5" />}>
      <div className="space-y-3">
        {demanda.historico.map((evento) => (
          <div key={evento.id} className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/30">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex gap-3">
                <span className="mt-1 h-2.5 w-2.5 rounded-full bg-indigo-500" />
                <div>
                  <p className="font-semibold text-zinc-950 dark:text-zinc-50">{evento.acao}</p>
                  <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                    {evento.usuario} · {evento.dataHora}
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap justify-end gap-1.5">
                {evento.tipo && evento.tipo !== "outro" && (
                  <Badge tone={evento.tipo === "refacao" ? "red" : evento.tipo === "ajuste_cliente" ? "amber" : "blue"}>
                    {evento.tipo === "ajuste_interno" ? "Ajuste interno" : evento.tipo === "ajuste_cliente" ? "Ajuste cliente" : "Refação"}
                  </Badge>
                )}
                <Badge tone="neutral">{evento.dispositivo}</Badge>
              </div>
            </div>
            <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400">IP: {evento.ip}</p>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}
