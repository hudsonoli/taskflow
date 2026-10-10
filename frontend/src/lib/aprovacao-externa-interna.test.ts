// Fase 9B — Portal Externo de Aprovação, lado INTERNO. `npm run test:aprovacao-externa-interna`.
// Lógica pura exercitada de verdade; tela, API e rótulos (.tsx/.ts com alias `@/`) são lidos como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  ARQUIVOS_MAX,
  AVISO_LINK_UNICO,
  acoesDoPainel,
  alternarArquivo,
  arquivoElegivelParaAprovacao,
  criarLinkDeAprovacao,
  descreverDecisaoInterna,
  deveRenderizarPainel,
  erroDaCriacao,
  erroDaInstrucao,
  linkDeAprovacao,
  montarEntradaDeCriacao,
  ordenarContatos,
  podeExibirBlocoAprovacao,
} from "./aprovacao-externa.ts";
import { WorkflowEtapaConflitoError, ehConflitoDeWorkflow, rotuloAprovadaExternamente } from "./workflow-demanda.ts";
import type { AprovacaoExterna, AprovacaoExternaCriada } from "../types/aprovacao-externa.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/^\s*\/\/.*$/gm, "");

const TOKEN = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-_AbCdE".slice(0, 43);

function aprovacao(extra: Partial<AprovacaoExterna> = {}): AprovacaoExterna {
  return {
    id: "ap-1", etapaId: "e2", estado: "pendente", instrucao: null, criadaEm: "2026-10-10T10:00:00Z", criadaPorNome: "Bia",
    expiraEm: "2026-10-17T10:00:00Z", revogadaEm: null, revogadaMotivo: null, destinatarioNome: null, destinatarioEmail: null,
    artefatos: [], decisao: null, ...extra,
  };
}

// ── link e aviso de exibição única ────────────────────────────────────────────────────────────────────────────

test("o link usa o FRAGMENTO (#token=) — o token não vai ao servidor web nem a path/query", () => {
  const link = linkDeAprovacao("https://app.exemplo.com/", TOKEN);
  assert.equal(link, `https://app.exemplo.com/aprovacao#token=${TOKEN}`);
  assert.doesNotMatch(link, /\?token=|\/aprovacao\/[A-Za-z0-9_-]{43}/);
});

test("aviso de link exibido uma única vez", () => {
  assert.equal(AVISO_LINK_UNICO, "O link é exibido somente agora. Para gerar outro, revogue e crie um novo.");
});

// ── onde o bloco aparece e o que ele permite ─────────────────────────────────────────────────────────────────

test("o bloco só existe na etapa ATUAL de APROVAÇÃO, fora da leitura da Pauta", () => {
  const e = { id: "e2", tipo: "aprovacao" as const, status: "pendente" as const };
  assert.equal(podeExibirBlocoAprovacao(e, "e2", false), true);
  assert.equal(podeExibirBlocoAprovacao(e, "e1", false), false); // não é a atual
  assert.equal(podeExibirBlocoAprovacao({ ...e, tipo: "execucao" }, "e2", false), false);
  assert.equal(podeExibirBlocoAprovacao({ ...e, status: "concluida" }, "e2", false), false);
  assert.equal(podeExibirBlocoAprovacao(e, "e2", true), false); // Pauta global: somente leitura
});

