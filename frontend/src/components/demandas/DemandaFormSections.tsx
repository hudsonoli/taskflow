"use client";

import { useEffect, useState, type ReactNode } from "react";
import { ClipboardList, FileText, GitBranch, History, UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Combobox } from "@/components/ui/Combobox";
import { Input } from "@/components/ui/Input";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { MultiSelect } from "@/components/ui/MultiSelect";
import { Select } from "@/components/ui/Select";
import { listHistoricoDemanda, patchDemandaReal, type DemandaPatchCampos } from "@/lib/api-backend";
import {
  prioridadeDemandaLabels,
  resolveResponsaveisDemandaNomes,
  statusDemandaEditaveis,
  statusDemandaLabels,
} from "@/lib/demandas";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { corDoEventoHistorico, descreverEventoHistorico } from "@/lib/historicoDemandaLabels";
import { workflowEtapaTipoLabels } from "@/types/workflow-modelo";
import type { Demanda, DemandaHistoricoEvento, DemandaPrioridade, DemandaStatusEditavel } from "@/types/demanda";
import { RichTextEditor } from "@/components/ui/RichTextEditor";
import { DemandaArquivosCard } from "./DemandaArquivosCard";
import { DemandaChecklistCard } from "./DemandaChecklistCard";
import { EnvioClienteCard } from "./EnvioClienteCard";
import { RegistrarAjusteCard } from "./RegistrarAjusteCard";
import { useDiretorioClientes } from "@/lib/diretorioClientes";
import { rotuloDemanda } from "@/lib/referencias";

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

/**
 * Edição inline do drawer (Fase 2E.4 — correção do bug de persistência) — até esta fase,
 * `updateDemanda` só fazia `onChange({ ...demanda, ...patch })`: uma fusão local que nunca
 * chegava ao backend, porque `onChange` aqui é `DemandasView.handleDemandChange`, que é só
 * `setDemandas(...)`. Todo campo editado em `DadosDemandaSection`/`BriefingDemandaSection`/
 * `ResponsaveisDemandaSection` parecia salvo na tela e sumia no próximo carregamento.
 *
 * A correção reaproveita `patchDemandaReal` — o mesmo PATCH parcial já usado por
 * `DemandasView.aplicarStatus` e pelos cards corrigidos nesta mesma fase — em vez de duplicar
 * uma chamada de API própria aqui. `onChange` só é chamado com a Demanda **devolvida pelo
 * servidor**, nunca com um objeto fabricado localmente; se o PATCH falhar, nada muda no
 * estado do pai e o erro fica visível na própria seção.
 */
async function salvarCampo(
  demanda: Demanda,
  patch: DemandaPatchCampos,
  onChange: (demanda: Demanda) => void,
  setErro: (mensagem: string | null) => void,
): Promise<boolean> {
  setErro(null);
  try {
    const atualizada = await patchDemandaReal(demanda.id, patch);
    onChange(atualizada);
    return true;
  } catch (error) {
    setErro(error instanceof Error ? error.message : "Não foi possível salvar a alteração.");
    return false;
  }
}

