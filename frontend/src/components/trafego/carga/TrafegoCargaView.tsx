"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Combobox } from "@/components/ui/Combobox";
import { EmptyState } from "@/components/ui/EmptyState";
import { Select } from "@/components/ui/Select";
import { Tabs } from "@/components/ui/Tabs";
import { useAppData } from "@/lib/AppDataContext";
import {
  ABA_PLANEJAMENTO_DA_DEMANDA,
  algumNaoPlanejado,
  algumaPendencia,
  cabecalhoDaSemana,
  estadoVazioDaCarga,
  indicadoresDoResumo,
  linhaDaPessoa,
  linhaDoDepartamento,
  parametrosPrincipais,
  qualidadeDoPlanejamento,
  resumoDaCarga,
  type AlvoDetalhe,
} from "@/lib/trafego-carga";
import { useTenantPath } from "@/lib/useTenantPath";
import type { CargaSemanal, FiltrosCarga } from "@/types/trafego-carga";
import { TrafegoAvisoAtualizacao, TrafegoErroLocal, TrafegoSkeleton } from "../TrafegoEstados";
import { CargaDetailDrawer } from "./CargaDetailDrawer";
import { CargaForaDaCapacidade, CargaPendencias, CargaPrecisaDePlanejamento } from "./CargaPlanejamento";
import { CargaCapacidadeIndisponivel, CargaPlanningWarnings, CargaSummary } from "./CargaSummary";
import { CargaDepartmentsTable, CargaPeopleTable } from "./CargaTabelas";
import { CargaWeekNavigator } from "./CargaWeekNavigator";
import { useTrafegoCarga } from "./useTrafegoCarga";

type ModoCarga = "pessoas" | "departamentos";
const MODOS = [
  { id: "pessoas", label: "Pessoas" },
  { id: "departamentos", label: "Departamentos" },
];

type OpcoesDeFiltro = { pessoas: Array<{ value: string; label: string }>; departamentos: Array<{ value: string; label: string }>; nomeDoDepartamento: Map<string, string> };
const SEM_OPCOES: OpcoesDeFiltro = { pessoas: [], departamentos: [], nomeDoDepartamento: new Map() };

function opcoesDaResposta(dados: CargaSemanal): OpcoesDeFiltro {
  return {
    pessoas: dados.pessoas.map((p) => ({ value: p.usuarioId, label: p.nome })),
    departamentos: dados.departamentos.map((d) => ({ value: d.departamentoId, label: d.nome })),
    nomeDoDepartamento: new Map(dados.departamentos.map((d) => [d.departamentoId, d.nome])),
  };
}

/**
 * CARGA SEMANAL — "quanto da capacidade planejável da equipe já está comprometida nesta semana, e o que ainda não está corretamente planejado?". NÃO é produtividade nem "quem trabalhou mais":
 * não usa sessões de trabalho (tempo pessoal) nem intervalos de estado (tempo operacional); a única fonte é `GET /trafego/operacional/carga`.
 *
 * UMA requisição principal por entrada, semana, filtro ou "Atualizar" (sem polling); o drill-down faz +1 só ao abrir. Os filtros vão para o servidor — o cliente nunca filtra e finge que recalculou.
 * Semana e filtros vivem no estado da tela (a URL carrega apenas `?visao=carga`).
 */
