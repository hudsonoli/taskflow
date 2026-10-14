// Fase Expediente 2 (frontend): 403 FORA_DO_EXPEDIENTE × 401, textos da tela, bloqueio vigente, store/polling ÚNICO e o que NÃO muda no hotfix de sessão expirada.
// `npm run test:expediente-acesso`
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  bloqueioDoEstado,
  bloqueioVigente,
  detalheDeForaDoExpediente,
  horaNoFuso,
  quandoNoFuso,
  textosForaDoExpediente,
  type BloqueioExpediente,
} from "./expediente-acesso.ts";
import { criarStoreEstadoExpediente } from "./expediente-estado-store.ts";
import { envolverFetch } from "./sessao-expirada.ts";
import type { EstadoExpediente } from "../types/regra-expediente.ts";

const SP = "America/Sao_Paulo";
const base = new URL("..", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, base), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

function estado(parcial: Partial<EstadoExpediente> = {}): EstadoExpediente {
  return {
    ativo: true,
    dentroExpediente: false,
    agora: "2026-10-05T12:10:00-03:00",
    toleranciaRetomadaMinutos: 30,
    horasUteisHoje: 8,
    sujeitoAoExpediente: true,
    bloqueioAtivo: true,
    acessoPermitido: false,
    trabalhoPermitido: false,
    proximoAcesso: "2026-10-05T12:30:00-03:00",
    proximoTrabalho: "2026-10-05T13:00:00-03:00",
    proximoTrabalhoFim: "2026-10-05T18:00:00-03:00",
    timezone: SP,
    ...parcial,
  };
}

// ── 403 FORA_DO_EXPEDIENTE × outros 403 ───────────────────────────────────────────────────────────────────────

test("reconhece o corpo do 403 FORA_DO_EXPEDIENTE e ignora qualquer outro 403", () => {
  const detalhe = detalheDeForaDoExpediente({
    detail: { code: "FORA_DO_EXPEDIENTE", message: "Fora do horário de expediente", proximoAcesso: "2026-10-05T12:30:00-03:00", proximoTrabalho: "2026-10-05T13:00:00-03:00", proximoTrabalhoFim: null, timezone: SP },
  });
  assert.ok(detalhe);
  assert.equal(detalhe.proximoAcesso, "2026-10-05T12:30:00-03:00");
  assert.equal(detalhe.proximoTrabalhoFim, null);
  // 403 comuns: permissão, troca de senha obrigatória, string simples, corpo estranho
  assert.equal(detalheDeForaDoExpediente({ detail: "Acesso negado" }), null);
  assert.equal(detalheDeForaDoExpediente({ detail: { code: "SENHA_TROCA_OBRIGATORIA", message: "x" } }), null);
  assert.equal(detalheDeForaDoExpediente({ detail: { code: "FORA_DE_EXPEDIENTE" } }), null); // o 409 legado tem outro código
  assert.equal(detalheDeForaDoExpediente(null), null);
  assert.equal(detalheDeForaDoExpediente("FORA_DO_EXPEDIENTE"), null);
});

async function respostaDe(status: number, corpo: unknown): Promise<Response> {
  return new Response(JSON.stringify(corpo), { status, headers: { "content-type": "application/json" } });
}

function wrapperComRegistro(status: number, corpo: unknown, url = "/api/backend/usuarios/me", pathname = "/e/boxcom/meu-dia") {
  const chamadas = { expirou: 0, recusas: [] as number[] };
  const original = (async () => respostaDe(status, corpo)) as typeof fetch;
  const envolvido = envolverFetch(original, {
    aoExpirar: () => {
      chamadas.expirou += 1;
    },
    aoRecusar: ({ status: s }) => {
      chamadas.recusas.push(s);
    },
    pathname: () => pathname,
    origem: () => "http://localhost:3000",
  });
  return { envolvido, chamadas, url };
}

test("401 → sessão expirada (login); 403 NUNCA expira a sessão — só chega a aoRecusar", async () => {
  const r401 = wrapperComRegistro(401, { detail: "Token inválido" });
  await r401.envolvido(r401.url);
  assert.deepEqual([r401.chamadas.expirou, r401.chamadas.recusas], [1, []]);

  const r403 = wrapperComRegistro(403, { detail: { code: "FORA_DO_EXPEDIENTE" } });
  await r403.envolvido(r403.url);
  assert.deepEqual([r403.chamadas.expirou, r403.chamadas.recusas], [0, [403]]);
});