export function DadosDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  const { projetos } = useDiretorioProjetos();
  const { clientes } = useDiretorioClientes();
  const [erro, setErro] = useState<string | null>(null);

  // PIT e prazo são texto/datetime-local — salvar a cada tecla faria um PATCH por tecla
  // (rede desnecessária e o campo "pisca" pro valor antigo entre o digitar e a resposta do
  // servidor). Guardado em estado local e só enviado no blur; Projeto/Cliente/Prioridade/
  // Status são seleção discreta (um evento por escolha), então salvam na hora, sem draft.
  //
  // Sem efeito para ressincronizar com `demanda.pit`/`demanda.prazoEtapaAtual`: o drawer
  // inteiro é remontado por `key={selectedDemand?.id}` (ver DemandasView.tsx) sempre que a
  // Demanda selecionada muda, então o `useState` abaixo já nasce com o valor certo a cada
  // Demanda diferente. Dentro da MESMA Demanda, o valor só muda por uma edição que este
  // próprio componente iniciou — sucesso já deixa local e prop iguais; falha já reverte
  // explicitamente em `salvarPit`/`salvarPrazo`, sem precisar de um efeito para isso.
  const [pit, setPit] = useState(demanda.pit ?? "");
  const [prazo, setPrazo] = useState(demanda.prazoEtapaAtual ?? "");

  async function handleProjetoChange(projetoId: string) {
    const projeto = projetos.find((item) => item.id === projetoId);
    await salvarCampo(demanda, { projetoId, clienteId: projeto?.clienteId ?? demanda.clienteId }, onChange, setErro);
  }

  async function salvarPit() {
    if (pit === (demanda.pit ?? "")) return;
    const ok = await salvarCampo(demanda, { pit: pit || null }, onChange, setErro);
    if (!ok) setPit(demanda.pit ?? "");
  }

  async function salvarPrazo() {
    if (prazo === (demanda.prazoEtapaAtual ?? "")) return;
    const ok = await salvarCampo(demanda, { prazoEtapaAtual: prazo || null }, onChange, setErro);
    if (!ok) setPrazo(demanda.prazoEtapaAtual ?? "");
  }

  return (
    <SectionShell title="Dados principais" description="Dados principais da tarefa e prazo da etapa atual." icon={<ClipboardList className="h-5 w-5" />}>
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone="blue">{prioridadeDemandaLabels[demanda.prioridade]}</Badge>
        <Badge tone="green">{statusDemandaLabels[demanda.status]}</Badge>
      </div>

      {erro && <p className="mb-3 text-xs text-red-600 dark:text-red-400">{erro}</p>}

      <div className="grid gap-3 md:grid-cols-2">
        <Input label="Código" value={rotuloDemanda(demanda)} disabled />
        <Input
          label="PIT (opcional)"
          placeholder="Ex: C3A-0008/26"
          value={pit}
          onChange={(event) => setPit(event.target.value)}
          onBlur={() => void salvarPit()}
        />
        <Combobox
          label="Projeto"
          value={demanda.projetoId ?? ""}
          onChange={(projetoId) => void handleProjetoChange(projetoId)}
          options={projetos.map((projeto) => ({ value: projeto.id, label: projeto.nome }))}
          placeholder="Buscar projeto…"
          emptyLabel="Nenhum projeto encontrado"
        />
        <Combobox
          label="Cliente"
          value={demanda.clienteId ?? ""}
          onChange={(clienteId) => void salvarCampo(demanda, { clienteId }, onChange, setErro)}
          options={clientes.map((cliente) => ({ value: cliente.id, label: cliente.nome }))}
          placeholder="Buscar cliente…"
          emptyLabel="Nenhum cliente encontrado"
        />
        <Input
          label="Prazo atual (data e horário)"
          type="datetime-local"
          value={prazo}
          onChange={(event) => setPrazo(event.target.value)}
          onBlur={() => void salvarPrazo()}
        />
        <Select
          label="Prioridade"
          value={demanda.prioridade}
          onChange={(event) =>
            void salvarCampo(demanda, { prioridade: event.target.value as DemandaPrioridade }, onChange, setErro)
          }
          options={Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label }))}
        />
        <Select
          label="Status"
          value={demanda.status}
          onChange={(event) =>
            void salvarCampo(demanda, { status: event.target.value as DemandaStatusEditavel }, onChange, setErro)
          }
          // `arquivada` fica fora de propósito — entra só pela rota de arquivamento, com
          // motivo obrigatório (mesma lista já usada em NovaDemandaModal).
          options={statusDemandaEditaveis.map((value) => ({ value, label: statusDemandaLabels[value] }))}
        />
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <EnvioClienteCard demanda={demanda} onChange={onChange} />
        <RegistrarAjusteCard demanda={demanda} />
      </div>
    </SectionShell>
  );
}

export function BriefingDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  const [erro, setErro] = useState<string | null>(null);
  // Sem efeito de ressincronização — mesmo raciocínio de DadosDemandaSection: o chamador já
  // usa `key={demanda.id}` (ver DemandaDetailsDrawer.tsx), então este componente remonta do
  // zero a cada Demanda diferente.
  const [briefing, setBriefing] = useState(demanda.briefing ?? "");

  async function salvarBriefing() {
    if (briefing === (demanda.briefing ?? "")) return;
    const ok = await salvarCampo(demanda, { briefing: briefing || null }, onChange, setErro);
    if (!ok) setBriefing(demanda.briefing ?? "");
  }

  return (
    <SectionShell title="Briefing" description="Use negrito, grifo e cor de fonte para destacar pontos do briefing." icon={<FileText className="h-5 w-5" />}>
      {erro && <p className="mb-3 text-xs text-red-600 dark:text-red-400">{erro}</p>}
      {/* RichTextEditor não expõe onBlur próprio — o blur do editable interno borbulha até
          aqui (React trata focus/blur como bubbling), então o wrapper capta o momento certo
          de salvar sem precisar alterar o componente compartilhado. */}
      <div onBlur={() => void salvarBriefing()}>
        <RichTextEditor value={briefing} onChange={setBriefing} />
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <DemandaChecklistCard demandaId={demanda.id} />
        <DemandaArquivosCard demandaId={demanda.id} />
      </div>
    </SectionShell>
  );
}

