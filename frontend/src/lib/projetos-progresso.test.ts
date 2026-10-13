// Visão "Progresso" de Projetos — regras puras exercitadas de verdade + estrutura (somente leitura, sem endpoint novo, sem N+1). `npm run test:projetos-progresso`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import type { Demanda, DemandaWorkflowEtapa } from "../types/demanda.ts";
import type { Projeto } from "../types/projeto.ts";
import {
  aplicarFiltros,
  contaNoProgresso,
  FILTROS_PROGRESSO_VAZIOS,
  fluxoDaTarefa,
  montarProjetos,
  ordenarTarefas,
  resumoDoProjeto,
  responsaveisDaTarefa,
  SEM_TRABALHO_AGORA,
  trabalhandoAgoraNaTarefa,
} from "./projetos-progresso.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

let seq = 0;
function etapa(ordem: number, status: DemandaWorkflowEtapa["status"], extra: Partial<DemandaWorkflowEtapa> = {}): DemandaWorkflowEtapa {
  return {
    id: `e${ordem}`,
    nome: `Etapa ${ordem}`,
    ordem,
    tipo: "execucao",
    quantidadeAntesDeadline: 1,
    unidadePrazo: "dias_uteis",
    usuarioResponsavelIds: [],
    departamentoResponsavelIds: [],
    status,
    iniciadaEm: null,
    concluidaEm: null,
    concluidaPorUsuarioId: null,
    podeAvancar: false,
    ...extra,
  };
}

function tarefa(extra: Partial<Demanda> = {}): Demanda {
  seq += 1;
  return {
    id: `d${seq}`,
    projetoId: "p1",
    clienteId: "c1",
    numeroOperacional: seq,
    identificador: `#${seq}`,
    nome: `Tarefa ${seq}`,
    status: "planejada",
    usuarioResponsavelIds: [],
    departamentoResponsavelIds: [],
    prazoEtapaAtual: null,
    workflowEtapas: [],
    etapaAtualId: null,
    ...extra,
  } as unknown as Demanda;
}

const projeto = (id: string, extra: Partial<Projeto> = {}): Projeto => ({ id, nome: `Projeto ${id}`, campanha: "", codigoReferencia: `P${id}`, clienteId: "c1", status: "ativo", ...extra }) as unknown as Projeto;

const nunca = () => false;

// ── percentual do projeto ────────────────────────────────────────────────────────────────────────────────────

test("projeto com 0 tarefas: percentual nulo (nunca 0%), total 0", () => {
  const resumo = resumoDoProjeto([], nunca);
  assert.equal(resumo.total, 0);
  assert.equal(resumo.percentual, null);
  assert.equal(resumo.segmentos.every((segmento) => segmento.quantidade === 0), true);
});

test("projeto com 1 tarefa: 0% ou 100%", () => {
  assert.equal(resumoDoProjeto([tarefa({ status: "em_execucao" })], nunca).percentual, 0);
  assert.equal(resumoDoProjeto([tarefa({ status: "concluida" })], nunca).percentual, 100);
});

test("percentual = concluídas / consideradas; cancelada e arquivada ficam fora do denominador", () => {
  const demandas = [tarefa({ status: "concluida" }), tarefa({ status: "em_execucao" }), tarefa({ status: "bloqueada" }), tarefa({ status: "cancelada" }), tarefa({ status: "arquivada" })];
  const resumo = resumoDoProjeto(demandas, nunca);
  assert.equal(resumo.total, 3);
  assert.equal(resumo.concluidas, 1);
  assert.equal(resumo.percentual, 33);
  assert.equal(contaNoProgresso({ status: "cancelada" }), false);
  assert.equal(contaNoProgresso({ status: "rascunho" }), true);
});

test("o percentual não depende de etapas, prazo nem de quem trabalha: só do status das tarefas", () => {
  const comEtapas = tarefa({ status: "em_execucao", workflowEtapas: [etapa(1, "concluida"), etapa(2, "concluida"), etapa(3, "em_execucao")], etapaAtualId: "e3" });
  const concluida = tarefa({ status: "concluida" });
  assert.equal(resumoDoProjeto([comEtapas, concluida], nunca).percentual, 50);
  assert.equal(resumoDoProjeto([comEtapas, concluida], () => true).percentual, 50);
});

