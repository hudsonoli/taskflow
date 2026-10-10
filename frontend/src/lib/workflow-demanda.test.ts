// Fase 8A — progressão do workflow da Demanda. `npm run test:workflow-demanda`.
// Lógica pura exercitada de verdade; tela e API (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  WorkflowEtapaConflitoError,
  acaoDaEtapa,
  avancarEtapaDoWorkflow,
  estadoDaEtapa,
  etapasOrdenadas,
  ehUltimaEtapa,
  perguntaDeConfirmacao,
  podeExibirAcao,
  rotuloDaAcao,
  rotuloEstadoConcluido,
  rotuloQuemConcluiu,
  workflowConcluido,
} from "./workflow-demanda.ts";
import type { DemandaWorkflowEtapa } from "../types/demanda.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function etapa(ordem: number, extra: Partial<DemandaWorkflowEtapa> = {}): DemandaWorkflowEtapa {
  return {
    id: `e${ordem}`, nome: `Etapa ${ordem}`, ordem, tipo: "execucao", quantidadeAntesDeadline: 1, unidadePrazo: "dias_corridos",
    usuarioResponsavelIds: [], departamentoResponsavelIds: [], status: "pendente", iniciadaEm: null, concluidaEm: null,
    concluidaPorUsuarioId: null, podeAvancar: false, ...extra,
  };
}

const demanda = (etapas: DemandaWorkflowEtapa[], etapaAtualId: string | null) => ({ workflowEtapas: etapas, etapaAtualId });

// ── timeline: concluídas → atual → pendentes ───────────────────────────────────────────────────────────────────

test("timeline: etapas ordenadas pela ordem do servidor e estado derivado de etapaAtualId/status", () => {
  const etapas = [
    etapa(3, { tipo: "aprovacao" }),
    etapa(1, { status: "concluida", concluidaEm: "2026-10-10T10:00:00Z" }),
    etapa(2, { podeAvancar: true }),
    etapa(4),
  ];
  const d = demanda(etapas, "e2");
  assert.deepEqual(etapasOrdenadas(d).map((e) => e.ordem), [1, 2, 3, 4]);
  assert.deepEqual(etapasOrdenadas(d).map((e) => estadoDaEtapa(e, d.etapaAtualId)), ["concluida", "atual", "pendente", "pendente"]);
  assert.equal(workflowConcluido(d), false);
});

test("o cliente não reordena nem recalcula a etapa atual: etapa não concluída fora de etapaAtualId é pendente", () => {
  assert.equal(estadoDaEtapa(etapa(1), "outra"), "pendente");
  assert.equal(estadoDaEtapa(etapa(1, { status: "em_execucao" }), "e1"), "atual");
});

test("workflow concluído = tem etapas e nenhuma é a atual; sem workflow não é 'concluído'", () => {
  const todas = [etapa(1, { status: "concluida" }), etapa(2, { status: "concluida" })];
  assert.equal(workflowConcluido(demanda(todas, null)), true);
  assert.equal(workflowConcluido(demanda([], null)), false);
});

// ── ação por tipo ──────────────────────────────────────────────────────────────────────────────────────────────

test("execução → Concluir etapa; aprovação → Aprovar etapa", () => {
  assert.equal(acaoDaEtapa(etapa(1)), "concluir");
  assert.equal(rotuloDaAcao(etapa(1)), "Concluir etapa");
  assert.equal(acaoDaEtapa(etapa(3, { tipo: "aprovacao" })), "aprovar");
  assert.equal(rotuloDaAcao(etapa(3, { tipo: "aprovacao" })), "Aprovar etapa");
});

test("completedBy: 'Aprovada por' na aprovação e 'Concluída por' na execução (um único campo persistido)", () => {
  assert.equal(rotuloQuemConcluiu(etapa(3, { tipo: "aprovacao" })), "Aprovada por");
  assert.equal(rotuloQuemConcluiu(etapa(1)), "Concluída por");
  assert.equal(rotuloEstadoConcluido(etapa(3, { tipo: "aprovacao" })), "Aprovada");
  assert.equal(rotuloEstadoConcluido(etapa(1)), "Concluída");
});

// ── quando existe botão ────────────────────────────────────────────────────────────────────────────────────────

test("botão: só na etapa atual, quando o SERVIDOR disse podeAvancar e o drawer não é somente leitura", () => {
  const atual = etapa(2, { podeAvancar: true });
  assert.equal(podeExibirAcao(atual, "e2", false), true); // responsável / gestor / Head autorizado
  assert.equal(podeExibirAcao(etapa(2, { podeAvancar: false }), "e2", false), false); // sem autoridade → sem ação
  assert.equal(podeExibirAcao(atual, "e2", true), false); // Pauta global: somente leitura
  assert.equal(podeExibirAcao(etapa(3, { podeAvancar: true }), "e2", false), false); // futura nunca
  assert.equal(podeExibirAcao(etapa(1, { status: "concluida", podeAvancar: true }), "e1", false), false); // concluída nunca
});

