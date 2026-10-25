// P1_KANBAN_FOCUS_SWITCH — o caminho REAL do arraste do Kanban: o que é chamado ao soltar um card. `npm run test:kanban-soltura`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { decidirSoltura, type EntradaSoltura } from "./kanban-soltura.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (codigo: string) => codigo.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

const EM_EXECUCAO = ["em_execucao"] as const;
const RASCUNHO_PLANEJADA = ["rascunho", "planejada"] as const;
const PAUSADA_BLOQUEADA = ["pausada", "bloqueada"] as const;

const base: EntradaSoltura = { statusDaColuna: EM_EXECUCAO, statusAtual: "planejada", podeIniciarTrabalho: true, trabalhandoAgora: false, podeIniciarNoExpediente: true };

test("executor elegível: soltar em Em execução vem de qualquer status e chama iniciar-trabalho (nunca um PATCH de status)", () => {
  for (const statusAtual of ["rascunho", "planejada", "pausada", "bloqueada", "aguardando_cliente"] as const) {
    assert.deepEqual(decidirSoltura({ ...base, statusAtual }), { acao: "iniciar-trabalho" }, statusAtual);
  }
});

test("1º arrasto cria a sessão MESMO se a tarefa já está em Em execução sem sessão da pessoa (status posto pelo drawer ou criada já em execução)", () => {
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", trabalhandoAgora: false }), { acao: "iniciar-trabalho" });
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", trabalhandoAgora: undefined }), { acao: "iniciar-trabalho" });
});

test("idempotência: quem JÁ trabalha na tarefa (sessão ativa) ou não é executor não dispara nada ao soltar na própria coluna", () => {
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", trabalhandoAgora: true }), { acao: "nada" });
  // gestor/atendimento que organiza o trabalho de outros: a tarefa já está lá, nada a fazer (nenhuma sessão pessoal nasce por acaso)
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", podeIniciarTrabalho: false }), { acao: "nada" });
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", podeIniciarTrabalho: undefined }), { acao: "nada" });
});

test("gestor não executor movendo de outra coluna: continua indo a iniciar-trabalho — é o SERVIDOR que decide (status-only sem sessão pessoal)", () => {
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "planejada", podeIniciarTrabalho: false }), { acao: "iniciar-trabalho" });
});

test("fora do expediente: bloqueia o início — também ao soltar tarefa já em execução sem sessão — e não bloqueia o que não é iniciar", () => {
  assert.deepEqual(decidirSoltura({ ...base, podeIniciarNoExpediente: false }), { acao: "bloqueado-expediente" });
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", podeIniciarNoExpediente: false }), { acao: "bloqueado-expediente" });
  assert.deepEqual(decidirSoltura({ ...base, statusAtual: "em_execucao", trabalhandoAgora: true, podeIniciarNoExpediente: false }), { acao: "nada" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "em_execucao", podeIniciarNoExpediente: false }), { acao: "mover", novoStatus: "pausada" });
});

test("as demais colunas seguem o PATCH de status (destino = primeiro status da coluna) e soltar na própria coluna é um no-op", () => {
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "pausada" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: RASCUNHO_PLANEJADA, statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "rascunho" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: ["concluida"], statusAtual: "em_execucao" }), { acao: "mover", novoStatus: "concluida" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: PAUSADA_BLOQUEADA, statusAtual: "bloqueada" }), { acao: "nada" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: RASCUNHO_PLANEJADA, statusAtual: "planejada" }), { acao: "nada" });
  assert.deepEqual(decidirSoltura({ ...base, statusDaColuna: [] }), { acao: "nada" });
});

test("nenhuma combinação leva um card a Em execução por PATCH de status", () => {
  const statuses = ["rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente", "concluida", "cancelada"] as const;
  for (const statusAtual of statuses)
    for (const podeIniciarTrabalho of [true, false, undefined])
      for (const trabalhandoAgora of [true, false, undefined])
        for (const podeIniciarNoExpediente of [true, false]) {
          const d = decidirSoltura({ statusDaColuna: EM_EXECUCAO, statusAtual, podeIniciarTrabalho, trabalhandoAgora, podeIniciarNoExpediente });
          assert.notEqual(d.acao, "mover");
        }
});

// ── fiação (source-scan): do soltar do card até o servidor e de volta à tela ─────────────────────────────────────────

test("handleDragEnd usa a decisão pura e só chama iniciar-trabalho/PATCH conforme ela; o motor dnd-kit não mudou", () => {
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /import \{ decidirSoltura \} from "@\/lib\/kanban-soltura";/);
  assert.match(kanban, /const decisao = decidirSoltura\(\{/);
  assert.match(kanban, /if \(decisao\.acao === "iniciar-trabalho"\) onIniciarTrabalho\(demanda\.id\);\s*else onMoveDemanda\(demanda\.id, decisao\.novoStatus\);/);
  assert.match(kanban, /useSensor\(PointerSensor, \{ activationConstraint: \{ distance: 8 \} \}\)/); // sensores intocados
  assert.doesNotMatch(kanban, /console\.(log|debug)/);
  // o frontend nunca "inventa" o status da tarefa anterior
  assert.doesNotMatch(kanban, /onMoveDemanda\([^)]*"pausada"|status: ?"pausada"/);
});

test("a tela só confia no servidor: iniciar-trabalho → resposta + refetch + estatísticas; nenhum otimismo sobre sessão nem sobre a tarefa anterior", () => {
  const view = semComentarios(ler("components/demandas/DemandasView.tsx"));
  const trecho = /async function iniciarTrabalho\(demandaId: string\) \{[\s\S]*?\n  \}\n/.exec(view)?.[0] ?? "";
  assert.match(trecho, /iniciarTrabalhoDemandaReal\(demandaId\)/);
  assert.match(trecho, /setRefetchTick\(\(tick\) => tick \+ 1\)/);
  assert.match(trecho, /setEstatisticasTick\(\(tick\) => tick \+ 1\)/);
  assert.match(trecho, /catch \(error\) \{\s*setErro\(mensagemDeErro\(error\)\)/);
  assert.doesNotMatch(trecho, /status: ?"pausada"|"pausada"|"em_execucao"/);
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /`\/demandas\/\$\{encodeURIComponent\(demandaId\)\}\/iniciar-trabalho`, \{ method: "POST"/);
});

test("o botão 'Iniciar trabalho' do card e o arrasto usam o MESMO comando", () => {
  const card = semComentarios(ler("components/demandas/DemandaKanbanCard.tsx"));
  assert.match(card, /demanda\.status === "em_execucao" && demanda\.podeIniciarTrabalho && !demanda\.trabalhandoAgora/);
  assert.match(card, /onClick=\{\(\) => onIniciarTrabalho\(demanda\.id\)\}/);
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /onIniciarTrabalho=\{onIniciarTrabalho\}/);
});