test("sem autoridade e sem histórico de link, nada é renderizado; ações dependem SÓ do podeGerenciar do servidor", () => {
  assert.equal(deveRenderizarPainel(null), false);
  assert.equal(deveRenderizarPainel({ podeGerenciar: false, atual: null }), false);
  assert.equal(deveRenderizarPainel({ podeGerenciar: false, atual: aprovacao() }), true); // quem vê o contexto vê o estado, sem ações
  assert.deepEqual(acoesDoPainel({ podeGerenciar: false, atual: aprovacao() }), { gerarNovo: false, revogar: false });
  assert.deepEqual(acoesDoPainel({ podeGerenciar: true, atual: null }), { gerarNovo: true, revogar: false });
  assert.deepEqual(acoesDoPainel({ podeGerenciar: true, atual: aprovacao() }), { gerarNovo: true, revogar: true });
  assert.deepEqual(acoesDoPainel({ podeGerenciar: true, atual: aprovacao({ estado: "ajustes_solicitados" }) }), { gerarNovo: true, revogar: false });
  assert.deepEqual(acoesDoPainel({ podeGerenciar: true, atual: aprovacao({ estado: "revogada" }) }), { gerarNovo: true, revogar: false });
  assert.deepEqual(acoesDoPainel({ podeGerenciar: true, atual: aprovacao({ estado: "expirada" }) }), { gerarNovo: true, revogar: false });
  assert.deepEqual(acoesDoPainel({ podeGerenciar: true, atual: aprovacao({ estado: "aprovada" }) }), { gerarNovo: false, revogar: false }); // decidida não se revoga
});

test("a lib não reconstrói RBAC (perfil/departamento/Head/Atendimento)", () => {
  const lib = semComentarios(ler("lib/aprovacao-externa.ts"));
  assert.doesNotMatch(lib, /perfil|liderDepartamento|isAdmin|gestor|atendimento|departamento/i);
});

// ── seleção de arquivos ──────────────────────────────────────────────────────────────────────────────────────

test("elegibilidade: layout/anexo físico PNG/JPG/PDF; link e outros tipos nunca", () => {
  const base = { id: "a", tipo: "layout", contentType: "image/png", nomeOriginal: "a.png" };
  assert.equal(arquivoElegivelParaAprovacao(base), true);
  assert.equal(arquivoElegivelParaAprovacao({ ...base, tipo: "anexo", contentType: "application/pdf" }), true);
  assert.equal(arquivoElegivelParaAprovacao({ ...base, contentType: "image/jpeg" }), true);
  assert.equal(arquivoElegivelParaAprovacao({ ...base, tipo: "link", contentType: null, nomeOriginal: null }), false);
  assert.equal(arquivoElegivelParaAprovacao({ ...base, contentType: "image/gif" }), false);
  assert.equal(arquivoElegivelParaAprovacao({ ...base, contentType: "text/html" }), false);
});

test("seleção: alterna, não repete e respeita o teto de 10", () => {
  assert.deepEqual(alternarArquivo([], "a"), ["a"]);
  assert.deepEqual(alternarArquivo(["a", "b"], "a"), ["b"]);
  const cheio = Array.from({ length: ARQUIVOS_MAX }, (_, i) => `f${i}`);
  assert.deepEqual(alternarArquivo(cheio, "novo"), cheio); // acima do teto: ignora
  assert.deepEqual(alternarArquivo(cheio, "f0"), cheio.slice(1)); // mas remover sempre pode
});

test("validação da criação: ao menos um arquivo, no máximo 10, instrução sem HTML e até 1000", () => {
  assert.match(erroDaCriacao({ arquivoIds: [], instrucao: "" }) ?? "", /ao menos um arquivo/);
  assert.equal(erroDaCriacao({ arquivoIds: ["a"], instrucao: "" }), null);
  assert.match(erroDaCriacao({ arquivoIds: Array.from({ length: 11 }, (_, i) => `f${i}`), instrucao: "" }) ?? "", /no máximo 10/);
  assert.match(erroDaInstrucao("<b>oi</b>") ?? "", /HTML/);
  assert.match(erroDaInstrucao("x".repeat(1001)) ?? "", /1000/);
  assert.equal(erroDaInstrucao("Aprovar a arte final."), null);
});

