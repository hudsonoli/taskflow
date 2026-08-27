"use client";

import type { ReactNode } from "react";
import { Archive, FileText, History, Plus, Trash2, UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { prioridadeProjetoLabels, statusProjetoLabels } from "@/lib/projetos";
import type { Projeto, ProjetoEquipeMembro, ProjetoPrioridade, ProjetoStatusEditavel } from "@/types/projeto";

/**
 * Hoje todas as seções são consumidas apenas pelo painel de leitura (ProjetoDetailsDrawer).
 * `onChange` continua opcional para o caso de uma tela de edição em linha voltar, mas
 * `somenteLeitura` é o modo em uso: com persistência real, editar em linha viraria um PATCH
 * por tecla digitada. A edição acontece no NovoProjetoModal, que salva de uma vez.
 */
type ProjetoSectionProps = {
  projeto: Projeto;
  onChange?: (projeto: Projeto) => void;
  somenteLeitura?: boolean;
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

function updateProjeto(
  projeto: Projeto,
  patch: Partial<Projeto>,
  onChange?: (projeto: Projeto) => void,
) {
  onChange?.({ ...projeto, ...patch });
}

export function DadosProjetoSection({ projeto, onChange, somenteLeitura }: ProjetoSectionProps) {
  const { clientes } = useDiretorioClientes();
  const { usuarios } = useDiretorioUsuarios();
  const { departamentos } = useDiretorioDepartamentos();

  const nomeCliente =
    clientes.find((cliente) => cliente.id === projeto.clienteId)?.nome ?? "Sem cliente";
  const nomesResponsaveis =
    projeto.responsavelIds
      .map((id) => usuarios.find((usuario) => usuario.id === id)?.nome ?? id)
      .join(", ") || "-";
  const nomesDepartamentos =
    projeto.departamentoResponsavelIds
      .map((id) => departamentos.find((departamento) => departamento.id === id)?.nome ?? id)
      .join(", ") || "-";

  return (
    <SectionShell title="Informações do projeto" description="Informações principais do cadastro." icon={<FileText className="h-5 w-5" />}>
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone="blue">{statusProjetoLabels[projeto.status]}</Badge>
        <Badge tone="neutral">{prioridadeProjetoLabels[projeto.prioridade]}</Badge>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {/* O código de referência é a identidade de negócio — imutável, por isso desabilitado. */}
        <Input label="Código" value={projeto.codigoReferencia} disabled />
        <Input label="Cliente" value={nomeCliente} disabled />
        <Input
          label="Campanha"
          disabled={somenteLeitura}
          value={projeto.campanha}
          onChange={(event) => updateProjeto(projeto, { campanha: event.target.value }, onChange)}
        />
        <Input
          label="Data de início"
          disabled={somenteLeitura}
          type="date"
          value={projeto.dataInicio}
          onChange={(event) => updateProjeto(projeto, { dataInicio: event.target.value }, onChange)}
        />
        <Input
          label="Data prevista"
          disabled={somenteLeitura}
          type="date"
          value={projeto.dataFimPrevista}
          onChange={(event) => updateProjeto(projeto, { dataFimPrevista: event.target.value }, onChange)}
        />
        <Select
          label="Status"
          disabled={somenteLeitura}
          value={projeto.status}
          onChange={(event) =>
            updateProjeto(projeto, { status: event.target.value as ProjetoStatusEditavel }, onChange)
          }
          // `arquivado` fica fora: entra pela ação Arquivar, com motivo obrigatório.
          options={Object.entries(statusProjetoLabels)
            .filter(([value]) => value !== "arquivado")
            .map(([value, label]) => ({ value, label }))}
        />
        <Select
          label="Prioridade"
          disabled={somenteLeitura}
          value={projeto.prioridade}
          onChange={(event) => updateProjeto(projeto, { prioridade: event.target.value as ProjetoPrioridade }, onChange)}
          options={Object.entries(prioridadeProjetoLabels).map(([value, label]) => ({ value, label }))}
        />
      </div>

      <div className="mt-4 rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-400">Responsáveis</p>
        {/* MultiSelect não tem modo desabilitado; em leitura os nomes já aparecem nos
            campos "selecionados" logo abaixo, então o seletor simplesmente não é montado. */}
        {!somenteLeitura && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <MultiSelect
            label="Usuários responsáveis"
            values={projeto.responsavelIds}
            onChange={(values) => updateProjeto(projeto, { responsavelIds: values }, onChange)}
            options={usuarios
              .filter((usuario) => usuario.status === "ativo")
              .map((usuario) => ({ value: usuario.id, label: usuario.nome }))}
          />
          <MultiSelect
            label="Departamentos responsáveis"
            values={projeto.departamentoResponsavelIds}
            onChange={(values) => updateProjeto(projeto, { departamentoResponsavelIds: values }, onChange)}
            options={departamentos
              .filter((departamento) => departamento.status === "ativo")
              .map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
          />
        </div>
        )}
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <Input label="Usuários selecionados" value={nomesResponsaveis} disabled />
          <Input label="Departamentos selecionados" value={nomesDepartamentos} disabled />
        </div>
      </div>

      <div className="mt-4">
        <Textarea
          label="Descrição"
          disabled={somenteLeitura}
          rows={4}
          value={projeto.descricao}
          onChange={(event) => updateProjeto(projeto, { descricao: event.target.value }, onChange)}
        />
      </div>
    </SectionShell>
  );
}

export function ResumoProjetoSection({ projeto, onChange, somenteLeitura }: ProjetoSectionProps) {
  return (
    <SectionShell title="Resumo operacional" description="Conteúdo exibido futuramente nas demandas vinculadas." icon={<FileText className="h-5 w-5" />}>
      <Textarea
        label="Resumo do projeto"
        disabled={somenteLeitura}
        rows={8}
        value={projeto.resumo}
        onChange={(event) => updateProjeto(projeto, { resumo: event.target.value }, onChange)}
      />
    </SectionShell>
  );
}

/**
 * Equipe do projeto.
 *
 * A chave do membro é o `usuarioId` — não há mais id próprio de vínculo. Nome e
 * departamento vêm do diretório de usuários, não são gravados junto: duplicá-los criaria
 * dois lugares para a mesma verdade (ver docstring de app/models/projeto_equipe_membro.py).
 */
export function EquipeProjetoSection({ projeto, onChange, somenteLeitura }: ProjetoSectionProps) {
  const { usuarios } = useDiretorioUsuarios();
  const jaNaEquipe = new Set(projeto.equipe.map((membro) => membro.usuarioId));
  const disponiveis = usuarios.filter(
    (usuario) => usuario.status === "ativo" && !jaNaEquipe.has(usuario.id),
  );

  function updateMember(usuarioId: string, patch: Partial<ProjetoEquipeMembro>) {
    updateProjeto(
      projeto,
      {
        equipe: projeto.equipe.map((membro) =>
          membro.usuarioId === usuarioId ? { ...membro, ...patch } : membro,
        ),
      },
      onChange,
    );
  }

  return (
    <SectionShell
      title="Equipe do projeto"
      description="Pessoas alocadas e a função que exercem neste projeto."
      icon={<UsersRound className="h-5 w-5" />}
      action={
        <Button
          type="button"
          disabled={somenteLeitura || disponiveis.length === 0}
          onClick={() =>
            updateProjeto(
              projeto,
              { equipe: [...projeto.equipe, { usuarioId: disponiveis[0].id, funcao: "" }] },
              onChange,
            )
          }
          className="px-3 py-1.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" />
          Adicionar membro
        </Button>
      }
    >
      {projeto.equipe.length === 0 ? (
        <EmptyState title="Nenhum membro alocado" description="Adicione as pessoas que trabalham neste projeto." icon={<UsersRound size={16} />} />
      ) : (
        <div className="space-y-3">
          {projeto.equipe.map((membro) => {
            const usuario = usuarios.find((item) => item.id === membro.usuarioId);
            return (
              <div
                key={membro.usuarioId}
                className="grid gap-3 rounded-2xl border border-zinc-100 bg-zinc-50/60 p-4 dark:border-zinc-800 dark:bg-zinc-950/30 md:grid-cols-[1fr_1fr_auto]"
              >
                <Select
                  label="Pessoa"
                  value={membro.usuarioId}
                  onChange={(event) => updateMember(membro.usuarioId, { usuarioId: event.target.value })}
                  options={[
                    // A própria pessoa continua na lista, senão o Select ficaria sem o valor atual.
                    ...(usuario ? [{ value: usuario.id, label: usuario.nome }] : []),
                    ...disponiveis.map((item) => ({ value: item.id, label: item.nome })),
                  ]}
                />
                <Input
                  label="Função no projeto"
                  value={membro.funcao}
                  placeholder="ex.: Direção de arte"
                  onChange={(event) => updateMember(membro.usuarioId, { funcao: event.target.value })}
                />
                <div className="flex items-end">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() =>
                      updateProjeto(
                        projeto,
                        { equipe: projeto.equipe.filter((item) => item.usuarioId !== membro.usuarioId) },
                        onChange,
                      )
                    }
                    className="px-3 py-1.5 text-xs"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Remover
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
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

/**
 * Projeto não tem mais `historico[]`: cada mudança relevante vira evento de domínio
 * (`projeto.*`), publicado na mesma transação da escrita. A tela de auditoria que consome
 * esses eventos é trabalho próprio — até lá, o histórico não é exibido aqui em vez de ser
 * exibido a partir de um campo que não existe mais.
 */
export function HistoricoProjetoSection() {
  return (
    <SectionShell title="Histórico" description="Eventos registrados para auditoria." icon={<History className="h-5 w-5" />}>
      <EmptyState
        title="Histórico registrado como evento de domínio"
        description="Criação, alteração, arquivamento e restauração são gravados em eventos. A visualização será entregue junto da tela de auditoria."
        icon={<History size={16} />}
      />
    </SectionShell>
  );
}