test("a decisão não olha perfil/departamento: depende só de podeAvancar (o frontend não reconstrói RBAC)", () => {
  const lib = semComentarios(ler("lib/workflow-demanda.ts"));
  assert.doesNotMatch(lib, /perfil|departamentoId|liderDepartamento|isAdmin|gestor/i);
  const tela = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
  const secao = tela.slice(tela.indexOf("export function WorkflowDemandaSection"), tela.indexOf("export function ResponsaveisDemandaSection"));
  assert.doesNotMatch(secao, /perfil|liderDepartamento|useAuth|usuarioAtual/i);
  assert.match(secao, /podeExibirAcao\(etapa, demanda\.etapaAtualId, somenteLeitura\)/);
  assert.match(secao, /useEscopoLeituraDemanda\(\) !== undefined/); // Pauta global lê somente
});

// ── confirmação ────────────────────────────────────────────────────────────────────────────────────────────────

test("confirmação simples: pergunta por tipo; na última etapa deixa claro que conclui o workflow, não a tarefa", () => {
  const etapas = [etapa(1), etapa(2, { tipo: "aprovacao" }), etapa(3)];
  const d = demanda(etapas, "e1");
  assert.equal(perguntaDeConfirmacao(d, etapas[0]), "Concluir esta etapa e avançar para a próxima?");
  assert.equal(perguntaDeConfirmacao(d, etapas[1]), "Aprovar esta etapa e avançar para a próxima?");
  assert.equal(ehUltimaEtapa(d, etapas[2]), true);
  assert.equal(ehUltimaEtapa(d, etapas[1]), false);
  const ultima = perguntaDeConfirmacao(d, etapas[2]);
  assert.match(ultima, /conclui o workflow, mas não conclui a tarefa/);
  const ultimaAprov = perguntaDeConfirmacao(demanda([etapa(1), etapa(2, { tipo: "aprovacao" })], "e1"), etapa(2, { tipo: "aprovacao" }));
  assert.match(ultimaAprov, /^Aprovar esta etapa conclui o workflow/);
});

// ── loading, sucesso e 409 ─────────────────────────────────────────────────────────────────────────────────────

test("sucesso: devolve a demanda atualizada pelo servidor (sem reload) e escolhe a ação pelo tipo", async () => {
  const chamadas: Array<[string, string]> = [];
  const atualizada = { ...demanda([etapa(1, { status: "concluida" }), etapa(2)], "e2"), id: "d1" };
  const r = await avancarEtapaDoWorkflow({
    etapa: etapa(1),
    avancar: async (acao, etapaId) => { chamadas.push([acao, etapaId]); return atualizada; },
    recarregar: async () => { throw new Error("não deve recarregar em sucesso"); },
  });
  assert.deepEqual(chamadas, [["concluir", "e1"]]);
  assert.equal(r.ok, true);
  if (r.ok) assert.equal(r.demanda, atualizada);

  const aprov: Array<[string, string]> = [];
  await avancarEtapaDoWorkflow({
    etapa: etapa(3, { tipo: "aprovacao" }),
    avancar: async (acao, etapaId) => { aprov.push([acao, etapaId]); return atualizada; },
    recarregar: async () => atualizada,
  });
  assert.deepEqual(aprov, [["aprovar", "e3"]]);
});

test("409: recarrega o estado do servidor e devolve a mensagem clara", async () => {
  const doServidor = { ...demanda([etapa(1, { status: "concluida" }), etapa(2)], "e2"), id: "d1" };
  let recarregou = 0;
  const r = await avancarEtapaDoWorkflow({
    etapa: etapa(1),
    avancar: async () => { throw new WorkflowEtapaConflitoError("Esta não é a etapa atual do workflow", "ETAPA_JA_CONCLUIDA"); },
    recarregar: async () => { recarregou += 1; return doServidor; },
  });
  assert.equal(r.ok, false);
  if (!r.ok) {
    assert.equal(r.conflito, true);
    assert.equal(r.mensagem, "Esta não é a etapa atual do workflow");
    assert.equal(r.demanda, doServidor);
  }
  assert.equal(recarregou, 1);
});

