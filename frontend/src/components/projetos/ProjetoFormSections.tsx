import type { ReactNode } from "react";
import { Archive, FileText, History, Layers3, Plus, Trash2, UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  departamentosProjetoDisponiveis,
  generateId,
  prioridadeProjetoLabels,
  resolveClienteProjetoNome,
  resolveDepartamentosProjetoNomes,
  resolveResponsaveisProjetoNomes,
  responsaveisProjetoDisponiveis,
  statusProjetoLabels,
  tiposTarefaProjetoDisponiveis,
  workflowsProjetoDisponiveis,
} from "@/lib/projetos-mock";
import type {
  Projeto,
  ProjetoEquipeMembro,
  ProjetoModeloCampanhaItem,
  ProjetoPrioridade,
  ProjetoStatus,
} from "@/types/projeto";

type ProjetoSectionProps = {
  projeto: Projeto;
  onChange: (projeto: Projeto) => void;
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
    <section className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-5">
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

function updateProjeto(projeto: Projeto, patch: Partial<Projeto>, onChange: (projeto: Projeto) => void) {
  onChange({ ...projeto, ...patch, updatedAt: new Date().toISOString() });
}

export function DadosProjetoSection({ projeto, onChange }: ProjetoSectionProps) {
  return (
    <SectionShell title="Informações do projeto" description="Informações principais e campos reservados para integrações futuras." icon={<FileText className="h-5 w-5" />}>
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone="blue">{statusProjetoLabels[projeto.status]}</Badge>
        <Badge tone="neutral">{prioridadeProjetoLabels[projeto.prioridade]}</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Input label="Código interno" value={projeto.codigoInterno} disabled />
        <Input label="Cliente" value={resolveClienteProjetoNome(projeto.clienteId)} disabled />
        <Input
          label="Campanha"
          value={projeto.campanha}
          onChange={(event) => updateProjeto(projeto, { campanha: event.target.value }, onChange)}
        />
        <Input
          label="Data de início"
          type="date"
          value={projeto.dataInicio}
          onChange={(event) => updateProjeto(projeto, { dataInicio: event.target.value }, onChange)}
        />
        <Input
          label="Data prevista"
          type="date"
          value={projeto.dataFimPrevista}
          onChange={(event) => updateProjeto(projeto, { dataFimPrevista: event.target.value }, onChange)}
        />
        <Select
          label="Status"
          value={projeto.status}
          onChange={(event) => updateProjeto(projeto, { status: event.target.value as ProjetoStatus }, onChange)}
          options={Object.entries(statusProjetoLabels).map(([value, label]) => ({ value, label }))}
        />
        <Select
          label="Prioridade"
          value={projeto.prioridade}
          onChange={(event) => updateProjeto(projeto, { prioridade: event.target.value as ProjetoPrioridade }, onChange)}
          options={Object.entries(prioridadeProjetoLabels).map(([value, label]) => ({ value, label }))}
        />
      </div>

      <div className="mt-4 rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">Responsáveis</p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <MultiSelect
            label="Usuários responsáveis"
            values={projeto.responsavelIds}
            onChange={(values) => updateProjeto(projeto, { responsavelIds: values }, onChange)}
            options={responsaveisProjetoDisponiveis.map((responsavel) => ({ value: responsavel.id, label: responsavel.nome }))}
          />
          <MultiSelect
            label="Departamentos responsáveis"
            values={projeto.departamentoResponsavelIds}
            onChange={(values) => updateProjeto(projeto, { departamentoResponsavelIds: values }, onChange)}
            options={departamentosProjetoDisponiveis.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
          />
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <Input label="Usuários selecionados" value={resolveResponsaveisProjetoNomes(projeto.responsavelIds)} disabled />
          <Input label="Departamentos selecionados" value={resolveDepartamentosProjetoNomes(projeto.departamentoResponsavelIds)} disabled />
        </div>
      </div>

      <div className="mt-4">
        <Textarea
          label="Descrição"
          rows={4}
          value={projeto.descricao}
          onChange={(event) => updateProjeto(projeto, { descricao: event.target.value }, onChange)}
        />
      </div>
    </SectionShell>
  );
}

export function ResumoProjetoSection({ projeto, onChange }: ProjetoSectionProps) {
  return (
    <SectionShell title="Resumo operacional" description="Conteúdo exibido futuramente nas demandas vinculadas." icon={<FileText className="h-5 w-5" />}>
      <Textarea
        label="Resumo do projeto"
        rows={8}
        value={projeto.resumo}
        onChange={(event) => updateProjeto(projeto, { resumo: event.target.value }, onChange)}
      />
    </SectionShell>
  );
}

function createModeloCampanhaItem(): ProjetoModeloCampanhaItem {
  return {
    id: generateId("modelo-item"),
    nomeDemanda: "Nova demanda padrão",
    tipoTarefaId: tiposTarefaProjetoDisponiveis[0].id,
    tipoTarefaNome: tiposTarefaProjetoDisponiveis[0].nome,
    briefingBase: "",
    prioridadePadrao: "media",
    workflowSugeridoId: workflowsProjetoDisponiveis[0].id,
    workflowSugeridoNome: workflowsProjetoDisponiveis[0].nome,
    responsavelOuSetorSugeridoId: departamentosProjetoDisponiveis[0].id,
    responsavelOuSetorSugeridoNome: departamentosProjetoDisponiveis[0].nome,
  };
}

export function ModeloCampanhaSection({ projeto, onChange }: ProjetoSectionProps) {
  function updateItem(itemId: string, patch: Partial<ProjetoModeloCampanhaItem>) {
    updateProjeto(
      projeto,
      { modeloCampanha: projeto.modeloCampanha.map((item) => (item.id === itemId ? { ...item, ...patch } : item)) },
      onChange,
    );
  }

  function removeItem(itemId: string) {
    updateProjeto(projeto, { modeloCampanha: projeto.modeloCampanha.filter((item) => item.id !== itemId) }, onChange);
  }

  return (
    <SectionShell
      title="Modelo de campanha"
      description="Backlog de demandas padrão para campanhas recorrentes."
      icon={<Layers3 className="h-5 w-5" />}
      action={
        <Button
          type="button"
          onClick={() =>
            updateProjeto(projeto, { modeloCampanha: [...projeto.modeloCampanha, createModeloCampanhaItem()] }, onChange)
          }
          className="px-3 py-1.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" />
          Adicionar item
        </Button>
      }
    >
      {projeto.modeloCampanha.length === 0 ? (
        <EmptyState title="Nenhum item no modelo" description="Adicione demandas padrão para campanhas recorrentes." icon={<Layers3 size={16} />} />
      ) : (
        <div className="space-y-4">
          {projeto.modeloCampanha.map((item) => (
            <div key={item.id} className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-zinc-950 dark:text-zinc-50">{item.nomeDemanda}</p>
                  <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                    {item.tipoTarefaNome} · {item.workflowSugeridoNome}
                  </p>
                </div>
                <Badge tone="blue">{prioridadeProjetoLabels[item.prioridadePadrao]}</Badge>
              </div>

              <div className="grid gap-3 lg:grid-cols-2">
                <Input label="Nome da demanda" value={item.nomeDemanda} onChange={(event) => updateItem(item.id, { nomeDemanda: event.target.value })} />
                <Select
                  label="Tipo de tarefa"
                  value={item.tipoTarefaId}
                  onChange={(event) => {
                    const selected = tiposTarefaProjetoDisponiveis.find((tipo) => tipo.id === event.target.value);
                    updateItem(item.id, { tipoTarefaId: event.target.value, tipoTarefaNome: selected?.nome ?? event.target.value });
                  }}
                  options={tiposTarefaProjetoDisponiveis.map((tipo) => ({ value: tipo.id, label: tipo.nome }))}
                />
                <Select
                  label="Prioridade padrão"
                  value={item.prioridadePadrao}
                  onChange={(event) => updateItem(item.id, { prioridadePadrao: event.target.value as ProjetoPrioridade })}
                  options={Object.entries(prioridadeProjetoLabels).map(([value, label]) => ({ value, label }))}
                />
                <Select
                  label="Workflow sugerido"
                  value={item.workflowSugeridoId}
                  onChange={(event) => {
                    const selected = workflowsProjetoDisponiveis.find((workflow) => workflow.id === event.target.value);
                    updateItem(item.id, { workflowSugeridoId: event.target.value, workflowSugeridoNome: selected?.nome ?? event.target.value });
                  }}
                  options={workflowsProjetoDisponiveis.map((workflow) => ({ value: workflow.id, label: workflow.nome }))}
                />
                <Select
                  label="Responsável/setor sugerido"
                  value={item.responsavelOuSetorSugeridoId}
                  onChange={(event) => {
                    const selected = departamentosProjetoDisponiveis.find((departamento) => departamento.id === event.target.value);
                    updateItem(item.id, {
                      responsavelOuSetorSugeridoId: event.target.value,
                      responsavelOuSetorSugeridoNome: selected?.nome ?? event.target.value,
                    });
                  }}
                  options={departamentosProjetoDisponiveis.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
                />
              </div>

              <div className="mt-3">
                <Textarea label="Briefing base" rows={4} value={item.briefingBase} onChange={(event) => updateItem(item.id, { briefingBase: event.target.value })} />
              </div>

              <div className="mt-3 flex justify-end">
                <Button type="button" variant="secondary" onClick={() => removeItem(item.id)} className="px-3 py-1.5 text-xs">
                  <Trash2 className="h-3.5 w-3.5" />
                  Remover item
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionShell>
  );
}

function createEquipeMembro(): ProjetoEquipeMembro {
  const departamento = departamentosProjetoDisponiveis[0];
  return {
    id: generateId("membro-projeto"),
    usuarioId: generateId("user-mock"),
    nome: "Novo membro",
    funcao: "Função no projeto",
    departamentoId: departamento.id,
    departamentoNome: departamento.nome,
  };
}

export function EquipeProjetoSection({ projeto, onChange }: ProjetoSectionProps) {
  function updateMember(memberId: string, patch: Partial<ProjetoEquipeMembro>) {
    updateProjeto(
      projeto,
      { equipe: projeto.equipe.map((membro) => (membro.id === memberId ? { ...membro, ...patch } : membro)) },
      onChange,
    );
  }

  return (
    <SectionShell
      title="Equipe do projeto"
      description="Membros vinculados localmente ao projeto."
      icon={<UsersRound className="h-5 w-5" />}
      action={
        <Button
          type="button"
          onClick={() => updateProjeto(projeto, { equipe: [...projeto.equipe, createEquipeMembro()] }, onChange)}
          className="px-3 py-1.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" />
          Adicionar membro
        </Button>
      }
    >
      <div className="space-y-3">
        {projeto.equipe.map((membro) => (
          <div key={membro.id} className="grid gap-3 rounded-2xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30 md:grid-cols-[1fr_1fr_1fr_auto]">
            <Input label="Nome" value={membro.nome} onChange={(event) => updateMember(membro.id, { nome: event.target.value })} />
            <Input label="Função" value={membro.funcao} onChange={(event) => updateMember(membro.id, { funcao: event.target.value })} />
            <Select
              label="Departamento"
              value={membro.departamentoId}
              onChange={(event) => {
                const selected = departamentosProjetoDisponiveis.find((departamento) => departamento.id === event.target.value);
                updateMember(membro.id, { departamentoId: event.target.value, departamentoNome: selected?.nome ?? event.target.value });
              }}
              options={departamentosProjetoDisponiveis.map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
            />
            <div className="flex items-end">
              <Button
                type="button"
                variant="secondary"
                onClick={() =>
                  updateProjeto(projeto, { equipe: projeto.equipe.filter((item) => item.id !== membro.id) }, onChange)
                }
                className="px-3 py-1.5 text-xs"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remover
              </Button>
            </div>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}

export function ArquivosProjetoSection() {
  return (
    <SectionShell title="Arquivos" description="Área reservada para anexos futuros do projeto." icon={<Archive className="h-5 w-5" />}>
      <EmptyState title="Nenhum arquivo anexado" description="O upload real de arquivos será tratado em fase futura." icon={<Archive size={16} />} />
    </SectionShell>
  );
}

export function HistoricoProjetoSection({ projeto }: { projeto: Projeto }) {
  return (
    <SectionShell title="Histórico" description="Eventos registrados para auditoria." icon={<History className="h-5 w-5" />}>
      <div className="space-y-3">
        {projeto.historico.map((evento) => (
          <div key={evento.id} className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
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
              <Badge tone="neutral">{evento.dispositivo}</Badge>
            </div>
            <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-400">IP: {evento.ip}</p>
          </div>
        ))}
      </div>
    </SectionShell>
  );
}
