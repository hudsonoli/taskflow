// Kanban → Em execução: a intenção (iniciar trabalho × alterar status administrativamente × bloquear) é escolhida ANTES da mutation, pelos sinais do servidor
// (`ehExecutorEfetivo` = responsabilidade; `podeAlterarStatus` = autoridade) — nunca pelo perfil e nunca como fallback de um erro. `npm run test:kanban-soltura`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { decidirSoltura, type EntradaSoltura } from "./kanban-soltura.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (codigo: string) => codigo.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

const EM_EXECUCAO = ["em_execucao"] as const;
const RASCUNHO_PLANEJADA = ["rascunho", "planejada"] as const;
const PAUSADA_BLOQUEADA = ["pausada", "bloqueada"] as const;
const TODOS = ["rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente", "concluida", "cancelada", "arquivada"] as const;

const base: EntradaSoltura = { statusDaColuna: EM_EXECUCAO, statusAtual: "pausada", podeIniciarNoExpediente: true, ehExecutorEfetivo: false, podeAlterarStatus: false };

test("A) executor efetivo → iniciar-trabalho, de qualquer status de origem (inclusive já em execução) e MESMO que também tenha autoridade (admin que executa)", () => {
  for (const statusAtual of TODOS) {
    assert.deepEqual(decidirSoltura({ ...base, statusAtual, ehExecutorEfetivo: true, podeAlterarStatus: false }), { acao: "iniciar-trabalho" }, `operador/${statusAtual}`);
    assert.deepEqual(decidirSoltura({ ...base, statusAtual, ehExecutorEfetivo: true, podeAlterarStatus: true }), { acao: "iniciar-trabalho" }, `admin executor/${statusAtual}`); // responsabilidade antes do perfil
  }
});

test("B) NÃO executor com autoridade → alteração administrativa de status para Em execução (sem sessão)", () => {
  for (const statusAtual of TODOS.filter((s) => s !== "em_execucao")) {
    assert.deepEqual(decidirSoltura({ ...base, statusAtual, ehExecutorEfetivo: false, podeAlterarStatus: true }), { acao: "alterar-status-administrativo", novoStatus: "em_execucao" }, statusAtual);
  }
  // já em execução e a pessoa não executa: nada a mudar, nenhuma sessão a abrir
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", podeAlterarStatus: true }), { acao: "nada" });
});

test("C) NÃO executor e sem autoridade → bloqueado (nem POST nem PATCH)", () => {
  for (const statusAtual of TODOS) {
    assert.deepEqual(decidirSoltura({ ...base, statusAtual, ehExecutorEfetivo: false, podeAlterarStatus: false }), { acao: "bloqueado-sem-autoridade" }, statusAtual);
  }
});

test("fora do expediente: NINGUÉM chega ao servidor — o executor NUNCA vira PATCH administrativo (o bloqueio de expediente vale para os dois caminhos)", () => {
  for (const statusAtual of TODOS) {
    for (const [ehExecutorEfetivo, podeAlterarStatus] of [[true, false], [true, true], [false, true], [false, false]] as const) {
      assert.deepEqual(decidirSoltura({ ...base, statusAtual, podeIniciarNoExpediente: false, ehExecutorEfetivo, podeAlterarStatus }), { acao: "bloqueado-expediente" }, `${statusAtual}/${ehExecutorEfetivo}/${podeAlterarStatus}`);
    }
  }
});

test("a decisão é função dos SINAIS do servidor, nunca do perfil: a entrada não tem perfil e o módulo não menciona admin/gestor/operador", () => {
  assert.deepEqual(Object.keys(base).sort(), ["ehExecutorEfetivo", "podeAlterarStatus", "podeIniciarNoExpediente", "statusAtual", "statusDaColuna"]);
  const codigo = semComentarios(ler("lib/kanban-soltura.ts"));
  assert.doesNotMatch(codigo, /(perfil|gestor|admin|dono|operador)|podeIniciarTrabalho|trabalhandoAgora/i);
});

test("nenhum caminho converte um erro em outro comando: a decisão não conhece respostas do servidor (sem fallback após 403)", () => {
  const codigo = semComentarios(ler("lib/kanban-soltura.ts"));
  assert.doesNotMatch(codigo, /403|catch|fallback|status ===? ?4/);
});

test("as demais colunas seguem o PATCH de status (destino = primeiro status da coluna) e soltar na própria coluna é um no-op; independem de executor/autoridade", () => {
  for (const [ehExecutorEfetivo, podeAlterarStatus] of [[true, false], [false, true], [false, false]] as const) {
    const sinais = { ehExecutorEfetivo, podeAlterarStatus };
    assert.deepEqual(decidirSoltura({ ...base, ...sinais, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "pausada" });
    assert.deepEqual(decidirSoltura({ ...base, ...sinais, statusDaColuna: RASCUNHO_PLANEJADA, statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "rascunho" });
    assert.deepEqual(decidirSoltura({ ...base, ...sinais, statusDaColuna: ["concluida"], statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "concluida" });
    assert.deepEqual(decidirSoltura({ ...base, ...sinais, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "bloqueada" }), { acao: "nada" });
    assert.deepEqual(decidirSoltura({ ...base, ...sinais, statusDaColuna: RASCUNHO_PLANEJADA, statusAtual: "planejada" }), { acao: "nada" });
  }
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: [] }), { acao: "nada" });
  // fora do expediente só bloqueia o INÍCIO de trabalho, não as outras colunas
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "em_execucao", podeIniciarNoExpediente: false }), { acao: "mover", novoStatus: "pausada" });
});