test("409 com recarga que falha: ainda devolve a mensagem; outros erros (403/rede) não recarregam", async () => {
  const falhaRecarga = await avancarEtapaDoWorkflow({
    etapa: etapa(1),
    avancar: async () => { throw new WorkflowEtapaConflitoError("workflow já concluído", "WORKFLOW_CONCLUIDO"); },
    recarregar: async () => { throw new Error("rede"); },
  });
  assert.equal(falhaRecarga.ok, false);
  if (!falhaRecarga.ok) assert.equal(falhaRecarga.demanda, undefined);

  let recarregou = false;
  const proibido = await avancarEtapaDoWorkflow({
    etapa: etapa(1),
    avancar: async () => { throw new Error("Você não tem autoridade para avançar esta etapa"); },
    recarregar: async () => { recarregou = true; return demanda([], null) as never; },
  });
  assert.equal(proibido.ok, false);
  if (!proibido.ok) {
    assert.equal(proibido.conflito, false);
    assert.match(proibido.mensagem, /autoridade/);
  }
  assert.equal(recarregou, false);
});

// ── tela e API ─────────────────────────────────────────────────────────────────────────────────────────────────

test("tela: desabilita durante a requisição, sem reload, sem nextStepId e com confirmação inline", () => {
  const tela = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
  const secao = tela.slice(tela.indexOf("export function WorkflowDemandaSection"), tela.indexOf("export function ResponsaveisDemandaSection"));
  assert.match(secao, /disabled=\{avancando\}/); // loading: botões desabilitados
  assert.match(secao, /Avançando…/);
  assert.doesNotMatch(secao, /location\.reload|router\.refresh|window\.confirm/);
  assert.match(secao, /onChange\(resultado\.demanda\)/); // atualiza o estado em memória
  assert.match(secao, /if \(resultado\.demanda\) onChange\(resultado\.demanda\)/); // 409: estado real do servidor
  assert.doesNotMatch(secao, /nextStepId|proximaEtapaId/);
  assert.match(secao, /rotuloDaAcao\(etapa\)/);
  assert.match(secao, /perguntaDeConfirmacao\(demanda, etapa\)/);
  assert.match(secao, /workflowConcluido\(demanda\)/);
  assert.match(secao, /não conclui a tarefa|decisão à parte/);
});

test("drawer: a seção de workflow recebe onChange (atualiza sem recarregar); fieldset já desabilita na leitura", () => {
  const drawer = semComentarios(ler("components/demandas/DemandaDetailsDrawer.tsx"));
  assert.match(drawer, /<WorkflowDemandaSection demanda=\{demanda\} onChange=\{onChange\} \/>/);
  assert.match(drawer, /<fieldset disabled=\{somenteLeitura\}/);
});

test("API: rotas concluir/aprovar sem corpo; 409 estruturado vira WorkflowEtapaConflitoError", () => {
  const api = ler("lib/api-backend.ts"); // sem semComentarios: o texto tem "/api/backend/**" em comentário (quebraria o regex)
  assert.match(api, /\/demandas\/\$\{demandaId\}\/workflow\/etapas\/\$\{etapaId\}\/\$\{acao\}/);
  const trecho = api.slice(api.indexOf("export async function avancarEtapaWorkflowReal"), api.indexOf("export async function restaurarDemandaReal"));
  assert.match(trecho, /method: "POST" \}/);
  assert.doesNotMatch(trecho, /body:/);
  assert.match(api, /response\.status === 409/);
  assert.match(api, /new WorkflowEtapaConflitoError\(/);
  // read model novo mapeado
  for (const campo of ["iniciadaEm", "concluidaEm", "concluidaPorUsuarioId", "podeAvancar"]) {
    assert.match(api, new RegExp(`${campo}:`), campo);
  }
});

test("Pauta/Meu Dia/Meu Departamento: nenhum escopo de leitura concede ação (podeAvancar vem do servidor e é zerado na Pauta)", () => {
  const pauta = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.match(pauta, /modoLeitura=/); // a Pauta abre o drawer em somente leitura
  const leitura = semComentarios(ler("components/demandas/leituraDemanda.tsx"));
  assert.match(leitura, /useEscopoLeituraDemanda/);
});

test("timeline do histórico descreve o avanço num único evento (etapa + próxima ou fim do workflow)", () => {
  const rotulos = ler("lib/historicoDemandaLabels.ts");
  assert.match(rotulos, /"demanda\.workflow_etapa_concluida":/);
  assert.match(rotulos, /"demanda\.workflow_etapa_aprovada":/);
  assert.match(rotulos, /avançou para/);
  assert.match(rotulos, /workflow concluído/);
  assert.match(rotulos, /tipo\.includes\("aprovad"\)/); // cor "concluído" também para aprovações
});
