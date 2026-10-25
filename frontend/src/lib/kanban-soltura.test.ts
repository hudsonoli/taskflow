// Semântica única do Kanban: arrastar para Em execução = INICIAR TRABALHO (nunca PATCH de status). `npm run test:kanban-soltura`.
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

const base: EntradaSoltura = { statusDaColuna: EM_EXECUCAO, statusAtual: "planejada", podeIniciarNoExpediente: true };

test("soltar em Em execução é SEMPRE iniciar-trabalho, de qualquer status de origem (planejada, pausada, bloqueada, aguardando cliente, concluída… e a que JÁ está em execução)", () => {
  for (const statusAtual of TODOS) {
    assert.deepEqual(decidirSoltura({ ...base, statusAtual }), { acao: "iniciar-trabalho" }, statusAtual);
  }
});

test("a decisão NÃO depende de quem arrasta: operador, gestor, dono/admin legado — a permissão final é do backend (que recusa quem não executa a etapa), nunca um PATCH no lugar", () => {
  const campos = Object.keys(base);
  assert.deepEqual(campos.sort(), ["podeIniciarNoExpediente", "statusAtual", "statusDaColuna"]); // sem perfil, sem flag de elegibilidade: não há como bifurcar por papel
  const codigo = semComentarios(ler("lib/kanban-soltura.ts"));
  assert.doesNotMatch(codigo, /perfil|gestor|admin|dono|podeIniciarTrabalho|trabalhandoAgora/i);
});

test("nenhuma combinação leva um card a Em execução por PATCH de status", () => {
  for (const statusAtual of TODOS)
    for (const podeIniciarNoExpediente of [true, false]) {
      const d = decidirSoltura({ statusDaColuna: EM_EXECUCAO, statusAtual, podeIniciarNoExpediente });
      assert.notEqual(d.acao, "mover", `${statusAtual}/${podeIniciarNoExpediente}`);
      assert.notEqual(d.acao, "nada", `${statusAtual}/${podeIniciarNoExpediente}`); // nem sumir com o gesto: ou inicia ou mostra o bloqueio de expediente
    }
});

test("fora do expediente: o gesto vira o aviso de bloqueio (sem request e sem fallback) — inclusive para a tarefa já em execução", () => {
  for (const statusAtual of TODOS) {
    assert.deepEqual(decidirSoltura({ ...base, statusAtual, podeIniciarNoExpediente: false }), { acao: "bloqueado-expediente" }, statusAtual);
  }
});

test("as demais colunas seguem o PATCH de status (destino = primeiro status da coluna) e soltar na própria coluna é um no-op; nunca em_execucao", () => {
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "pausada" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: RASCUNHO_PLANEJADA, statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "rascunho" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: ["concluida"], statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "concluida" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "bloqueada" }), { acao: "nada" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: RASCUNHO_PLANEJADA, statusAtual: "planejada" }), { acao: "nada" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: [] }), { acao: "nada" });
  // fora do expediente só bloqueia o INÍCIO de trabalho, não as outras colunas
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "em_execucao", podeIniciarNoExpediente: false }), { acao: "mover", novoStatus: "pausada" });
});

// ── fiação (source-scan): do soltar do card até o servidor e de volta à tela ─────────────────────────────────────────

test("handleDragEnd usa a decisão pura: iniciar-trabalho ou PATCH das outras colunas, sem ramificar por perfil; o motor dnd-kit não mudou", () => {
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /import \{ decidirSoltura \} from "@\/lib\/kanban-soltura";/);
  assert.match(kanban, /const decisao = decidirSoltura\(\{\s*statusDaColuna: column\.statuses,\s*statusAtual: demanda\.status,\s*podeIniciarNoExpediente: expediente\.podeIniciar,\s*\}\);/);
  assert.match(kanban, /if \(decisao\.acao === "iniciar-trabalho"\) onIniciarTrabalho\(demanda\.id\);\s*else onMoveDemanda\(demanda\.id, decisao\.novoStatus\);/);
  assert.match(kanban, /useSensor\(PointerSensor, \{ activationConstraint: \{ distance: 8 \} \}\)/); // sensores intocados
  assert.doesNotMatch(kanban, /console\.(log|debug)/);
  assert.doesNotMatch(kanban, /podeIniciarTrabalho|trabalhandoAgora|perfil|gestor|admin/i); // o gesto define a intenção; ninguém bifurca por papel
  assert.doesNotMatch(kanban, /onMoveDemanda\([^)]*"(pausada|em_execucao)"|status: ?"pausada"/); // o frontend nunca inventa status
});

