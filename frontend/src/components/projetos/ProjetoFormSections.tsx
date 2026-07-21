import { useState } from "react";
import {
  Archive,
  CheckCircle2,
  FileText,
  History,
  Layers3,
  MessageSquare,
  Milestone,
  ListChecks,
  Plus,
  Trash2,
  UsersRound,
} from "lucide-react";
import { EntityHistory, type EntityHistoryEvent } from "@/components/entity";
import { Button } from "@/components/ui/Button";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Select } from "@/components/ui/Select";
import { StatusPill } from "@/components/ui/StatusPill";
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
  ProjetoAprovacaoStatus,
  ProjetoEquipeMembro,
  ProjetoModeloCampanhaItem,
  ProjetoPrioridade,
  ProjetoStatus,
} from "@/types/projeto";

type ProjetoSectionProps = {
  projeto: Projeto;
  onChange: (projeto: Projeto) => void;
};

type ProjetoSectionShellProps = {
  title: string;
  description: string;
  eyebrow: string;
  icon: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
};

export function ProjetoSectionShell({
  title,
  description,
  eyebrow,
  icon,
  action,
  children,
}: ProjetoSectionShellProps) {
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

function updateProjeto(
  projeto: Projeto,
  patch: Partial<Projeto>,
  onChange: (projeto: Projeto) => void
) {
  onChange({
    ...projeto,
    ...patch,
    updatedAt: new Date().toISOString(),
  });
}

export function DadosProjetoSection({ projeto, onChange }: ProjetoSectionProps) {
  return (
    <ProjetoSectionShell
      eyebrow="Dados"
      title="Informações do projeto"
      description="Informações principais do projeto e campos reservados para integrações futuras."
      icon={<FileText className="h-5 w-5" />}
    >
      <div className="mb-5 flex flex-wrap gap-2">
        <StatusPill tone="blue">{statusProjetoLabels[projeto.status]}</StatusPill>
        <StatusPill tone="neutral">
          {prioridadeProjetoLabels[projeto.prioridade]}
        </StatusPill>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Input label="Código interno" value={projeto.codigoInterno} disabled />
        <Input
          label="Cliente"
          value={resolveClienteProjetoNome(projeto.clienteId)}
          disabled
        />
        <Input
          label="Campanha"
          value={projeto.campanha}
          onChange={(event) =>
            updateProjeto(projeto, { campanha: event.target.value }, onChange)
          }
        />
        <Input
          label="Data de início"
          type="date"
          value={projeto.dataInicio}
          onChange={(event) =>
            updateProjeto(projeto, { dataInicio: event.target.value }, onChange)
          }
        />
        <Input
          label="Data prevista"
          type="date"
          value={projeto.dataFimPrevista}
          onChange={(event) =>
            updateProjeto(
              projeto,
              { dataFimPrevista: event.target.value },
              onChange
            )
          }
        />
        <Select
          label="Status"
          value={projeto.status}
          onChange={(event) =>
            updateProjeto(
              projeto,
              { status: event.target.value as ProjetoStatus },
              onChange
            )
          }
          options={Object.entries(statusProjetoLabels).map(([value, label]) => ({
            value,
            label,
          }))}
        />
        <Select
          label="Prioridade"
          value={projeto.prioridade}
          onChange={(event) =>
            updateProjeto(
              projeto,
              { prioridade: event.target.value as ProjetoPrioridade },
              onChange
            )
          }
          options={Object.entries(prioridadeProjetoLabels).map(
            ([value, label]) => ({
              value,
              label,
            })
          )}
        />
        <Input label="PIT do Publi" value="Integração futura" disabled />
        <Input label="OCs vinculadas" value="Consulta futura" disabled />
      </div>

      <div className="mt-5 rounded-3xl border border-zinc-100 bg-zinc-50/70 p-4">
        <SectionHeader
          eyebrow="Responsáveis"
          title="Usuários e departamentos"
          description="Relações preservadas por IDs, com nomes resolvidos apenas para exibição."
        />
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <MultiSelect
            label="Usuários responsáveis"
            placeholder="Selecione usuários"
            values={projeto.responsavelIds}
            onChange={(values) =>
              updateProjeto(projeto, { responsavelIds: values }, onChange)
            }
            options={responsaveisProjetoDisponiveis.map((responsavel) => ({
              value: responsavel.id,
              label: responsavel.nome,
            }))}
          />
          <MultiSelect
            label="Departamentos responsáveis"
            placeholder="Selecione departamentos"
            values={projeto.departamentoResponsavelIds}
            onChange={(values) =>
              updateProjeto(
                projeto,
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
            label="Usuários responsáveis selecionados"
            value={resolveResponsaveisProjetoNomes(projeto.responsavelIds)}
            disabled
          />
          <Input
            label="Departamentos responsáveis selecionados"
            value={resolveDepartamentosProjetoNomes(
              projeto.departamentoResponsavelIds
            )}
            disabled
          />
        </div>
      </div>

      <div className="mt-5">
        <Textarea
          label="Descrição"
          rows={4}
          value={projeto.descricao}
          onChange={(event) =>
            updateProjeto(projeto, { descricao: event.target.value }, onChange)
          }
        />
      </div>
    </ProjetoSectionShell>
  );
}

export function ResumoProjetoSection({
  projeto,
  onChange,
}: ProjetoSectionProps) {
  return (
    <ProjetoSectionShell
      eyebrow="Resumo"
      title="Resumo operacional"
      description="Conteúdo operacional que será exibido futuramente nas demandas vinculadas."
      icon={<FileText className="h-5 w-5" />}
    >
      <Textarea
        label="Resumo do projeto"
        rows={8}
        value={projeto.resumo}
        onChange={(event) =>
          updateProjeto(projeto, { resumo: event.target.value }, onChange)
        }
      />
    </ProjetoSectionShell>
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

export function ModeloCampanhaSection({
  projeto,
  onChange,
}: ProjetoSectionProps) {
  function updateItem(itemId: string, patch: Partial<ProjetoModeloCampanhaItem>) {
    updateProjeto(
      projeto,
      {
        modeloCampanha: projeto.modeloCampanha.map((item) =>
          item.id === itemId ? { ...item, ...patch } : item
        ),
      },
      onChange
    );
  }

  function removeItem(itemId: string) {
    updateProjeto(
      projeto,
      {
        modeloCampanha: projeto.modeloCampanha.filter(
          (item) => item.id !== itemId
        ),
      },
      onChange
    );
  }

  return (
    <ProjetoSectionShell
      eyebrow="Modelo"
      title="Modelo de Campanha"
      description="Backlog mock para campanhas recorrentes. Não gera demandas reais nesta fase."
      icon={<Layers3 className="h-5 w-5" />}
      action={
        <Button
          type="button"
          onClick={() =>
            updateProjeto(
              projeto,
              {
                modeloCampanha: [
                  ...projeto.modeloCampanha,
                  createModeloCampanhaItem(),
                ],
              },
              onChange
            )
          }
          className="inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Adicionar item
        </Button>
      }
    >
      {projeto.modeloCampanha.length === 0 ? (
        <EmptyStateIllustration
          title="Nenhum item no modelo"
          description="Adicione demandas padrão para campanhas recorrentes."
          icon={<Layers3 className="h-6 w-6" />}
        />
      ) : (
        <div className="space-y-4">
          {projeto.modeloCampanha.map((item) => (
            <div
              key={item.id}
              className="rounded-3xl border border-zinc-100 bg-zinc-50/60 p-4 shadow-sm"
            >
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-zinc-950">
                    {item.nomeDemanda}
                  </p>
                  <p className="mt-1 text-xs text-zinc-500">
                    {item.tipoTarefaNome} · {item.workflowSugeridoNome}
                  </p>
                </div>
                <StatusPill tone="blue">
                  {prioridadeProjetoLabels[item.prioridadePadrao]}
                </StatusPill>
              </div>

              <div className="grid gap-4 lg:grid-cols-2">
                <Input
                  label="Nome da demanda"
                  value={item.nomeDemanda}
                  onChange={(event) =>
                    updateItem(item.id, { nomeDemanda: event.target.value })
                  }
                />
                <Select
                  label="Tipo de tarefa"
                  value={item.tipoTarefaId}
                  onChange={(event) => {
                    const selected = tiposTarefaProjetoDisponiveis.find(
                      (tipo) => tipo.id === event.target.value
                    );
                    updateItem(item.id, {
                      tipoTarefaId: event.target.value,
                      tipoTarefaNome: selected?.nome ?? event.target.value,
                    });
                  }}
                  options={tiposTarefaProjetoDisponiveis.map((tipo) => ({
                    value: tipo.id,
                    label: tipo.nome,
                  }))}
                />
                <Select
                  label="Prioridade padrão"
                  value={item.prioridadePadrao}
                  onChange={(event) =>
                    updateItem(item.id, {
                      prioridadePadrao: event.target.value as ProjetoPrioridade,
                    })
                  }
                  options={Object.entries(prioridadeProjetoLabels).map(
                    ([value, label]) => ({ value, label })
                  )}
                />
                <Select
                  label="Workflow sugerido"
                  value={item.workflowSugeridoId}
                  onChange={(event) => {
                    const selected = workflowsProjetoDisponiveis.find(
                      (workflow) => workflow.id === event.target.value
                    );
                    updateItem(item.id, {
                      workflowSugeridoId: event.target.value,
                      workflowSugeridoNome: selected?.nome ?? event.target.value,
                    });
                  }}
                  options={workflowsProjetoDisponiveis.map((workflow) => ({
                    value: workflow.id,
                    label: workflow.nome,
                  }))}
                />
                <Select
                  label="Responsável/setor sugerido"
                  value={item.responsavelOuSetorSugeridoId}
                  onChange={(event) => {
                    const selected = departamentosProjetoDisponiveis.find(
                      (departamento) => departamento.id === event.target.value
                    );
                    updateItem(item.id, {
                      responsavelOuSetorSugeridoId: event.target.value,
                      responsavelOuSetorSugeridoNome:
                        selected?.nome ?? event.target.value,
                    });
                  }}
                  options={departamentosProjetoDisponiveis.map(
                    (departamento) => ({
                      value: departamento.id,
                      label: departamento.nome,
                    })
                  )}
                />
              </div>

              <div className="mt-4">
                <Textarea
                  label="Briefing base"
                  rows={4}
                  value={item.briefingBase}
                  onChange={(event) =>
                    updateItem(item.id, { briefingBase: event.target.value })
                  }
                />
              </div>

              <div className="mt-4 flex justify-end">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => removeItem(item.id)}
                  className="inline-flex items-center gap-2"
                >
                  <Trash2 className="h-4 w-4" />
                  Remover item
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </ProjetoSectionShell>
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

export function EquipeProjetoSection({
  projeto,
  onChange,
}: ProjetoSectionProps) {
  function updateMember(memberId: string, patch: Partial<ProjetoEquipeMembro>) {
    updateProjeto(
      projeto,
      {
        equipe: projeto.equipe.map((membro) =>
          membro.id === memberId ? { ...membro, ...patch } : membro
        ),
      },
      onChange
    );
  }

  return (
    <ProjetoSectionShell
      eyebrow="Equipe"
      title="Equipe do projeto"
      description="Membros mock vinculados localmente ao projeto."
      icon={<UsersRound className="h-5 w-5" />}
      action={
        <Button
          type="button"
          onClick={() =>
            updateProjeto(
              projeto,
              { equipe: [...projeto.equipe, createEquipeMembro()] },
              onChange
            )
          }
          className="inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Adicionar membro
        </Button>
      }
    >
      <div className="space-y-3">
        {projeto.equipe.map((membro) => (
          <div
            key={membro.id}
            className="grid gap-3 rounded-3xl border border-zinc-100 bg-zinc-50/60 p-4 md:grid-cols-[1fr_1fr_1fr_auto]"
          >
            <Input
              label="Nome"
              value={membro.nome}
              onChange={(event) =>
                updateMember(membro.id, { nome: event.target.value })
              }
            />
            <Input
              label="Função"
              value={membro.funcao}
              onChange={(event) =>
                updateMember(membro.id, { funcao: event.target.value })
              }
            />
            <Select
              label="Departamento"
              value={membro.departamentoId}
              onChange={(event) => {
                const selected = departamentosProjetoDisponiveis.find(
                  (departamento) => departamento.id === event.target.value
                );
                updateMember(membro.id, {
                  departamentoId: event.target.value,
                  departamentoNome: selected?.nome ?? event.target.value,
                });
              }}
              options={departamentosProjetoDisponiveis.map((departamento) => ({
                value: departamento.id,
                label: departamento.nome,
              }))}
            />
            <div className="flex items-end">
              <Button
                type="button"
                variant="secondary"
                onClick={() =>
                  updateProjeto(
                    projeto,
                    {
                      equipe: projeto.equipe.filter(
                        (item) => item.id !== membro.id
                      ),
                    },
                    onChange
                  )
                }
                className="inline-flex items-center gap-2"
              >
                <Trash2 className="h-4 w-4" />
                Remover
              </Button>
            </div>
          </div>
        ))}
      </div>
    </ProjetoSectionShell>
  );
}

export function ArquivosProjetoSection({ projeto }: { projeto: Projeto }) {
  return (
    <ProjetoSectionShell
      eyebrow="Arquivos"
      title="Arquivos"
      description="Área reservada para anexos do projeto. Upload real será tratado em fase futura."
      icon={<Archive className="h-5 w-5" />}
    >
      {projeto.arquivos.length === 0 ? (
        <EmptyStateIllustration
          title="Nenhum arquivo anexado."
          description="O upload real de arquivos será tratado em fase futura."
          icon={<Archive className="h-6 w-6" />}
          action={
            <Button type="button" variant="secondary" disabled>
              Adicionar arquivo
            </Button>
          }
        />
      ) : (
        <div className="space-y-2">
          {projeto.arquivos.map((arquivo) => (
            <div
              key={arquivo.id}
              className="flex items-center gap-3 rounded-2xl border border-zinc-100 px-3 py-2.5 transition hover:bg-zinc-50"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-zinc-100 text-zinc-500">
                <FileText className="h-4 w-4" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-zinc-800">{arquivo.nome}</p>
                <p className="text-[11px] text-zinc-400">
                  {arquivo.tipo} · {arquivo.tamanho} · {arquivo.usuarioNome} · {arquivo.criadoEm}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </ProjetoSectionShell>
  );
}

export function HistoricoProjetoSection({ projeto }: { projeto: Projeto }) {
  return (
    <ProjetoSectionShell
      eyebrow="Histórico"
      title="Histórico"
      description="Eventos mock preparados visualmente para auditoria futura."
      icon={<History className="h-5 w-5" />}
    >
      <EntityHistory
        variant="full"
        events={projeto.historico.map((evento) => ({
          id: evento.id,
          usuario: evento.usuario,
          dataHora: evento.dataHora,
          acao: evento.acao,
          ipOrigem: evento.ip,
          dispositivo: evento.dispositivo,
        }))}
      />
    </ProjetoSectionShell>
  );
}

export function TimelineProjetoSection({ projeto }: { projeto: Projeto }) {
  const events: EntityHistoryEvent[] = [
    ...projeto.historico.map((evento) => ({
      id: evento.id,
      usuario: evento.usuario,
      dataHora: evento.dataHora,
      acao: evento.acao,
      ipOrigem: evento.ip,
      dispositivo: evento.dispositivo,
      origem: "Evento",
    })),
    ...projeto.comentarios.map((comentario) => ({
      id: comentario.id,
      usuario: comentario.autorNome,
      dataHora: comentario.createdAt,
      acao: `Comentou: "${comentario.texto}"`,
      origem: "Comentário",
    })),
    ...projeto.arquivos.map((arquivo) => ({
      id: arquivo.id,
      usuario: arquivo.usuarioNome,
      dataHora: arquivo.criadoEm,
      acao: `Anexou o arquivo "${arquivo.nome}"`,
      origem: "Arquivo",
    })),
  ].sort((a, b) => (a.dataHora < b.dataHora ? 1 : -1));

  return (
    <ProjetoSectionShell
      eyebrow="Timeline"
      title="Linha do tempo"
      description="Combina eventos, comentários e arquivos do projeto em ordem cronológica — mesma composição prevista para a Timeline real (docs/arquitetura-taskfloww/02-modelo-dados-futuro.md, seção 6.3)."
      icon={<Milestone className="h-5 w-5" />}
    >
      <EntityHistory variant="full" events={events} />
    </ProjetoSectionShell>
  );
}

export function ChecklistProjetoSection({ projeto, onChange }: ProjetoSectionProps) {
  const [novoItem, setNovoItem] = useState("");
  const concluidos = projeto.checklist.filter((item) => item.concluido).length;
  const total = projeto.checklist.length;

  function toggleItem(itemId: string) {
    updateProjeto(
      projeto,
      {
        checklist: projeto.checklist.map((item) =>
          item.id === itemId
            ? {
                ...item,
                concluido: !item.concluido,
                concluidoEm: !item.concluido ? new Date().toLocaleString("pt-BR") : undefined,
                concluidoPor: !item.concluido ? "Hudson Cunha" : undefined,
              }
            : item
        ),
      },
      onChange
    );
  }

  function removeItem(itemId: string) {
    updateProjeto(
      projeto,
      { checklist: projeto.checklist.filter((item) => item.id !== itemId) },
      onChange
    );
  }

  function addItem() {
    if (!novoItem.trim()) return;

    updateProjeto(
      projeto,
      {
        checklist: [
          ...projeto.checklist,
          { id: generateId("checklist-projeto"), descricao: novoItem.trim(), concluido: false },
        ],
      },
      onChange
    );
    setNovoItem("");
  }

  return (
    <ProjetoSectionShell
      eyebrow="Checklist"
      title="Checklist do projeto"
      description={
        total > 0
          ? `${concluidos} de ${total} concluídos.`
          : "Itens de verificação preparados para acompanhamento do projeto."
      }
      icon={<ListChecks className="h-5 w-5" />}
    >
      {projeto.checklist.length === 0 ? (
        <EmptyStateIllustration
          title="Nenhum item no checklist"
          description="Adicione itens de verificação para acompanhar este projeto."
          icon={<ListChecks className="h-6 w-6" />}
        />
      ) : (
        <div className="space-y-2">
          {projeto.checklist.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-3 rounded-2xl border border-zinc-100 px-3 py-2.5 transition hover:bg-zinc-50"
            >
              <input
                type="checkbox"
                checked={item.concluido}
                onChange={() => toggleItem(item.id)}
                aria-label={item.descricao}
                className="mt-1 h-4 w-4 shrink-0 rounded border-zinc-300 text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-1"
              />

              <div className="min-w-0 flex-1">
                <p className={`text-sm ${item.concluido ? "text-zinc-400 line-through" : "text-zinc-800"}`}>
                  {item.descricao}
                </p>
                {item.concluido && item.concluidoPor && (
                  <p className="mt-0.5 text-[11px] text-zinc-400">
                    Concluído por {item.concluidoPor}
                    {item.concluidoEm ? ` · ${item.concluidoEm}` : ""}
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={() => removeItem(item.id)}
                aria-label="Remover item"
                className="shrink-0 rounded-full p-1 text-zinc-300 transition hover:bg-red-50 hover:text-red-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-1"
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-end gap-2">
        <Input
          label="Novo item"
          density="compact"
          placeholder="Descrever item do checklist"
          value={novoItem}
          onChange={(event) => setNovoItem(event.target.value)}
          className="flex-1"
        />
        <Button type="button" variant="secondary" size="sm" onClick={addItem} leftIcon={<Plus className="h-4 w-4" />}>
          Adicionar
        </Button>
      </div>
    </ProjetoSectionShell>
  );
}

export function ComentariosProjetoSection({ projeto, onChange }: ProjetoSectionProps) {
  const [texto, setTexto] = useState("");

  function addComentario() {
    if (!texto.trim()) return;

    updateProjeto(
      projeto,
      {
        comentarios: [
          {
            id: generateId("comentario-projeto"),
            autorId: "user-1",
            autorNome: "Hudson Cunha",
            texto: texto.trim(),
            createdAt: new Date().toLocaleString("pt-BR"),
          },
          ...projeto.comentarios,
        ],
      },
      onChange
    );
    setTexto("");
  }

  return (
    <ProjetoSectionShell
      eyebrow="Comentários"
      title="Comentários"
      description="Discussão e anotações contextuais do projeto."
      icon={<MessageSquare className="h-5 w-5" />}
    >
      <Textarea
        label="Novo comentário"
        density="compact"
        rows={2}
        placeholder="Escreva um comentário..."
        value={texto}
        onChange={(event) => setTexto(event.target.value)}
      />
      <div className="mt-2 flex justify-end">
        <Button type="button" variant="secondary" size="sm" onClick={addComentario}>
          Comentar
        </Button>
      </div>

      <div className="mt-5">
        {projeto.comentarios.length === 0 ? (
          <EmptyStateIllustration
            title="Nenhum comentário ainda"
            description="Comentários da equipe sobre este projeto aparecerão aqui."
            icon={<MessageSquare className="h-6 w-6" />}
          />
        ) : (
          <div className="space-y-3">
            {projeto.comentarios.map((comentario) => (
              <div key={comentario.id} className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-3">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-[11px] font-semibold text-white">
                    {comentario.autorNome
                      .split(" ")
                      .slice(0, 2)
                      .map((parte) => parte[0]?.toUpperCase())
                      .join("")}
                  </span>
                  <p className="text-sm font-semibold text-zinc-900">{comentario.autorNome}</p>
                  <span className="text-[11px] text-zinc-400">{comentario.createdAt}</span>
                </div>
                <p className="mt-2 text-sm text-zinc-700">{comentario.texto}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </ProjetoSectionShell>
  );
}

const aprovacaoTone: Record<ProjetoAprovacaoStatus, "green" | "amber" | "red"> = {
  aprovado: "green",
  pendente: "amber",
  rejeitado: "red",
};

const aprovacaoLabel: Record<ProjetoAprovacaoStatus, string> = {
  aprovado: "Aprovado",
  pendente: "Pendente",
  rejeitado: "Rejeitado",
};

// Somente leitura: aprovação é uma decisão de workflow (quem aprova, quando
// bloqueia), sem correspondência de regra definida ainda (ver tipo
// ProjetoAprovacao em types/projeto.ts) — ação de aprovar/rejeitar fica
// para quando essa regra for desenhada, não é UI state local como
// checklist/comentário.
export function AprovacoesProjetoSection({ projeto }: { projeto: Projeto }) {
  return (
    <ProjetoSectionShell
      eyebrow="Aprovações"
      title="Aprovações"
      description="Estrutura visual preparada para aprovações do projeto. Fluxo de solicitação/decisão ainda não definido."
      icon={<CheckCircle2 className="h-5 w-5" />}
    >
      {projeto.aprovacoes.length === 0 ? (
        <EmptyStateIllustration
          title="Nenhuma aprovação registrada"
          description="Solicitações de aprovação do projeto aparecerão aqui."
          icon={<CheckCircle2 className="h-6 w-6" />}
        />
      ) : (
        <div className="space-y-2">
          {projeto.aprovacoes.map((aprovacao) => (
            <div key={aprovacao.id} className="rounded-2xl border border-zinc-100 px-3 py-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-zinc-900">{aprovacao.titulo}</p>
                  {aprovacao.descricao && (
                    <p className="mt-1 text-xs text-zinc-500">{aprovacao.descricao}</p>
                  )}
                </div>
                <StatusPill tone={aprovacaoTone[aprovacao.status]}>
                  {aprovacaoLabel[aprovacao.status]}
                </StatusPill>
              </div>

              <p className="mt-2 text-[11px] text-zinc-400">
                Solicitado por {aprovacao.solicitadoPor} · {aprovacao.solicitadoEm}
                {aprovacao.respondidoPor
                  ? ` · Respondido por ${aprovacao.respondidoPor}${aprovacao.respondidoEm ? ` em ${aprovacao.respondidoEm}` : ""}`
                  : ""}
              </p>
            </div>
          ))}
        </div>
      )}
    </ProjetoSectionShell>
  );
}