test("403 comum, 409, 404, 422 e 500 não expiram a sessão e a resposta chega intacta", async () => {
  for (const status of [403, 404, 409, 422, 500]) {
    const r = wrapperComRegistro(status, { detail: "x" });
    const resposta = await r.envolvido(r.url);
    assert.equal(resposta.status, status);
    assert.equal(r.chamadas.expirou, 0, String(status));
    assert.deepEqual(await resposta.json(), { detail: "x" }); // o corpo continua legível (o clone foi só para quem observa)
  }
});

test("respostas ok e chamadas fora do proxy tenant/área autenticada não chamam aoRecusar", async () => {
  const ok = wrapperComRegistro(200, {});
  await ok.envolvido(ok.url);
  assert.deepEqual(ok.chamadas.recusas, []);
  const auth = wrapperComRegistro(403, {}, "/api/auth/login");
  await auth.envolvido(auth.url);
  assert.deepEqual(auth.chamadas.recusas, []);
  const gestao = wrapperComRegistro(403, {}, "/api/backend/x", "/gestao/empresas");
  await gestao.envolvido(gestao.url);
  assert.deepEqual(gestao.chamadas.recusas, []);
  const login = wrapperComRegistro(403, {}, "/api/backend/x", "/e/boxcom/login");
  await login.envolvido(login.url);
  assert.deepEqual(login.chamadas.recusas, []);
});

// ── textos da tela ───────────────────────────────────────────────────────────────────────────────────────────

test("a tela mostra o próximo acesso e o próximo período no fuso da EMPRESA, não do navegador", () => {
  const bloqueio = bloqueioDoEstado(estado())!;
  const hoje = new Date("2026-10-05T15:10:00Z"); // 12:10 em São Paulo
  const textos = textosForaDoExpediente(bloqueio, hoje);
  assert.equal(textos.titulo, "Fora do horário de expediente");
  assert.equal(textos.proximoAcesso, "Seu próximo acesso estará disponível às 12:30.");
  assert.equal(textos.proximoTrabalho, "Próximo período de trabalho: 13:00–18:00.");
  // mesmo instante, empresa em outro fuso: a hora exibida muda com o fuso da EMPRESA
  assert.equal(horaNoFuso("2026-10-05T15:30:00Z", "America/Manaus"), "11:30");
  assert.equal(horaNoFuso("2026-10-05T15:30:00Z", SP), "12:30");
});

test("quando o próximo acesso é em outro dia, a mensagem diz o dia", () => {
  const sexta = new Date("2026-10-09T22:00:00Z"); // sexta 19:00 em SP
  const bloqueio: BloqueioExpediente = {
    proximoAcesso: "2026-10-12T08:30:00-03:00",
    proximoTrabalho: "2026-10-12T09:00:00-03:00",
    proximoTrabalhoFim: "2026-10-12T12:00:00-03:00",
    timezone: SP,
  };
  const textos = textosForaDoExpediente(bloqueio, sexta);
  assert.match(textos.proximoAcesso!, /^Seu próximo acesso estará disponível na segunda-feira \(12\/10\) às 08:30\.$/);
  assert.match(textos.proximoTrabalho!, /^Próximo período de trabalho: segunda-feira \(12\/10\), 09:00–12:00\.$/);
  assert.equal(quandoNoFuso("2026-10-12T08:30:00-03:00", SP, sexta).startsWith("na segunda-feira"), true);
});

test("sem horários do servidor a tela ainda explica; nunca mostra 'Não autenticado'", () => {
  const vazio = textosForaDoExpediente({ proximoAcesso: null, proximoTrabalho: null, proximoTrabalhoFim: null, timezone: null });
  assert.equal(vazio.proximoAcesso, null);
  assert.equal(vazio.proximoTrabalho, null);
  const tela = semComentarios(ler("components/layout/ForaDoExpedienteView.tsx"));
  assert.equal(/Não autenticado/.test(tela), false);
  assert.match(tela, /Sair/);
  assert.match(tela, /role="status"/);
});

// ── bloqueio vigente: o mais recente vence ───────────────────────────────────────────────────────────────────

test("o poll mais novo derruba o bloqueio do 403 (acesso voltou sem novo login); um 403 mais novo vale já", () => {
  const doErro = { bloqueio: bloqueioDoEstado(estado())!, em: 1000 };
  assert.ok(bloqueioVigente(null, 0, doErro)); // sem estado ainda: vale o 403
  assert.ok(bloqueioVigente(estado({ acessoPermitido: false }), 500, doErro)); // 403 mais novo que o poll
  assert.equal(bloqueioVigente(estado({ acessoPermitido: true, trabalhoPermitido: false }), 2000, doErro), null); // 12:30 — acesso volta
  assert.equal(bloqueioDoEstado(estado({ acessoPermitido: true })), null);
});