const workflowEtapaStatusTone = {
  pendente: "neutral",
  em_execucao: "green",
  pausada: "amber",
  concluida: "green",
} as const;

const workflowEtapaStatusLabel = {
  pendente: "Pendente",
  em_execucao: "Em execução",
  pausada: "Pausada",
  concluida: "Concluída",
} as const;

/**
 * Etapas materializadas na criação (Fase 2E.2) — leitura, não edição. Não há endpoint de
 * transição de etapa nesta fase (ver docstring de `DemandaWorkflowEtapa`), então esta seção
 * mostra o snapshot aplicado, sem controle de escrita — mesmo raciocínio de "affordance
 * ausente com explicação" que o contrato transitório já usava aqui.
 */
export function WorkflowDemandaSection({ demanda }: { demanda: Demanda }) {
  const { usuarios } = useDiretorioUsuarios();
  const { departamentos } = useDiretorioDepartamentos();

  if (demanda.workflowEtapas.length === 0) {
    return (
      <SectionShell title="Workflow" description="Etapas do fluxo de execução da tarefa." icon={<GitBranch className="h-5 w-5" />}>
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Esta tarefa não foi criada a partir de um modelo de workflow.
        </p>
      </SectionShell>
    );
  }

  return (
    <SectionShell
      title="Workflow"
      description="Etapas aplicadas na criação — modelo de origem não pode mais ser trocado."
      icon={<GitBranch className="h-5 w-5" />}
    >
      <div className="flex flex-col gap-3">
        {[...demanda.workflowEtapas]
          .sort((a, b) => a.ordem - b.ordem)
          .map((etapa) => {
            const atual = etapa.id === demanda.etapaAtualId;
            const responsaveis = etapa.usuarioResponsavelIds
              .map((id) => usuarios.find((usuario) => usuario.id === id)?.nome ?? id)
              .join(", ");
            const departamentosNomes = etapa.departamentoResponsavelIds
              .map((id) => departamentos.find((departamento) => departamento.id === id)?.nome ?? id)
              .join(", ");

            return (
              <div
                key={etapa.id}
                className={`rounded-2xl border p-3.5 ${
                  atual
                    ? "border-indigo-200 bg-indigo-50/40 dark:border-indigo-500/30 dark:bg-indigo-500/5"
                    : "border-zinc-100 bg-zinc-50/60 dark:border-zinc-800 dark:bg-zinc-950/30"
                }`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={workflowEtapaStatusTone[etapa.status]}>Etapa {etapa.ordem}</Badge>
                  {atual && <Badge tone="blue">Etapa atual</Badge>}
                  <Badge tone={etapa.tipo === "aprovacao" ? "amber" : "blue"}>
                    {workflowEtapaTipoLabels[etapa.tipo]}
                  </Badge>
                  <span className="text-xs text-zinc-500 dark:text-zinc-400">
                    {workflowEtapaStatusLabel[etapa.status]}
                  </span>
                </div>
                <p className="mt-1.5 text-sm font-semibold text-zinc-900 dark:text-zinc-100">{etapa.nome}</p>
                <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                  {responsaveis || departamentosNomes
                    ? [responsaveis, departamentosNomes].filter(Boolean).join(" · ")
                    : "Sem responsável definido"}
                </p>
              </div>
            );
          })}
      </div>
    </SectionShell>
  );
}

export function ResponsaveisDemandaSection({ demanda, onChange }: DemandaSectionProps) {
  const { departamentos } = useDiretorioDepartamentos();
  // Picker só oferece usuário ativo; referência histórica de inativo resolve nome/avatar
  // em outros lugares via resolverUsuarioPorReferencia (ver lib/referencias.ts).
  const diretorio = useDiretorioUsuarios().usuarios;
  const usuariosAtivos = diretorio.filter((usuario) => usuario.status === "ativo");
  const [erro, setErro] = useState<string | null>(null);

  const departamentosNomes = demanda.departamentoResponsavelIds
    .map((id) => departamentos.find((departamento) => departamento.id === id)?.nome ?? id)
    .join(", ") || "-";

  return (
    <SectionShell title="Responsáveis" description="Responsáveis principais por ID." icon={<UsersRound className="h-5 w-5" />}>
      {erro && <p className="mb-3 text-xs text-red-600 dark:text-red-400">{erro}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        <MemberSelector
          label="Usuários responsáveis"
          values={demanda.usuarioResponsavelIds}
          onChange={(values) => void salvarCampo(demanda, { usuarioResponsavelIds: values }, onChange, setErro)}
          placeholder="Selecionar responsáveis…"
          options={usuariosAtivos.map((usuario) => ({
            id: usuario.id,
            nome: usuario.nome,
            subtitulo: departamentos.find((departamento) => departamento.id === usuario.departamentoId)?.nome,
            corIdentificacao: usuario.corIdentificacao,
            fotoUrl: usuario.fotoUrl,
          }))}
        />
        <MultiSelect
          label="Departamentos responsáveis"
          values={demanda.departamentoResponsavelIds}
          onChange={(values) => void salvarCampo(demanda, { departamentoResponsavelIds: values }, onChange, setErro)}
          options={departamentos
            .filter((departamento) => departamento.status === "ativo")
            .map((departamento) => ({ value: departamento.id, label: departamento.nome }))}
        />
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Input label="Usuários selecionados" value={resolveResponsaveisDemandaNomes(demanda.usuarioResponsavelIds, diretorio)} disabled />
        <Input label="Departamentos selecionados" value={departamentosNomes} disabled />
      </div>
    </SectionShell>
  );
}

/**
 * Timeline real da Demanda (Fase 2E.4) — vem de `/demandas/{id}/historico`, que lê eventos
 * de domínio reais. Sem IP/dispositivo: nunca existiram no evento real, o mock inventava no
 * navegador (ver instrução da fase, item 8). Nome de usuário resolvido pelo diretório, com
 * fallback para autor removido/inativado (ver `descreverEventoHistorico`).
 */
export function HistoricoDemandaSection({ demanda }: { demanda: Demanda }) {
  const { usuarios } = useDiretorioUsuarios();
  const { departamentos } = useDiretorioDepartamentos();
  const [eventos, setEventos] = useState<DemandaHistoricoEvento[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let cancelado = false;
    listHistoricoDemanda(demanda.id)
      .then((dados) => {
        if (!cancelado) setEventos(dados);
      })
      .catch(() => {
        if (!cancelado) setErro("Não foi possível carregar o histórico.");
      })
      .finally(() => {
        if (!cancelado) setCarregando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [demanda.id]);

  function nomeUsuario(usuarioId: string | null): string {
    if (!usuarioId) return "Sistema";
    return usuarios.find((usuario) => usuario.id === usuarioId)?.nome ?? "Usuário removido";
  }

  return (
    <SectionShell title="Histórico" description="Eventos registrados para auditoria." icon={<History className="h-5 w-5" />}>
      {erro && <p className="mb-3 text-xs text-red-600 dark:text-red-400">{erro}</p>}
      {carregando ? (
        <p className="text-sm text-zinc-400">Carregando histórico…</p>
      ) : eventos.length === 0 ? (
        <p className="text-sm text-zinc-400">Nenhum evento registrado ainda.</p>
      ) : (
        <div className="space-y-3">
          {eventos.map((evento) => (
            <div key={evento.id} className="rounded-2xl border border-zinc-100 bg-zinc-50/60 p-3.5 dark:border-zinc-800 dark:bg-zinc-950/30">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex gap-3">
                  <span
                    className={`mt-1 h-2.5 w-2.5 rounded-full ${
                      {
                        blue: "bg-blue-500",
                        green: "bg-emerald-500",
                        amber: "bg-amber-500",
                        red: "bg-red-500",
                        neutral: "bg-zinc-400",
                      }[corDoEventoHistorico(evento.tipo)]
                    }`}
                  />
                  <div>
                    <p className="font-semibold text-zinc-950 dark:text-zinc-50">
                      {descreverEventoHistorico(evento, { usuarios, departamentos })}
                    </p>
                    <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
                      {nomeUsuario(evento.usuarioId)} · {new Date(evento.occurredAt).toLocaleString("pt-BR")}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </SectionShell>
  );
}