test("entrada da criação: destinatário é SNAPSHOT do contato (nome/e-mail), nunca id do contato", () => {
  const entrada = montarEntradaDeCriacao({
    arquivoIds: ["a"], instrucao: "  Veja  ", validadeDias: 7,
    contato: { nome: "Maria", email: "m@c.com", cargo: "Dir", recebeEntregas: true },
  });
  assert.deepEqual(entrada, { arquivoIds: ["a"], instrucao: "Veja", validadeDias: 7, destinatarioNome: "Maria", destinatarioEmail: "m@c.com" });
  const sem = montarEntradaDeCriacao({ arquivoIds: ["a"], instrucao: "   ", validadeDias: 3, contato: null });
  assert.deepEqual(sem, { arquivoIds: ["a"], instrucao: null, validadeDias: 3, destinatarioNome: null, destinatarioEmail: null });
});

test("contatos: quem recebe entregas vem primeiro (ordem estável)", () => {
  const ordenados = ordenarContatos([
    { nome: "A", email: null, cargo: null, recebeEntregas: false },
    { nome: "B", email: null, cargo: null, recebeEntregas: true },
    { nome: "C", email: null, cargo: null, recebeEntregas: false },
  ]);
  assert.deepEqual(ordenados.map((c) => c.nome), ["B", "A", "C"]);
});

// ── fluxo de criação ─────────────────────────────────────────────────────────────────────────────────────────

test("criar: sucesso devolve o token UMA vez; sem arquivo nem chega ao servidor", async () => {
  let chamadas = 0;
  const criada = { ...aprovacao(), token: TOKEN } as AprovacaoExternaCriada;
  const ok = await criarLinkDeAprovacao({
    corpo: { arquivoIds: ["a"], validadeDias: 7 },
    criar: async () => { chamadas += 1; return criada; },
    ehConflito: ehConflitoDeWorkflow,
  });
  assert.equal(ok.ok, true);
  if (ok.ok) assert.equal(ok.criada.token, TOKEN);
  const vazio = await criarLinkDeAprovacao({
    corpo: { arquivoIds: [], validadeDias: 7 },
    criar: async () => { chamadas += 1; return criada; },
    ehConflito: ehConflitoDeWorkflow,
  });
  assert.equal(vazio.ok, false);
  assert.equal(chamadas, 1);
});

test("criar: 409 de workflow vira conflito (fecha e recarrega); outro erro mantém o modal", async () => {
  const conflito = await criarLinkDeAprovacao({
    corpo: { arquivoIds: ["a"], validadeDias: 7 },
    criar: async () => { throw new WorkflowEtapaConflitoError("Esta não é a etapa atual do workflow", "ETAPA_NAO_ATUAL"); },
    ehConflito: ehConflitoDeWorkflow,
  });
  assert.deepEqual(conflito, { ok: false, mensagem: "Esta não é a etapa atual do workflow", conflito: true });
  const comum = await criarLinkDeAprovacao({
    corpo: { arquivoIds: ["a"], validadeDias: 7 },
    criar: async () => { throw new Error("Você não tem autoridade para gerenciar a aprovação externa desta etapa"); },
    ehConflito: ehConflitoDeWorkflow,
  });
  assert.equal(comum.ok, false);
  if (!comum.ok) assert.equal(comum.conflito, false);
});

test("decisão exibida ao usuário interno deixa claro que a identidade é declarada", () => {
  const texto = descreverDecisaoInterna(
    aprovacao({ estado: "aprovada", decisao: { decisao: "aprovada", decididaEm: "2026-10-11T10:00:00Z", nomeAprovador: "Maria Cliente", emailAprovador: null, motivo: null } }),
  );
  assert.match(texto ?? "", /Aprovado por Maria Cliente/);
  assert.match(texto ?? "", /declarada, não verificada/);
  assert.equal(descreverDecisaoInterna(aprovacao()), null);
  assert.equal(rotuloAprovadaExternamente("Maria"), "Aprovada externamente por Maria");
});

// ── tela, API, timeline ──────────────────────────────────────────────────────────────────────────────────────

const bloco = semComentarios(ler("components/demandas/AprovacaoExternaBloco.tsx"));
const secoes = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
const api = ler("lib/api-backend.ts");