test("12:30 libera o ACESSO mas não o TRABALHO; 13:00 libera o trabalho (decisão do servidor, a tela só lê)", () => {
  const as1230 = estado({ acessoPermitido: true, trabalhoPermitido: false, dentroExpediente: false });
  assert.equal(bloqueioDoEstado(as1230), null);
  assert.equal(as1230.trabalhoPermitido, false);
  const as1300 = estado({ acessoPermitido: true, trabalhoPermitido: true, dentroExpediente: true });
  assert.equal(bloqueioDoEstado(as1300), null);
  assert.equal(as1300.trabalhoPermitido, true);
});

// ── store: polling ÚNICO ─────────────────────────────────────────────────────────────────────────────────────

function storeDeTeste(respostas: EstadoExpediente[]) {
  let relogio = 1_000_000;
  const timers: Array<{ id: number; acao: () => void; ms: number }> = [];
  let proximoId = 1;
  let buscas = 0;
  const store = criarStoreEstadoExpediente({
    buscar: async () => respostas[Math.min(buscas++, respostas.length - 1)],
    agora: () => relogio,
    setIntervalo: (acao, ms) => {
      const id = proximoId++;
      timers.push({ id, acao, ms });
      return id;
    },
    limparIntervalo: (id) => {
      const i = timers.findIndex((t) => t.id === id);
      if (i >= 0) timers.splice(i, 1);
    },
  });
  return {
    store,
    timers,
    buscas: () => buscas,
    avancar: (ms: number) => {
      relogio += ms;
    },
  };
}

test("vários assinantes compartilham UM temporizador de ~30 s e UMA busca", async () => {
  const t = storeDeTeste([estado({ acessoPermitido: true })]);
  const desinscrever = [t.store.subscribe(() => undefined), t.store.subscribe(() => undefined), t.store.subscribe(() => undefined)];
  await t.store.atualizar();
  assert.equal(t.timers.length, 1);
  assert.equal(t.timers[0].ms, 30_000);
  assert.equal(t.buscas(), 1); // as três assinaturas simultâneas não geraram três buscas
  desinscrever[0]();
  desinscrever[1]();
  assert.equal(t.timers.length, 1); // ainda há um assinante
  desinscrever[2]();
  assert.equal(t.timers.length, 0); // sem assinantes não há polling
});

test("o poll converge sozinho: bloqueia às 12:00 e libera às 12:30, sem ação da pessoa", async () => {
  const t = storeDeTeste([estado({ acessoPermitido: true }), estado({ acessoPermitido: false }), estado({ acessoPermitido: true, trabalhoPermitido: false })]);
  t.store.subscribe(() => undefined);
  await t.store.atualizar();
  assert.equal(t.store.getSnapshot().bloqueio, null);
  t.avancar(30_000);
  t.timers[0].acao(); // tick de 30 s
  await t.store.atualizar(true);
  assert.ok(t.store.getSnapshot().bloqueio);
  t.avancar(30_000);
  await t.store.atualizar(true);
  assert.equal(t.store.getSnapshot().bloqueio, null);
});

test("um 403 mostra o bloqueio imediatamente e o servidor confirma em seguida", async () => {
  const t = storeDeTeste([estado({ acessoPermitido: false })]);
  t.store.subscribe(() => undefined);
  t.avancar(5_000);
  t.store.registrarBloqueio({ proximoAcesso: "2026-10-05T12:30:00-03:00", proximoTrabalho: null, proximoTrabalhoFim: null, timezone: SP });
  assert.ok(t.store.getSnapshot().bloqueio); // antes mesmo da resposta do poll
  await t.store.atualizar(true);
  assert.ok(t.store.getSnapshot().bloqueio);
});

test("uma rajada de 403 simultâneos gera UMA busca de confirmação, não uma por resposta", async () => {
  const t = storeDeTeste([estado({ acessoPermitido: false })]);
  t.store.subscribe(() => undefined);
  await t.store.atualizar(true);
  const antes = t.buscas();
  t.avancar(500);
  for (let i = 0; i < 12; i++) t.store.registrarBloqueio({ proximoAcesso: null, proximoTrabalho: null, proximoTrabalhoFim: null, timezone: SP });
  await t.store.atualizar();
  assert.equal(t.buscas() - antes, 0); // dentro do intervalo mínimo: nenhuma busca extra
  assert.ok(t.store.getSnapshot().bloqueio);
  t.avancar(5_000);
  t.store.registrarBloqueio({ proximoAcesso: null, proximoTrabalho: null, proximoTrabalhoFim: null, timezone: SP });
  t.store.registrarBloqueio({ proximoAcesso: null, proximoTrabalho: null, proximoTrabalhoFim: null, timezone: SP });
  await t.store.atualizar();
  assert.equal(t.buscas() - antes, 1); // as duas simultâneas compartilham a mesma busca em voo
});