test("composição por status reais: soma dos segmentos = total; planejada agrupa rascunho; bloqueadas/atrasadas/aguardando contados", () => {
  const atrasada = tarefa({ status: "em_execucao", prazoEtapaAtual: "2020-01-01T00:00:00Z" });
  const demandas = [tarefa({ status: "concluida" }), atrasada, tarefa({ status: "aguardando_cliente" }), tarefa({ status: "bloqueada" }), tarefa({ status: "pausada" }), tarefa({ status: "planejada" }), tarefa({ status: "rascunho" })];
  const resumo = resumoDoProjeto(demandas, (demanda) => demanda.id === atrasada.id);
  const por = Object.fromEntries(resumo.segmentos.map((segmento) => [segmento.id, segmento.quantidade]));
  assert.deepEqual(por, { concluida: 1, em_execucao: 1, aguardando_cliente: 1, bloqueada: 1, pausada: 1, planejada: 2 });
  assert.equal(resumo.segmentos.reduce((soma, segmento) => soma + segmento.quantidade, 0), resumo.total);
  assert.equal(resumo.bloqueadas, 1);
  assert.equal(resumo.atrasadas, 1);
  assert.equal(resumo.aguardandoCliente, 1);
});

// ── fluxo / etapa atual ──────────────────────────────────────────────────────────────────────────────────────

test("sem workflow: 'sem_workflow' — nenhum percentual inventado", () => {
  assert.deepEqual(fluxoDaTarefa(tarefa()), { tipo: "sem_workflow" });
});

test("workflow: N/M etapas, etapa atual = etapaAtualId (autoridade do servidor), passos na ordem", () => {
  const fluxo = fluxoDaTarefa(tarefa({ workflowEtapas: [etapa(3, "pendente"), etapa(1, "concluida"), etapa(2, "em_execucao")], etapaAtualId: "e2" }));
  assert.equal(fluxo.tipo, "workflow");
  if (fluxo.tipo !== "workflow") return;
  assert.equal(fluxo.total, 3);
  assert.equal(fluxo.concluidas, 1);
  assert.deepEqual(fluxo.passos.map((passo) => passo.estado), ["concluida", "atual", "pendente"]);
  assert.equal(fluxo.atual?.id, "e2");
  assert.equal(fluxo.todasConcluidas, false);
});

test("etapa atual pausada é distinguível; todas concluídas não tem etapa atual", () => {
  const pausada = fluxoDaTarefa(tarefa({ workflowEtapas: [etapa(1, "pausada")], etapaAtualId: "e1" }));
  assert.equal(pausada.tipo === "workflow" && pausada.passos[0].estado, "atual_pausada");
  const fim = fluxoDaTarefa(tarefa({ workflowEtapas: [etapa(1, "concluida"), etapa(2, "concluida")], etapaAtualId: null }));
  assert.equal(fim.tipo === "workflow" && fim.todasConcluidas, true);
  assert.equal(fim.tipo === "workflow" && fim.atual, null);
});

test("workflows diferentes convivem: 2 etapas e 5 etapas cada um com o seu N/M", () => {
  const curto = fluxoDaTarefa(tarefa({ workflowEtapas: [etapa(1, "concluida"), etapa(2, "em_execucao")], etapaAtualId: "e2" }));
  const longo = fluxoDaTarefa(tarefa({ workflowEtapas: [1, 2, 3, 4, 5].map((n) => etapa(n, n <= 3 ? "concluida" : "pendente")), etapaAtualId: "e4" }));
  assert.deepEqual([curto.tipo === "workflow" && curto.concluidas, curto.tipo === "workflow" && curto.total], [1, 2]);
  assert.deepEqual([longo.tipo === "workflow" && longo.concluidas, longo.tipo === "workflow" && longo.total], [3, 5]);
});

// ── responsáveis e trabalhando agora ─────────────────────────────────────────────────────────────────────────

test("responsáveis: usuários da etapa atual; sem usuário, departamento; sem nada, 'sem responsável'", () => {
  const comUsuario = responsaveisDaTarefa(tarefa({ workflowEtapas: [etapa(1, "em_execucao", { usuarioResponsavelIds: ["u1"], departamentoResponsavelIds: ["dep1"] })], etapaAtualId: "e1" }));
  assert.deepEqual(comUsuario.usuarioIds, ["u1"]);
  assert.deepEqual(comUsuario.departamentoIds, []); // departamento só quando não há usuário
  const comDepartamento = responsaveisDaTarefa(tarefa({ workflowEtapas: [etapa(1, "em_execucao", { departamentoResponsavelIds: ["dep1"] })], etapaAtualId: "e1" }));
  assert.deepEqual(comDepartamento.departamentoIds, ["dep1"]);
  assert.equal(comDepartamento.semResponsavel, false);
  const ninguem = responsaveisDaTarefa(tarefa({ workflowEtapas: [etapa(1, "em_execucao")], etapaAtualId: "e1" }));
  assert.equal(ninguem.semResponsavel, true);
});

test("workflow com todas as etapas concluídas: não há quem responda — e isso não é \"sem responsável\"", () => {
  const r = responsaveisDaTarefa(tarefa({ workflowEtapas: [etapa(1, "concluida", { usuarioResponsavelIds: ["u1"] })], etapaAtualId: null }));
  assert.equal(r.origem, "workflow_concluido");
  assert.equal(r.semResponsavel, false);
  assert.deepEqual(r.usuarioIds, []);
});

