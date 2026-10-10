// Fase 8D — rejeição/devolução de etapa do workflow. `npm run test:workflow-rejeicao`.
// Lógica pura exercitada de verdade; tela, API e rótulos (.tsx/.ts com alias `@/`) são lidos como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  MOTIVO_REJEICAO_MAX,
  WorkflowEtapaConflitoError,
  erroDoMotivo,
  etapaDeRetorno,
  podeExibirAcao,
  podeExibirRejeitar,
  rejeitarEtapaDoWorkflow,
  textoDoRetorno,
} from "./workflow-demanda.ts";
import type { DemandaWorkflowEtapa } from "../types/demanda.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function etapa(ordem: number, extra: Partial<DemandaWorkflowEtapa> = {}): DemandaWorkflowEtapa {
  return {
    id: `e${ordem}`, nome: `Etapa ${ordem}`, ordem, tipo: "execucao", quantidadeAntesDeadline: 1, unidadePrazo: "dias_corridos",
    usuarioResponsavelIds: [], departamentoResponsavelIds: [], status: "pendente", iniciadaEm: null, concluidaEm: null,
    concluidaPorUsuarioId: null, podeAvancar: false, podeRejeitar: false, ...extra,
  };
}

const fluxo = [etapa(1, { nome: "Criação", status: "concluida" }), etapa(2, { nome: "Aprovação", tipo: "aprovacao", podeAvancar: true, podeRejeitar: true }), etapa(3, { nome: "Publicação" })];
const demanda = (etapas: DemandaWorkflowEtapa[], etapaAtualId: string | null) => ({ workflowEtapas: etapas, etapaAtualId });

// ── botão Rejeitar ────────────────────────────────────────────────────────────────────────────────────────────

test("Rejeitar: só na etapa ATUAL de aprovação, quando o SERVIDOR disse podeRejeitar", () => {
  const aprovacao = fluxo[1];
  assert.equal(podeExibirRejeitar(aprovacao, "e2", false), true);
  assert.equal(podeExibirRejeitar({ ...aprovacao, podeRejeitar: false }, "e2", false), false); // sem autoridade / sem etapa anterior
  assert.equal(podeExibirRejeitar({ ...aprovacao, podeRejeitar: undefined }, "e2", false), false); // contrato antigo: sem botão
  assert.equal(podeExibirRejeitar(aprovacao, "e1", false), false); // não é a atual
  assert.equal(podeExibirRejeitar({ ...aprovacao, status: "concluida" }, "e2", false), false);
});

test("Rejeitar não aparece em etapa de execução nem na leitura da Pauta", () => {
  assert.equal(podeExibirRejeitar(etapa(1, { podeRejeitar: true }), "e1", false), false); // execução, mesmo que o flag viesse true
  assert.equal(podeExibirRejeitar(fluxo[1], "e2", true), false); // Pauta global: somente leitura
});

test("a decisão do botão não reconstrói RBAC: só lê podeRejeitar (e Aprovar continua independente)", () => {
  const lib = semComentarios(ler("lib/workflow-demanda.ts"));
  assert.doesNotMatch(lib, /perfil|liderDepartamento|isAdmin|gestor/i);
  assert.equal(podeExibirAcao(fluxo[1], "e2", false), true); // Aprovar segue podendo aparecer sozinho
});

// ── etapa de retorno e motivo ─────────────────────────────────────────────────────────────────────────────────

test("etapa de retorno = a imediatamente anterior por ordem; primeira etapa não tem", () => {
  assert.equal(etapaDeRetorno(demanda(fluxo, "e2"), fluxo[1])?.nome, "Criação");
  assert.equal(etapaDeRetorno(demanda(fluxo, "e3"), fluxo[2])?.nome, "Aprovação"); // não pula etapas
  assert.equal(etapaDeRetorno(demanda(fluxo, "e1"), fluxo[0]), null);
  const desordenado = [fluxo[2], fluxo[0], fluxo[1]];
  assert.equal(etapaDeRetorno(demanda(desordenado, "e2"), fluxo[1])?.nome, "Criação");
});

test("texto do modal informa o nome da etapa anterior", () => {
  assert.equal(textoDoRetorno("Criação"), "A etapa será devolvida para Criação.");
});