test("tela: bloco 'Aprovação do cliente' na aba Workflow, só na etapa atual de aprovação", () => {
  assert.match(bloco, /Aprovação do cliente/);
  assert.match(secoes, /podeExibirBlocoAprovacao\(etapa, demanda\.etapaAtualId, somenteLeitura\)/);
  assert.match(secoes, /<AprovacaoExternaBloco demanda=\{demanda\} etapa=\{etapa\} onChange=\{onChange\} \/>/);
});

test("tela: o link aparece uma vez, com copiar e o aviso; fechar descarta o token; revogar pede confirmação", () => {
  assert.match(bloco, /AVISO_LINK_UNICO/);
  assert.match(bloco, /Copiar link/);
  assert.match(bloco, /navigator\.clipboard\.writeText/);
  assert.match(bloco, /linkDeAprovacao\(window\.location\.origin, resultado\.criada\.token\)/);
  assert.match(bloco, /Revogar link/);
  assert.match(bloco, /Confirmar revogação/);
  assert.match(bloco, /Gerar novo link/);
});

test("tela: o token vive só em memória (nada de storage, cookie, console, URL ou dangerouslySetInnerHTML)", () => {
  assert.doesNotMatch(bloco, /localStorage|sessionStorage|document\.cookie|console\.|dangerouslySetInnerHTML|history\.(push|replace)State/);
  assert.doesNotMatch(bloco, /router\.(push|replace)/);
});

test("tela: contatos do Cliente alimentam o destinatário (sem id de contato) e a validade tem opções 1..30", () => {
  assert.match(bloco, /Para quem é o link/);
  assert.match(bloco, /recebe entregas/);
  assert.match(bloco, /VALIDADES_DIAS/);
  assert.match(bloco, /painel\.validadePadraoDias/);
});

test("API: criar/consultar/revogar usam as rotas do servidor e não guardam token", () => {
  const trecho = api.slice(api.indexOf("export async function getAprovacaoExternaPainel"), api.indexOf("export async function restaurarDemandaReal"));
  assert.match(trecho, /\/workflow\/etapas\/\$\{etapaId\}\/aprovacao-externa/);
  assert.match(trecho, /aprovacao-externa\/\$\{aprovacaoId\}\/revogar/);
  assert.doesNotMatch(trecho, /localStorage|sessionStorage|console\./);
  assert.match(api, /concluidaPorExternoNome: etapa\.concluidaPorExternoNome \?\? null/);
});

test("workflow: etapa aprovada pelo cliente mostra 'Aprovada externamente por <nome>' (não um usuário)", () => {
  assert.match(secoes, /rotuloAprovadaExternamente\(etapa\.concluidaPorExternoNome\)/);
});

test("timeline: eventos do link e autor externo (nome declarado, nunca 'Sistema')", () => {
  const rotulos = ler("lib/historicoDemandaLabels.ts");
  for (const tipo of ["aprovacao_externa_criada", "aprovacao_externa_revogada", "aprovacao_externa_aprovada", "aprovacao_externa_ajustes"]) {
    assert.match(rotulos, new RegExp(`"demanda\\.${tipo}"`));
  }
  assert.match(rotulos, /externamente/);
  assert.match(rotulos, /ajustes solicitados pelo cliente/);
  assert.match(secoes, /autorExternoDoEvento\(evento\.dados\)/);
  assert.match(secoes, /identidade declarada/);
  assert.match(secoes, /\{autorDoEvento\(evento\)\} ·/);
});

test("regressão: a seção de Workflow continua com Concluir/Aprovar/Rejeitar e sem window.confirm", () => {
  const secao = secoes.slice(secoes.indexOf("export function WorkflowDemandaSection"), secoes.indexOf("export function ResponsaveisDemandaSection"));
  assert.match(secao, /rotuloDaAcao\(etapa\)/);
  assert.match(secao, /Rejeitar e devolver/);
  assert.doesNotMatch(secao, /window\.confirm/);
});
