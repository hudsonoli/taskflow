"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Building2,
  CalendarClock,
  CheckCircle2,
  Gauge,
  PauseCircle,
  Send,
  ShieldAlert,
  Timer,
  UserX,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Select";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { EstadoErro } from "@/components/operacional/EstadoErro";
import { IndicadoresGrid, type IndicadorItem } from "@/components/operacional/IndicadoresGrid";
import { TarefasLista } from "@/components/operacional/TarefasLista";
import { useAppData } from "@/lib/AppDataContext";
import { useDiretorioEquipes } from "@/lib/diretorioEquipes";
import { useDiretorioDepartamentos } from "@/lib/diretorioDepartamentos";
import { useDiretorioProjetos } from "@/lib/diretorioProjetos";
import { getHorasDepartamento } from "@/lib/api";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import { demandaTemResponsavel, normalizarUsuarioId, prioridadeDemandaLabels, statusDemandaLabels } from "@/lib/demandas";
import {
  capacidadeAproximada,
  classificarTarefa,
  detectarSobrecargaEstimada,
  formatHoras,
  horasEstimadasDemanda,
  podeAcessarMeuDepartamento,
  resolverHeadDepartamento,
  tarefasDoDepartamento,
} from "@/lib/escopo-operacional";
import type { DemandaPrioridade, DemandaStatus } from "@/types/demanda";
import { useDiretorioClientes } from "@/lib/diretorioClientes";

type PeriodoFiltro = "todos" | "hoje" | "semana" | "atrasadas";
type OrigemFiltro = "todos" | "interna" | "cliente";

const DIAS_UTEIS_SEMANA = 5;