test("motivo obrigatório: vazio, só espaços, curto, longo e HTML são recusados; válido passa", () => {
  assert.match(erroDoMotivo("") ?? "", /Informe o motivo/);
  assert.match(erroDoMotivo("    ") ?? "", /Informe o motivo/);
  assert.match(erroDoMotivo("ab") ?? "", /ao menos 3/);
  assert.match(erroDoMotivo("x".repeat(MOTIVO_REJEICAO_MAX + 1)) ?? "", /no máximo 1000/);
  assert.match(erroDoMotivo("<b>negrito</b>") ?? "", /HTML/);
  assert.equal(erroDoMotivo("Ajustar o logotipo"), null);
  assert.equal(erroDoMotivo("x".repeat(MOTIVO_REJEICAO_MAX)), null);
  assert.equal(erroDoMotivo("a < b mas sem tag"), null); // só recusa tag (< e >) — o servidor aplica a mesma regra
});

// ── envio, loading, sucesso e 409 ─────────────────────────────────────────────────────────────────────────────

test("sucesso: manda SÓ o motivo (aparado), devolve o estado do servidor sem reload", async () => {
  const chamadas: Array<[string, string]> = [];
  const novo = { ...demanda([etapa(1), etapa(2, { tipo: "aprovacao" }), etapa(3)], "e1"), id: "d1" };
  const r = await rejeitarEtapaDoWorkflow({
    etapaId: "e2",
    motivo: "  Ajustar o logotipo  ",
    rejeitar: async (etapaId, motivo) => { chamadas.push([etapaId, motivo]); return novo; },
    recarregar: async () => { throw new Error("não deve recarregar em sucesso"); },
  });
  assert.deepEqual(chamadas, [["e2", "Ajustar o logotipo"]]);
  assert.equal(r.ok, true);
  if (r.ok) assert.equal(r.demanda.etapaAtualId, "e1"); // a etapa anterior voltou a ser a atual
});

test("motivo inválido nem chega ao servidor", async () => {
  let chamou = false;
  const r = await rejeitarEtapaDoWorkflow({
    etapaId: "e2", motivo: "  ", rejeitar: async () => { chamou = true; return demanda([], null) as never; }, recarregar: async () => demanda([], null) as never,
  });
  assert.equal(r.ok, false);
  assert.equal(chamou, false);
});

test("409: recarrega o workflow e devolve a mensagem; erro comum não recarrega (o modal fica aberto com o motivo)", async () => {
  const doServidor = { ...demanda([etapa(1, { status: "concluida" }), etapa(2)], "e2"), id: "d1" };
  let recarregou = 0;
  const conflito = await rejeitarEtapaDoWorkflow({
    etapaId: "e2", motivo: "Motivo válido",
    rejeitar: async () => { throw new WorkflowEtapaConflitoError("Esta não é a etapa atual do workflow", "ETAPA_NAO_ATUAL"); },
    recarregar: async () => { recarregou += 1; return doServidor; },
  });
  assert.equal(conflito.ok, false);
  if (!conflito.ok) {
    assert.equal(conflito.conflito, true);
    assert.equal(conflito.demanda, doServidor);
  }
  assert.equal(recarregou, 1);

  const comum = await rejeitarEtapaDoWorkflow({
    etapaId: "e2", motivo: "Motivo válido",
    rejeitar: async () => { throw new Error("Você não tem autoridade para avançar esta etapa"); },
    recarregar: async () => { recarregou += 1; return doServidor; },
  });
  assert.equal(comum.ok, false);
  if (!comum.ok) assert.equal(comum.conflito, false);
  assert.equal(recarregou, 1); // não recarregou de novo
});

test("SEM_ETAPA_ANTERIOR é tratado como conflito de workflow (recarrega)", () => {
  assert.match(ler("lib/workflow-demanda.ts"), /"SEM_ETAPA_ANTERIOR"/);
});

// ── tela, API e timeline ──────────────────────────────────────────────────────────────────────────────────────

const tela = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
const secao = tela.slice(tela.indexOf("export function WorkflowDemandaSection"), tela.indexOf("export function ResponsaveisDemandaSection"));