test("a tela só confia no servidor: iniciar-trabalho → resposta + refetch; em recusa, mensagem + refetch (o card fica onde estava); nenhum fallback para PATCH", () => {
  const view = semComentarios(ler("components/demandas/DemandasView.tsx"));
  const trecho = /async function iniciarTrabalho\(demandaId: string\) \{[\s\S]*?\n  \}\n/.exec(view)?.[0] ?? "";
  assert.match(trecho, /iniciarTrabalhoDemandaReal\(demandaId\)/);
  assert.match(trecho, /setRefetchTick\(\(tick\) => tick \+ 1\);\s*setEstatisticasTick\(\(tick\) => tick \+ 1\);\s*\} catch \(error\) \{\s*setErro\(mensagemDeErro\(error\)\);\s*setRefetchTick\(\(tick\) => tick \+ 1\);/);
  assert.doesNotMatch(trecho, /patchDemandaReal|aplicarStatus|"pausada"|"em_execucao"/); // recusa NUNCA vira PATCH
  // rede de segurança: mesmo uma chamada a handleMoveDemand com em_execucao vai para iniciar-trabalho, nunca para o PATCH
  const mover = /function handleMoveDemand\([\s\S]*?\n  \}\n/.exec(view)?.[0] ?? "";
  assert.match(mover, /if \(novoStatus === "em_execucao"\) \{\s*void iniciarTrabalho\(demandaId\);\s*return;\s*\}/);
  assert.ok(mover.indexOf('"em_execucao"') < mover.indexOf("aplicarStatus"));
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /`\/demandas\/\$\{encodeURIComponent\(demandaId\)\}\/iniciar-trabalho`, \{ method: "POST"/);
});

test("auditoria dos caminhos até Em execução: só o controle ADMINISTRATIVO (campo Status do drawer/modal) usa PATCH/POST de status; o Kanban nunca", () => {
  // KANBAN_DRAG: DemandasKanban → decidirSoltura → onIniciarTrabalho (POST iniciar-trabalho). O único PATCH do Kanban é o das OUTRAS colunas (aplicarStatus, sem em_execucao).
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.doesNotMatch(kanban, /patchDemandaReal|aplicarStatus/);
  // ADMIN_STATUS_CONTROL (preservado): campo Status do drawer e do modal Nova tarefa
  assert.match(semComentarios(ler("components/demandas/DemandaFormSections.tsx")), /salvarCampo\(demanda, \{ status: event\.target\.value as DemandaStatusEditavel \}/);
  assert.match(semComentarios(ler("components/demandas/NovaDemandaModal.tsx")), /updateDraft\(\{ status: event\.target\.value as DemandaStatusEditavel \}\)/);
  // OTHER: nenhuma outra tela leva a tarefa a em_execucao por PATCH
  for (const arquivo of ["components/demandas/EnvioClienteCard.tsx", "components/dashboard/DashboardView.tsx"]) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /status: ?"em_execucao"/, arquivo);
  }
});

test("o botão 'Iniciar trabalho' do card e o arrasto usam o MESMO comando", () => {
  const card = semComentarios(ler("components/demandas/DemandaKanbanCard.tsx"));
  assert.match(card, /demanda\.status === "em_execucao" && demanda\.podeIniciarTrabalho && !demanda\.trabalhandoAgora/);
  assert.match(card, /onClick=\{\(\) => onIniciarTrabalho\(demanda\.id\)\}/);
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /onIniciarTrabalho=\{onIniciarTrabalho\}/);
});