export function TrafegoCargaView() {
  const { setDemandaParaAbrir } = useAppData();
  const router = useRouter();
  const caminhoDoTenant = useTenantPath();

  // `null` = semana atual (o servidor resolve a segunda-feira no fuso da empresa).
  const [semana, setSemana] = useState<string | null>(null);
  const [filtros, setFiltros] = useState<FiltrosCarga>({ departamentoId: null, usuarioId: null });
  const [modo, setModo] = useState<ModoCarga>("pessoas");
  const [versao, setVersao] = useState(0);
  const [alvo, setAlvo] = useState<AlvoDetalhe | null>(null);

  const parametros = useMemo(() => parametrosPrincipais(semana, filtros), [semana, filtros]);
  const { dados, carregando, atualizando, erro } = useTrafegoCarga(parametros, versao);

  // Opções dos filtros: vêm da última resposta SEM filtro (a que lista todos). Com filtro ativo a resposta só traz o recorte, então as opções anteriores são mantidas.
  const [opcoes, setOpcoes] = useState<OpcoesDeFiltro>(SEM_OPCOES);
  const [dadosVistos, setDadosVistos] = useState<CargaSemanal | null>(null);
  if (dados !== null && dados !== dadosVistos) {
    setDadosVistos(dados);
    if (dados.poolSemDepartamento !== null) setOpcoes(opcoesDaResposta(dados));
  }

  const atualizar = useCallback(() => setVersao((v) => v + 1), []);

  const abrirTarefa = useCallback(
    (demandaId: string) => {
      setDemandaParaAbrir({ demandaId, aba: ABA_PLANEJAMENTO_DA_DEMANDA });
      router.push(caminhoDoTenant("tarefas"));
    },
    [router, caminhoDoTenant, setDemandaParaAbrir],
  );

  const cabecalho = dados ? cabecalhoDaSemana(dados) : null;
  const qualidade = dados ? qualidadeDoPlanejamento(dados, filtros) : null;
  const resumo = dados ? resumoDaCarga(dados) : null;
  const vazio = dados ? estadoVazioDaCarga(dados, filtros) : null;
  const filtroAtivo = Boolean(filtros.departamentoId || filtros.usuarioId);

  const linhasPessoas = dados ? dados.pessoas.map((p) => linhaDaPessoa(p, (p.departamentoId && opcoes.nomeDoDepartamento.get(p.departamentoId)) || null)) : [];
  const linhasDepartamentos = dados ? dados.departamentos.map(linhaDoDepartamento) : [];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <p className="text-sm text-fg-muted">Quanto da capacidade da equipe já está comprometida com o que foi estimado e planejado — e o que ainda falta planejar.</p>
        <CargaWeekNavigator cabecalho={cabecalho} onIr={setSemana} onAtualizar={atualizar} atualizando={atualizando} />
      </div>

      <div role="search" aria-label="Filtros da carga" className="grid grid-cols-1 gap-3 rounded-2xl border border-line bg-surface p-4 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
        <Select
          label="Departamento"
          value={filtros.departamentoId ?? ""}
          onChange={(evento) => setFiltros({ departamentoId: evento.target.value || null, usuarioId: null })}
          options={[{ value: "", label: "Todos os departamentos" }, ...opcoes.departamentos]}
        />
        <Combobox
          label="Pessoa"
          value={filtros.usuarioId ?? ""}
          onChange={(id) => setFiltros({ departamentoId: null, usuarioId: id || null })}
          options={opcoes.pessoas}
          placeholder="Todas as pessoas"
        />
      </div>

      {carregando && dados === null ? (
        <TrafegoSkeleton kpis={4} linhas={5} />
      ) : dados === null || resumo === null || qualidade === null ? (
        <TrafegoErroLocal mensagem={erro ?? "Não foi possível carregar a Carga semanal."} onTentarNovamente={atualizar} />
      ) : (
        <div className="flex flex-col gap-4" aria-busy={atualizando}>
          {erro && <TrafegoAvisoAtualizacao mensagem={erro} onTentarNovamente={atualizar} />}
          {resumo.capacidadeIndisponivel !== null && <CargaCapacidadeIndisponivel motivo={resumo.capacidadeIndisponivel} />}
          <CargaPlanningWarnings qualidade={qualidade} />
          <CargaSummary indicadores={indicadoresDoResumo(resumo, qualidade)} />

          <section aria-label="Carga por pessoa e departamento" className="rounded-2xl border border-line bg-surface p-4 shadow-sm">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-fg">{modo === "pessoas" ? "Pessoas" : "Departamentos"}</h3>
                <p className="text-xs text-fg-subtle">
                  Capacidade alocável × planejado (etapas estimadas e com janela). Planejamento — não é tempo trabalhado.
                  {filtroAtivo ? " Recorte aplicado pelo servidor." : ""}
                </p>
              </div>
              <Tabs tabs={MODOS} activeTab={modo} onChange={(id) => setModo(id as ModoCarga)} />
            </div>
            {vazio ? (
              <EmptyState title={vazio.titulo} description={vazio.descricao} />
            ) : modo === "pessoas" ? (
              linhasPessoas.length === 0 ? (
                <EmptyState title="Não há pessoas neste recorte." description="Os departamentos deste recorte não têm pessoas com capacidade. Veja a aba Departamentos." />
              ) : (
                <CargaPeopleTable linhas={linhasPessoas} onAbrir={(linha) => setAlvo({ tipo: "usuario", id: linha.usuarioId, nome: linha.nome })} />
              )
            ) : linhasDepartamentos.length === 0 ? (
              <EmptyState title="Nenhum departamento neste recorte." description="Com um filtro de pessoa, use a aba Pessoas." />
            ) : (
              <CargaDepartmentsTable linhas={linhasDepartamentos} onAbrir={(linha) => setAlvo({ tipo: "departamento", id: linha.departamentoId, nome: linha.nome })} />
            )}
          </section>

          <CargaForaDaCapacidade poolSemDepartamento={resumo.poolSemDepartamento} poolsSemCapacidade={resumo.poolsSemCapacidade} />
          {algumNaoPlanejado(dados) && <CargaPrecisaDePlanejamento dados={dados} />}
          {algumaPendencia(dados) && <CargaPendencias dados={dados} onAbrirTarefa={abrirTarefa} />}
        </div>
      )}

      {alvo && dados && <CargaDetailDrawer alvo={alvo} semana={dados.semana.inicio} onClose={() => setAlvo(null)} onAbrirTarefa={abrirTarefa} />}
    </div>
  );
}