test("tela: Rejeitar é secundário, ao lado de Aprovar, e abre modal com motivo obrigatório e nome da etapa anterior", () => {
  assert.match(secao, /variant="secondary" onClick=\{\(\) => abrirRejeicao\(etapa\)\}/);
  assert.match(secao, /podeExibirRejeitar\(etapa, demanda\.etapaAtualId, somenteLeitura\)/);
  assert.match(secao, /Motivo da rejeição \*/);
  assert.match(secao, /textoDoRetorno\(etapaDeRetorno\(demanda, rejeitando\)\?\.nome/);
  assert.match(secao, /Rejeitar e devolver/);
  assert.match(secao, /Cancelar/);
  assert.doesNotMatch(secao, /window\.confirm/); // sem segundo modal: o motivo já é a confirmação
});

test("tela: loading desabilita o envio; botão só habilita com motivo válido; atualiza sem reload", () => {
  assert.match(secao, /disabled=\{avancando \|\| erroDoMotivo\(motivo\) !== null\}/);
  assert.match(secao, /Rejeitando…/);
  assert.match(secao, /if \(avancando \|\| !rejeitando\) return;/);
  assert.doesNotMatch(secao, /location\.reload|router\.refresh/);
  assert.match(secao, /setRejeitando\(null\);\s*onChange\(resultado\.demanda\);/);
});

test("tela: 409 fecha o modal, mostra a mensagem e atualiza o workflow; erro comum mantém o modal e o motivo", () => {
  assert.match(secao, /if \(resultado\.conflito\) \{[\s\S]*?setRejeitando\(null\);[\s\S]*?setErro\(resultado\.mensagem\);[\s\S]*?onChange\(resultado\.demanda\)/);
  assert.match(secao, /setErroRejeicao\(resultado\.mensagem\);/); // não limpa o motivo
});

test("tela: na leitura da Pauta o botão não existe (somenteLeitura vem do contexto) e o servidor zera podeRejeitar", () => {
  assert.match(secao, /useEscopoLeituraDemanda\(\) !== undefined/);
});

test("API: POST /rejeitar manda SÓ { motivo } (sem targetStepId) e mapeia podeRejeitar", () => {
  const api = ler("lib/api-backend.ts");
  const trecho = api.slice(api.indexOf("export async function rejeitarEtapaWorkflowReal"), api.indexOf("export async function restaurarDemandaReal"));
  assert.match(trecho, /\/workflow\/etapas\/\$\{etapaId\}\/rejeitar/);
  assert.match(trecho, /JSON\.stringify\(\{ motivo \}\)/);
  assert.doesNotMatch(trecho, /targetStepId|previousStepId|etapaRetorno/);
  assert.match(api, /podeRejeitar: etapa\.podeRejeitar === true/);
});

test("timeline: rejeição aparece com motivo e etapa de retorno; eventos anteriores continuam (append-only)", () => {
  const rotulos = ler("lib/historicoDemandaLabels.ts");
  assert.match(rotulos, /"demanda\.workflow_etapa_rejeitada": \(dados\) => descreverRejeicaoDeEtapa\(dados\)/);
  assert.match(rotulos, /rejeitada\$\{retorno\}\$\{motivo\}/);
  assert.match(rotulos, /devolvida para/);
  assert.match(rotulos, /Motivo: /);
  assert.match(rotulos, /"demanda\.workflow_etapa_concluida":/); // os anteriores seguem descritos
  assert.match(rotulos, /tipo\.includes\("rejeitad"\)/);
});

test("segundo ciclo: depois de devolvida, a aprovação volta a ser pendente e pode ser aprovada/rejeitada de novo", () => {
  // estado devolvido: Criação atual (pendente), Aprovação pendente (sem conclusão)
  const devolvido = demanda([etapa(1, { nome: "Criação", podeAvancar: true }), etapa(2, { tipo: "aprovacao" }), etapa(3)], "e1");
  assert.equal(podeExibirRejeitar(devolvido.workflowEtapas[1], devolvido.etapaAtualId, false), false); // ainda não é a atual
  // refeita a Criação, a aprovação volta a ser a atual com podeRejeitar do servidor
  const segundoCiclo = demanda([etapa(1, { status: "concluida" }), etapa(2, { tipo: "aprovacao", podeAvancar: true, podeRejeitar: true }), etapa(3)], "e2");
  assert.equal(podeExibirRejeitar(segundoCiclo.workflowEtapas[1], segundoCiclo.etapaAtualId, false), true);
  assert.equal(podeExibirAcao(segundoCiclo.workflowEtapas[1], segundoCiclo.etapaAtualId, false), true);
});