test("responsáveis ignoram os da tarefa quando há workflow (a etapa atual manda); sem workflow valem os da tarefa", () => {
  const comWorkflow = responsaveisDaTarefa(tarefa({ usuarioResponsavelIds: ["u9"], workflowEtapas: [etapa(1, "em_execucao", { usuarioResponsavelIds: ["u1"] })], etapaAtualId: "e1" }));
  assert.deepEqual(comWorkflow.usuarioIds, ["u1"]);
  assert.equal(comWorkflow.origem, "etapa_atual");
  const semWorkflow = responsaveisDaTarefa(tarefa({ usuarioResponsavelIds: ["u9"] }));
  assert.deepEqual(semWorkflow.usuarioIds, ["u9"]);
  assert.equal(semWorkflow.origem, "tarefa");
});

test("sessão ativa: marca o responsável ('Agora'); quem trabalha sem ser responsável fica em indicador separado", () => {
  const r = responsaveisDaTarefa(tarefa({ usuarioResponsavelIds: ["u1", "u2"] }));
  const viva = trabalhandoAgoraNaTarefa("d1", { fonte: "pessoas", porDemanda: { d1: ["u2", "u7"] } }, r);
  assert.deepEqual(viva.responsaveisAgora, ["u2"]);
  assert.deepEqual(viva.outrosAgora, ["u7"]);
  assert.equal(viva.alguemAgora, true);
  const parada = trabalhandoAgoraNaTarefa("d2", { fonte: "pessoas", porDemanda: { d1: ["u2"] } }, r);
  assert.deepEqual(parada, { responsaveisAgora: [], outrosAgora: [], alguemAgora: false });
});

test("fonte só por tarefa (perfis sem acesso às pessoas): sabe QUE há alguém, nunca QUEM; sem fonte: nada", () => {
  const r = responsaveisDaTarefa(tarefa({ usuarioResponsavelIds: ["u1"] }));
  const porDemanda = trabalhandoAgoraNaTarefa("d1", { fonte: "demandas", demandaIds: new Set(["d1"]) }, r);
  assert.deepEqual(porDemanda, { responsaveisAgora: [], outrosAgora: [], alguemAgora: true });
  assert.equal(trabalhandoAgoraNaTarefa("d1", SEM_TRABALHO_AGORA, r).alguemAgora, false);
});

// ── ordem, agrupamento e filtros ─────────────────────────────────────────────────────────────────────────────

test("ordem das tarefas: bloqueadas, atrasadas, em execução, aguardando cliente, pausadas, planejadas, concluídas; canceladas não aparecem", () => {
  const concluida = tarefa({ status: "concluida" });
  const planejada = tarefa({ status: "planejada" });
  const pausada = tarefa({ status: "pausada" });
  const aguardando = tarefa({ status: "aguardando_cliente" });
  const execucao = tarefa({ status: "em_execucao" });
  const atrasada = tarefa({ status: "planejada", prazoEtapaAtual: "2020-01-01T00:00:00Z" });
  const bloqueada = tarefa({ status: "bloqueada" });
  const cancelada = tarefa({ status: "cancelada" });
  const ordenadas = ordenarTarefas([concluida, planejada, pausada, aguardando, execucao, atrasada, bloqueada, cancelada], (demanda) => demanda.id === atrasada.id);
  assert.deepEqual(
    ordenadas.map((demanda) => demanda.id),
    [bloqueada, atrasada, execucao, aguardando, pausada, planejada, concluida].map((demanda) => demanda.id),
  );
});

test("vários projetos: cada tarefa vai ao seu projeto; tarefas sem projeto não entram; projetos com pendência vêm antes dos 100% concluídos", () => {
  const feito = tarefa({ projetoId: "pA", status: "concluida" });
  const aberta = tarefa({ projetoId: "pB", status: "bloqueada" });
  const semProjeto = tarefa({ projetoId: null });
  const grupos = montarProjetos([projeto("pA"), projeto("pB"), projeto("pC")], [feito, aberta, semProjeto], nunca);
  assert.deepEqual(grupos.map((grupo) => grupo.projeto.id), ["pB", "pA", "pC"]);
  assert.equal(grupos.find((grupo) => grupo.projeto.id === "pC")?.resumo.total, 0);
  assert.equal(grupos.flatMap((grupo) => grupo.tarefas).includes(semProjeto), false);
});

test("filtros mexem nas LINHAS, nunca no resumo do projeto", () => {
  const a = tarefa({ projetoId: "pA", status: "bloqueada", nome: "Banner Verão" });
  const b = tarefa({ projetoId: "pA", status: "concluida", nome: "Vídeo" });
  const grupos = montarProjetos([projeto("pA")], [a, b], nunca);
  const filtrado = aplicarFiltros(grupos, { ...FILTROS_PROGRESSO_VAZIOS, status: "bloqueada" });
  assert.equal(filtrado[0].tarefas.length, 1);
  assert.equal(filtrado[0].resumo.total, 2); // cabeçalho intacto
  assert.equal(filtrado[0].resumo.percentual, 50);
});