test("falha de rede no poll mantém o último estado e nunca inventa bloqueio", async () => {
  let falhar = false;
  const store = criarStoreEstadoExpediente({
    buscar: async () => {
      if (falhar) throw new Error("rede");
      return estado({ acessoPermitido: true });
    },
    setIntervalo: () => 1,
    limparIntervalo: () => undefined,
    agora: () => Date.now(),
  });
  store.subscribe(() => undefined);
  await store.atualizar(true);
  falhar = true;
  await store.atualizar(true);
  assert.equal(store.getSnapshot().bloqueio, null);
  assert.equal(store.getSnapshot().estado?.acessoPermitido, true);
});

test("logout/401 limpa o estado e o bloqueio (nada do usuário anterior sobra)", async () => {
  const t = storeDeTeste([estado({ acessoPermitido: false })]);
  t.store.subscribe(() => undefined);
  await t.store.atualizar(true);
  assert.ok(t.store.getSnapshot().bloqueio);
  t.store.limpar();
  assert.equal(t.store.getSnapshot().bloqueio, null);
  assert.equal(t.store.getSnapshot().estado, null);
});

// ── estrutura ────────────────────────────────────────────────────────────────────────────────────────────────

test("só existe UM setInterval de expediente (no store); o hook e as telas não criam polling próprio", () => {
  const hook = semComentarios(ler("lib/estadoExpediente.ts"));
  assert.equal(/setInterval|setTimeout/.test(hook), false);
  const store = semComentarios(ler("lib/expediente-estado-store.ts"));
  assert.equal((store.match(/setIntervalo\(/g) ?? []).length, 1);
  for (const arquivo of ["components/layout/ExpedienteGuard.tsx", "components/layout/ForaDoExpedienteView.tsx", "components/demandas/DemandasKanban.tsx", "components/meu-departamento/MeuDepartamentoView.tsx"]) {
    assert.equal(/setInterval/.test(semComentarios(ler(arquivo))), false, arquivo);
  }
});

test("o guarda vive só na área tenant (nunca em /gestao) e o 403 vira tela, não login", () => {
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /<ExpedienteGuard/);
  const gestaoIdx = shell.indexOf("<GestaoTopBar />");
  const guardIdx = shell.indexOf("<ExpedienteGuard");
  assert.ok(gestaoIdx > 0 && guardIdx > gestaoIdx);
  const contexto = semComentarios(ler("lib/AppDataContext.tsx"));
  assert.match(contexto, /aoRecusar/);
  assert.match(contexto, /registrarBloqueio\(bloqueioDoDetalhe\(detalhe\)\)/);
  // o tratamento do 403 de expediente nunca navega para o login
  const trecho = contexto.slice(contexto.indexOf("aoRecusar"), contexto.indexOf("aoRecusar") + 600);
  assert.equal(/router|hrefLogin|setHrefLoginExpirado/.test(trecho), false);
});

test("o Kanban usa a decisão do servidor para a pessoa (trabalhoPermitido)", () => {
  const kanban = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(kanban, /estado\.trabalhoPermitido \?\? estado\.dentroExpediente/);
});

test("a tela de configuração: bloqueio liga, pausa continua 'Em breve' e o logout tem horário próprio", () => {
  const view = semComentarios(ler("components/regra-expediente/RegraExpedienteView.tsx"));
  assert.match(view, /checked=\{regra\.bloquearForaExpediente\}/);
  assert.match(view, /checked=\{regra\.logoutAutomaticoAtivo\}/);
  assert.match(view, /type="time"/);
  // pausa: travada
  const pausa = view.slice(view.indexOf("Pausar atividades ao final dos períodos") - 200, view.indexOf("Pausar atividades ao final dos períodos") + 300);
  assert.match(pausa, /checked=\{false\}/);
  assert.match(pausa, /disabled/);
  assert.match(view, /Em breve/);
  assert.match(view, /logoutHorario: regra\.logoutHorario \?\? null/);
  assert.match(view, /independentes/);
});