// ── fiação (source-scan): do soltar do card até o servidor e de volta à tela ─────────────────────────────────────────

test("handleDragEnd decide pelos sinais do servidor e executa a decisão: iniciar-trabalho, PATCH administrativo, bloqueio; sem ramificar por perfil; o motor dnd-kit não mudou", () => {
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /import \{ decidirSoltura \} from "@\/lib\/kanban-soltura";/);
  assert.match(kanban, /const decisao = decidirSoltura\(\{\s*statusDaColuna: column\.statuses,\s*statusAtual: demanda\.status,\s*podeIniciarNoExpediente: expediente\.podeIniciar,\s*ehExecutorEfetivo: demanda\.ehExecutorEfetivo === true,\s*podeAlterarStatus: demanda\.podeAlterarStatus === true,\s*\}\);/);
  assert.match(kanban, /if \(decisao\.acao === "bloqueado-sem-autoridade"\) \{\s*setAvisoBloqueio\(MOTIVO_SEM_RESPONSABILIDADE_NEM_AUTORIDADE\);\s*return;\s*\}/);
  assert.match(kanban, /if \(decisao\.acao === "iniciar-trabalho"\) onIniciarTrabalho\(demanda\.id\);\s*else onMoveDemanda\(demanda\.id, decisao\.novoStatus\);/);
  assert.match(kanban, /useSensor\(PointerSensor, \{ activationConstraint: \{ distance: 8 \} \}\)/); // sensores intocados
  assert.doesNotMatch(kanban, /console\.(log|debug)/);
  assert.doesNotMatch(kanban, /podeIniciarTrabalho|trabalhandoAgora|perfil|gestor|admin/i); // o gesto define a intenção; ninguém bifurca por papel
});

test("a tela não tem fallback: iniciar-trabalho em recusa só mostra a mensagem e recarrega; o PATCH administrativo é um caminho à parte, escolhido antes", () => {
  const view = semComentarios(ler("components/demandas/DemandasView.tsx"));
  const trecho = /async function iniciarTrabalho\(demandaId: string\) \{[\s\S]*?\n  \}\n/.exec(view)?.[0] ?? "";
  assert.match(trecho, /iniciarTrabalhoDemandaReal\(demandaId\)/);
  assert.match(trecho, /setRefetchTick\(\(tick\) => tick \+ 1\);\s*setEstatisticasTick\(\(tick\) => tick \+ 1\);\s*\} catch \(error\) \{\s*setErro\(mensagemDeErro\(error\)\);\s*setRefetchTick\(\(tick\) => tick \+ 1\);/);
  assert.doesNotMatch(trecho, /patchDemandaReal|aplicarStatus|handleMoveDemand|"pausada"|"em_execucao"/); // recusa NUNCA vira PATCH
  const mover = /function handleMoveDemand\([\s\S]*?\n  \}\n/.exec(view)?.[0] ?? "";
  assert.doesNotMatch(mover, /iniciarTrabalho/); // o PATCH administrativo nunca cai no comando de iniciar trabalho
  assert.match(mover, /void aplicarStatus\(demandaId, novoStatus\);/);
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /`\/demandas\/\$\{encodeURIComponent\(demandaId\)\}\/iniciar-trabalho`, \{ method: "POST"/);
  assert.match(api, /ehExecutorEfetivo: data\.ehExecutorEfetivo === true,\s*podeAlterarStatus: data\.podeAlterarStatus === true,/);
});

test("os controles administrativos de status (drawer e Nova tarefa) seguem independentes do Kanban", () => {
  assert.match(semComentarios(ler("components/demandas/DemandaFormSections.tsx")), /salvarCampo\(demanda, \{ status: event\.target\.value as DemandaStatusEditavel \}/);
  assert.match(semComentarios(ler("components/demandas/NovaDemandaModal.tsx")), /updateDraft\(\{ status: event\.target\.value as DemandaStatusEditavel \}\)/);
});

test("o botão 'Iniciar trabalho' do card e o arrasto do executor usam o MESMO comando", () => {
  const card = semComentarios(ler("components/demandas/DemandaKanbanCard.tsx"));
  assert.match(card, /demanda\.status === "em_execucao" && demanda\.podeIniciarTrabalho && !demanda\.trabalhandoAgora/);
  assert.match(card, /onClick=\{\(\) => onIniciarTrabalho\(demanda\.id\)\}/);
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /onIniciarTrabalho=\{onIniciarTrabalho\}/);
});