test("busca sem acento por tarefa e por projeto; projeto sem linhas some quando há filtro de tarefa", () => {
  const a = tarefa({ projetoId: "pA", nome: "Peça Promoção" });
  const grupos = montarProjetos([projeto("pA", { nome: "Campanha Natal" }), projeto("pB", { nome: "Outro" })], [a, tarefa({ projetoId: "pB", nome: "Zzz" })], nunca);
  assert.equal(aplicarFiltros(grupos, { ...FILTROS_PROGRESSO_VAZIOS, busca: "promocao" }).length, 1);
  const porProjeto = aplicarFiltros(grupos, { ...FILTROS_PROGRESSO_VAZIOS, busca: "natal" });
  assert.equal(porProjeto.length, 1);
  assert.equal(porProjeto[0].tarefas.length, 1); // projeto que casa mostra suas tarefas
});

test("filtro de responsável e de departamento casa com a etapa atual ou com a tarefa; cliente filtra o projeto", () => {
  const viaEtapa = tarefa({ projetoId: "pA", workflowEtapas: [etapa(1, "em_execucao", { usuarioResponsavelIds: ["u1"], departamentoResponsavelIds: ["dep1"] })], etapaAtualId: "e1" });
  const viaTarefa = tarefa({ projetoId: "pA", usuarioResponsavelIds: ["u2"] });
  const grupos = montarProjetos([projeto("pA", { clienteId: "c1" }), projeto("pB", { clienteId: "c2" })], [viaEtapa, viaTarefa, tarefa({ projetoId: "pB" })], nunca);
  assert.deepEqual(aplicarFiltros(grupos, { ...FILTROS_PROGRESSO_VAZIOS, responsavelId: "u1" })[0].tarefas, [viaEtapa]);
  assert.deepEqual(aplicarFiltros(grupos, { ...FILTROS_PROGRESSO_VAZIOS, responsavelId: "u2" })[0].tarefas, [viaTarefa]);
  assert.deepEqual(aplicarFiltros(grupos, { ...FILTROS_PROGRESSO_VAZIOS, departamentoId: "dep1" })[0].tarefas, [viaEtapa]);
  assert.deepEqual(aplicarFiltros(grupos, { ...FILTROS_PROGRESSO_VAZIOS, clienteId: "c2" }).map((grupo) => grupo.projeto.id), ["pB"]);
});

// ── estrutura: somente leitura, sem endpoint novo, sem N+1 ───────────────────────────────────────────────────

test("a visão reutiliza o painel de detalhes existente e não cria edição inline", () => {
  const view = semComentarios(ler("components/projetos/progresso/ProjetosProgressoView.tsx"));
  assert.match(view, /DemandaDetailsDrawer/);
  const linha = semComentarios(ler("components/projetos/progresso/ProjetoProgressoGrupo.tsx"));
  for (const proibido of ["dnd-kit", "onDrag", "draggable", "<select", "<input", "<textarea", "atualizarDemanda", "PATCH", "fetch("]) {
    assert.equal(linha.includes(proibido), false, `a linha de tarefa não pode conter ${proibido}`);
  }
  assert.match(linha, /Avatar/); // linguagem visual canônica de pessoas
});

test("o carregamento usa só endpoints existentes, em lote (sem requisição por linha)", () => {
  const dados = semComentarios(ler("lib/progresso-projetos-dados.ts"));
  assert.match(dados, /listProjetosReais\(\)/);
  assert.match(dados, /listDemandasReais\(\{ projetoId: ids/);
  assert.match(dados, /getAgoraTrafegoSessoes/);
  assert.match(dados, /listarDemandasEmExecucaoNaPauta/);
  // nenhuma requisição dentro de map/forEach/Promise.all por tarefa
  assert.equal(/\.(map|forEach)\([^)]*=>[^)]*(listDemandasReais|getAgoraTrafegoSessoes|request)/.test(dados), false);
  assert.equal(/Promise\.all/.test(dados), false);
  const api = ler("lib/api-backend.ts");
  assert.equal(api.includes("/projetos/progresso"), false); // nenhum endpoint novo foi criado
});

test("a aba Progresso fica DENTRO de /projetos (sem novo item de menu)", () => {
  const projetos = ler("components/projetos/ProjetosView.tsx");
  assert.match(projetos, /ProjetosProgressoView/);
  assert.match(projetos, /label: "Progresso"/);
  assert.equal(ler("app/e/[slug]/projetos/page.tsx").includes("Progresso"), false);
});
