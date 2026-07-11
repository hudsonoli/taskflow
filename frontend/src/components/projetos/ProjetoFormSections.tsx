import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { WorkspaceEmptyState } from "@/components/workspace/WorkspaceEmptyState";
import { WorkspaceSection } from "@/components/workspace/WorkspaceSection";
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
    <WorkspaceSection
      title="Dados"
      description="Informações principais do projeto e campos reservados para integrações futuras."
    >
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

      <div className="mt-4 grid gap-4 md:grid-cols-2">
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

      <div className="mt-4">
        <Textarea
          label="Descrição"
          rows={4}
          value={projeto.descricao}
          onChange={(event) =>
            updateProjeto(projeto, { descricao: event.target.value }, onChange)
          }
        />
      </div>
    </WorkspaceSection>
  );
}

export function ResumoProjetoSection({
  projeto,
  onChange,
}: ProjetoSectionProps) {
  return (
    <WorkspaceSection
      title="Resumo"
      description="Conteúdo operacional que será exibido futuramente nas demandas vinculadas."
    >
      <Textarea
        label="Resumo do projeto"
        rows={8}
        value={projeto.resumo}
        onChange={(event) =>
          updateProjeto(projeto, { resumo: event.target.value }, onChange)
        }
      />
    </WorkspaceSection>
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
    <WorkspaceSection
      title="Modelo de Campanha"
      description="Backlog mock para campanhas recorrentes. Não gera demandas reais nesta fase."
    >
      <div className="mb-4 flex justify-end">
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
        >
          Adicionar item
        </Button>
      </div>

      {projeto.modeloCampanha.length === 0 ? (
        <WorkspaceEmptyState
          title="Nenhum item no modelo"
          description="Adicione demandas padrão para campanhas recorrentes."
        />
      ) : (
        <div className="space-y-4">
          {projeto.modeloCampanha.map((item) => (
            <div
              key={item.id}
              className="rounded-3xl border border-zinc-100 bg-white p-4 shadow-sm"
            >
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
                      prioridadePadrao: event.target
                        .value as ProjetoPrioridade,
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
                      workflowSugeridoNome:
                        selected?.nome ?? event.target.value,
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
                >
                  Remover item
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </WorkspaceSection>
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
    <WorkspaceSection
      title="Equipe"
      description="Membros mock vinculados localmente ao projeto."
    >
      <div className="mb-4 flex justify-end">
        <Button
          type="button"
          onClick={() =>
            updateProjeto(
              projeto,
              { equipe: [...projeto.equipe, createEquipeMembro()] },
              onChange
            )
          }
        >
          Adicionar membro
        </Button>
      </div>

      <div className="space-y-3">
        {projeto.equipe.map((membro) => (
          <div
            key={membro.id}
            className="grid gap-3 rounded-3xl border border-zinc-100 p-4 md:grid-cols-[1fr_1fr_1fr_auto]"
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
              >
                Remover
              </Button>
            </div>
          </div>
        ))}
      </div>
    </WorkspaceSection>
  );
}

export function ArquivosProjetoSection() {
  return (
    <WorkspaceSection
      title="Arquivos"
      description="Área reservada para anexos futuros do projeto."
    >
      <WorkspaceEmptyState
        title="Nenhum arquivo anexado."
        description="O upload real de arquivos será tratado em fase futura."
      />

      <div className="mt-4 flex justify-end">
        <Button type="button" variant="secondary">
          Adicionar arquivo
        </Button>
      </div>
    </WorkspaceSection>
  );
}

export function HistoricoProjetoSection({ projeto }: { projeto: Projeto }) {
  return (
    <WorkspaceSection
      title="Histórico"
      description="Eventos mock preparados visualmente para auditoria futura."
    >
      <div className="space-y-3">
        {projeto.historico.map((evento) => (
          <div
            key={evento.id}
            className="rounded-3xl border border-zinc-100 bg-white p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium text-zinc-900">{evento.acao}</p>
                <p className="mt-1 text-sm text-zinc-500">
                  {evento.usuario} · {evento.dataHora}
                </p>
              </div>

              <Badge>{evento.dispositivo}</Badge>
            </div>

            <p className="mt-3 text-sm text-zinc-500">IP: {evento.ip}</p>
          </div>
        ))}
      </div>
    </WorkspaceSection>
  );
}