export function MeuDepartamentoView() {
  const { demandas, regraExpediente, usuarioAtual } = useAppData();
  const { clientes } = useDiretorioClientes();
  const { equipes } = useDiretorioEquipes();
  const { departamentos } = useDiretorioDepartamentos();
  const { usuarios } = useDiretorioUsuarios();
  const { projetos } = useDiretorioProjetos();

  const [colaboradorId, setColaboradorId] = useState("");
  const [equipeId, setEquipeId] = useState("");
  const [clienteId, setClienteId] = useState("");
  const [projetoId, setProjetoId] = useState("");
  const [status, setStatus] = useState<DemandaStatus | "todos">("todos");
  const [prioridade, setPrioridade] = useState<DemandaPrioridade | "todos">("todos");
  const [periodo, setPeriodo] = useState<PeriodoFiltro>("todos");
  const [origem, setOrigem] = useState<OrigemFiltro>("todos");

  const [horasConsumidas, setHorasConsumidas] = useState(0);
  const [carregandoHoras, setCarregandoHoras] = useState(true);
  const [erroHoras, setErroHoras] = useState<string | null>(null);

  const departamentoHead = usuarioAtual ? resolverHeadDepartamento(usuarioAtual, departamentos) : undefined;
  const podeAcessar = usuarioAtual ? podeAcessarMeuDepartamento(usuarioAtual, departamentos) : false;

  async function carregarHoras(departamentoId: string) {
    setCarregandoHoras(true);
    setErroHoras(null);
    try {
      const resultado = await getHorasDepartamento(departamentoId);
      setHorasConsumidas(resultado.horasConsumidas);
    } catch (error) {
      setErroHoras(error instanceof Error ? error.message : "Não foi possível carregar as horas (API indisponível).");
    } finally {
      setCarregandoHoras(false);
    }
  }

  useEffect(() => {
    if (!departamentoHead) return;
    const timeoutId = setTimeout(() => {
      void carregarHoras(departamentoHead.id);
    }, 0);
    return () => clearTimeout(timeoutId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [departamentoHead?.id]);

  const tarefasDoDept = useMemo(
    () => (departamentoHead ? tarefasDoDepartamento(demandas, departamentoHead.id) : []),
    [demandas, departamentoHead],
  );

  // Colaborador estrutural do departamento = vínculo organizacional (usuarios.departamentoId),
  // não responsabilidade em Demanda — existe mesmo sem nenhuma tarefa atribuída ainda. Só
  // usuários ativos entram na base de capacidade/sobrecarga (mesmo padrão de
  // `UsuarioDiretorioItem` para listas selecionáveis).
  const colaboradoresOptions = useMemo(() => {
    if (!departamentoHead) return [];
    return usuarios.filter(
      (usuario) => usuario.departamentoId === departamentoHead.id && usuario.status === "ativo",
    );
  }, [usuarios, departamentoHead]);

  const clientesOptions = useMemo(() => {
    const ids = new Set(tarefasDoDept.map((demanda) => demanda.clienteId).filter(Boolean));
    return clientes.filter((cliente) => ids.has(cliente.id));
  }, [tarefasDoDept, clientes]);

  const projetosOptions = useMemo(() => {
    const ids = new Set(tarefasDoDept.map((demanda) => demanda.projetoId).filter(Boolean));
    return projetos.filter((projeto) => ids.has(projeto.id));
  }, [tarefasDoDept, projetos]);

  const tarefasFiltradas = useMemo(() => {
    return tarefasDoDept.filter((demanda) => {
      if (colaboradorId && !demandaTemResponsavel(demanda, colaboradorId, usuarios)) return false;
      if (equipeId) {
        const equipe = equipes.find((item) => item.id === equipeId);
        const membros = new Set(equipe?.membroIds ?? []);
        const temMembro = demanda.usuarioResponsavelIds.some((id) => membros.has(normalizarUsuarioId(id)));
        if (!temMembro) return false;
      }
      if (clienteId && demanda.clienteId !== clienteId) return false;
      if (projetoId && demanda.projetoId !== projetoId) return false;
      if (status !== "todos" && demanda.status !== status) return false;
      if (prioridade !== "todos" && demanda.prioridade !== prioridade) return false;

      const classificacao = classificarTarefa(demanda);
      if (periodo === "hoje" && !classificacao.previstaHoje) return false;
      if (periodo === "semana" && !classificacao.previstaSemana) return false;
      if (periodo === "atrasadas" && !classificacao.atrasada) return false;
      if (origem !== "todos" && classificacao.origem !== origem) return false;
      return true;
    });
  }, [tarefasDoDept, colaboradorId, equipeId, equipes, clienteId, projetoId, status, prioridade, periodo, origem, usuarios]);

  // Indicadores consideram todo o departamento (não os filtros) — os filtros afetam só a lista abaixo.
  const classificacoesDept = useMemo(() => tarefasDoDept.map((demanda) => classificarTarefa(demanda)), [tarefasDoDept]);
  const novas = classificacoesDept.filter((c) => c.nova).length;
  const semResponsavel = classificacoesDept.filter((c) => c.semResponsavel).length;
  const emAndamento = classificacoesDept.filter((c) => c.emAndamento).length;
  const pausadas = classificacoesDept.filter((c) => c.pausada).length;
  const aguardando = classificacoesDept.filter((c) => c.aguardando).length;
  const atrasadas = classificacoesDept.filter((c) => c.atrasada).length;
  const concluidas = classificacoesDept.filter((c) => c.concluida).length;

  const horasEstimadasTotal = tarefasDoDept.reduce((total, demanda) => total + horasEstimadasDemanda(demanda), 0);
  const capacidadeTotal = capacidadeAproximada(regraExpediente, colaboradoresOptions.length, DIAS_UTEIS_SEMANA);
  const capacidadeDisponivel = Math.max(0, capacidadeTotal - horasConsumidas);

  const colaboradoresSobrecarregados = colaboradoresOptions.filter((colaborador) => {
    const estimadoColaborador = tarefasDoDept
      .filter((demanda) => demandaTemResponsavel(demanda, colaborador.id, usuarios))
      .reduce((total, demanda) => total + horasEstimadasDemanda(demanda), 0);
    const capacidadeIndividual = capacidadeAproximada(regraExpediente, 1, DIAS_UTEIS_SEMANA);
    return detectarSobrecargaEstimada(estimadoColaborador, capacidadeIndividual).sobrecarregado;
  }).length;

  const indicadores: IndicadorItem[] = [
    { key: "novas", title: "Novas", value: novas, description: "Rascunho ou planejada.", icon: <CalendarClock size={16} />, tone: "blue" },
    { key: "sem-responsavel", title: "Sem responsável", value: semResponsavel, description: "Precisam de atribuição.", icon: <UserX size={16} />, tone: "amber" },
    { key: "andamento", title: "Em andamento", value: emAndamento, description: "Em execução agora.", icon: <Gauge size={16} />, tone: "green" },
    { key: "pausadas", title: "Pausadas", value: pausadas, description: "Pausadas ou bloqueadas.", icon: <PauseCircle size={16} />, tone: "amber" },
    { key: "aguardando", title: "Aguardando", value: aguardando, description: "Aguardando retorno do cliente.", icon: <Send size={16} />, tone: "amber" },
    { key: "atrasadas", title: "Atrasadas", value: atrasadas, description: "Prazo da etapa atual vencido.", icon: <AlertTriangle size={16} />, tone: "red" },
    { key: "concluidas", title: "Concluídas", value: concluidas, description: "Finalizadas.", icon: <CheckCircle2 size={16} />, tone: "green" },
    { key: "horas-estimadas", title: "Horas estimadas (aprox.)", value: formatHoras(horasEstimadasTotal), description: "Soma do workflow — estimativa derivada.", icon: <Timer size={16} />, tone: "neutral" },
    { key: "horas-consumidas", title: "Horas consumidas", value: carregandoHoras ? "…" : formatHoras(horasConsumidas), description: "Sessões de trabalho reais do departamento.", icon: <Timer size={16} />, tone: "neutral" },
    { key: "capacidade-disponivel", title: "Capacidade disponível (aprox.)", value: formatHoras(capacidadeDisponivel), description: "Capacidade aproximada da semana menos consumido.", icon: <Gauge size={16} />, tone: "blue" },
    { key: "sobrecarregados", title: "Colaboradores sobrecarregados", value: colaboradoresSobrecarregados, description: "Estimativa acima da capacidade aproximada.", icon: <ShieldAlert size={16} />, tone: colaboradoresSobrecarregados > 0 ? "red" : "neutral" },
  ];

  if (!usuarioAtual) return null;

  if (!podeAcessar || !departamentoHead) {
    return (
      <div className="flex flex-col gap-6">
        <Cabecalho nomeDepartamento={undefined} />
        <AcessoNegado
          titulo="Você não é Head de nenhum departamento"
          descricao="Esta visão é destinada aos responsáveis formais por um departamento. Fale com a Gestão se isso não estiver correto."
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <Cabecalho nomeDepartamento={departamentoHead.nome} />

      <IndicadoresGrid itens={indicadores} colunas={4} />

      {erroHoras && departamentoHead && (
        <EstadoErro
          mensagem={`${erroHoras} — horas consumidas ficaram indisponíveis.`}
          onRetry={() => void carregarHoras(departamentoHead.id)}
        />
      )}

      <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <p className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Filtros</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Select
            label="Colaborador"
            value={colaboradorId}
            onChange={(event) => setColaboradorId(event.target.value)}
            options={[{ value: "", label: "Todos" }, ...colaboradoresOptions.map((usuario) => ({ value: usuario.id, label: usuario.nome }))]}
          />
          <Select
            label="Equipe"
            value={equipeId}
            onChange={(event) => setEquipeId(event.target.value)}
            options={[{ value: "", label: "Todas" }, ...equipes.map((equipe) => ({ value: equipe.id, label: equipe.nome }))]}
          />
          <Select
            label="Cliente"
            value={clienteId}
            onChange={(event) => setClienteId(event.target.value)}
            options={[{ value: "", label: "Todos" }, ...clientesOptions.map((cliente) => ({ value: cliente.id, label: cliente.nome }))]}
          />
          <Select
            label="Projeto"
            value={projetoId}
            onChange={(event) => setProjetoId(event.target.value)}
            options={[{ value: "", label: "Todos" }, ...projetosOptions.map((projeto) => ({ value: projeto.id, label: projeto.nome }))]}
          />
          <Select
            label="Status"
            value={status}
            onChange={(event) => setStatus(event.target.value as DemandaStatus | "todos")}
            options={[{ value: "todos", label: "Todos" }, ...Object.entries(statusDemandaLabels).map(([value, label]) => ({ value, label }))]}
          />
          <Select
            label="Prioridade"
            value={prioridade}
            onChange={(event) => setPrioridade(event.target.value as DemandaPrioridade | "todos")}
            options={[{ value: "todos", label: "Todas" }, ...Object.entries(prioridadeDemandaLabels).map(([value, label]) => ({ value, label }))]}
          />
          <Select
            label="Período"
            value={periodo}
            onChange={(event) => setPeriodo(event.target.value as PeriodoFiltro)}
            options={[
              { value: "todos", label: "Todos" },
              { value: "hoje", label: "Previstas para hoje" },
              { value: "semana", label: "Previstas para a semana" },
              { value: "atrasadas", label: "Atrasadas" },
            ]}
          />
          <Select
            label="Origem"
            value={origem}
            onChange={(event) => setOrigem(event.target.value as OrigemFiltro)}
            options={[
              { value: "todos", label: "Todas" },
              { value: "cliente", label: "Cliente" },
              { value: "interna", label: "Interna" },
            ]}
          />
        </div>
      </div>

      <TarefasLista
        demandas={tarefasFiltradas}
        usuarios={usuarios}
        clientes={clientes}
        emptyTitle="Nenhuma tarefa encontrada"
        emptyDescription="Ajuste os filtros para visualizar tarefas do departamento."
      />
    </div>
  );
}

function Cabecalho({ nomeDepartamento }: { nomeDepartamento: string | undefined }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: [0.2, 0.9, 0.3, 1] }}
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Meu Departamento</h1>
            <p className="mt-1 text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              {nomeDepartamento ? `Visão operacional de ${nomeDepartamento}.` : "Visão restrita a Heads de departamento."}
            </p>
          </div>
        </div>
        <Badge tone="blue">Dados locais</Badge>
      </div>
    </motion.div>
  );
}
