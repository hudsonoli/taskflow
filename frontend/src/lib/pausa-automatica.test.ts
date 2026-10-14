// Fase Expediente 3 (frontend): aviso "Tarefas pausadas automaticamente." — evento novo/recente/quantidade, dedup por eventoId, localStorage indisponível e estrutura.
// `npm run test:pausa-automatica`
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { beforeEach, test } from "node:test";
import {
  JANELA_RECENTE_MS,
  MENSAGEM_PAUSA_AUTOMATICA,
  eventoParaAvisar,
  gravarEventoApresentado,
  lerEventoApresentado,
  limparMemoriaDaSessao,
  pausaRecente,
} from "./pausa-automatica.ts";

const base = new URL("..", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, base), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

const CORTE = "2026-10-05T12:00:00-03:00";
const ultima = (extra: Partial<{ eventoId: string; em: string; quantidade: number }> = {}) => ({ eventoId: "ev-1", em: CORTE, quantidade: 2, ...extra });
const depoisDoCorte = (segundos: number) => new Date(Date.parse(CORTE) + segundos * 1000).toISOString();

beforeEach(() => limparMemoriaDaSessao());

test("o texto do aviso é exatamente 'Tarefas pausadas automaticamente.'", () => {
  assert.equal(MENSAGEM_PAUSA_AUTOMATICA, "Tarefas pausadas automaticamente.");
});

test("evento novo e recente avisa UMA vez (comparado com o agora do SERVIDOR)", () => {
  assert.equal(eventoParaAvisar(ultima(), depoisDoCorte(42), null), "ev-1");
  // o mesmo evento no próximo poll: já apresentado → nada
  assert.equal(eventoParaAvisar(ultima(), depoisDoCorte(72), "ev-1"), null);
  // um evento DIFERENTE (outro corte) volta a avisar
  assert.equal(eventoParaAvisar(ultima({ eventoId: "ev-2", em: "2026-10-05T18:00:00-03:00" }), "2026-10-05T18:00:30-03:00", "ev-1"), "ev-2");
});

test("evento antigo não avisa (login horas depois)", () => {
  assert.equal(pausaRecente(ultima(), depoisDoCorte(JANELA_RECENTE_MS / 1000)), true); // exatamente no limite
  assert.equal(pausaRecente(ultima(), depoisDoCorte(JANELA_RECENTE_MS / 1000 + 1)), false);
  assert.equal(eventoParaAvisar(ultima(), "2026-10-05T15:30:00-03:00", null), null);
});

test("quantidade 0/ausente, evento ausente ou datas inválidas não avisam", () => {
  assert.equal(eventoParaAvisar(ultima({ quantidade: 0 }), depoisDoCorte(10), null), null);
  assert.equal(eventoParaAvisar(null, depoisDoCorte(10), null), null);
  assert.equal(eventoParaAvisar(undefined, depoisDoCorte(10), null), null);
  assert.equal(eventoParaAvisar(ultima({ eventoId: "" }), depoisDoCorte(10), null), null);
  assert.equal(eventoParaAvisar(ultima({ em: "ontem" }), depoisDoCorte(10), null), null);
  assert.equal(eventoParaAvisar(ultima(), null, null), null);
});

test("relógios levemente dessincronizados (agora antes do corte) ainda contam como recente", () => {
  assert.equal(pausaRecente(ultima(), depoisDoCorte(-3)), true);
});

test("o evento apresentado é lembrado por usuário (localStorage) e não vaza para outra pessoa", () => {
  const dados = new Map<string, string>();
  const storage = { getItem: (k: string) => dados.get(k) ?? null, setItem: (k: string, v: string) => void dados.set(k, v) };
  gravarEventoApresentado("u1", "ev-1", storage);
  assert.equal(lerEventoApresentado("u1", storage), "ev-1");
  assert.equal(lerEventoApresentado("u2", storage), null);
  assert.equal(dados.size, 1);
});

test("localStorage indisponível (lança) cai na memória da sessão e continua deduplicando", () => {
  const quebrado = {
    getItem: () => {
      throw new Error("bloqueado");
    },
    setItem: () => {
      throw new Error("bloqueado");
    },
  };
  assert.doesNotThrow(() => gravarEventoApresentado("u1", "ev-9", quebrado));
  assert.equal(lerEventoApresentado("u1", quebrado), "ev-9");
  assert.equal(eventoParaAvisar(ultima({ eventoId: "ev-9" }), depoisDoCorte(5), lerEventoApresentado("u1", quebrado)), null);
  // sem armazenamento nenhum (SSR/privado)
  assert.equal(lerEventoApresentado("u1", null), "ev-9");
  assert.doesNotThrow(() => gravarEventoApresentado("u3", "ev-3", null));
  assert.equal(lerEventoApresentado("u3", null), "ev-3");
});

test("a segurança não depende do localStorage: sem ele, o servidor continua sendo a fonte (poll devolve o mesmo evento; a memória evita repetir)", () => {
  gravarEventoApresentado("u1", "ev-1", null);
  assert.equal(eventoParaAvisar(ultima(), depoisDoCorte(5), lerEventoApresentado("u1", null)), null);
});

// ── estrutura ────────────────────────────────────────────────────────────────────────────────────────────────

test("o aviso usa o AvisoFlutuante existente e o store único (sem polling próprio, sem biblioteca nova)", () => {
  const aviso = semComentarios(ler("components/layout/PausaAutomaticaAviso.tsx"));
  assert.match(aviso, /AvisoFlutuante/);
  assert.match(aviso, /useSnapshotExpediente/);
  assert.equal(/setInterval|setTimeout|fetch\(/.test(aviso), false);
  assert.match(aviso, /MENSAGEM_PAUSA_AUTOMATICA/);
  const guarda = semComentarios(ler("components/layout/ExpedienteGuard.tsx"));
  assert.match(guarda, /<PausaAutomaticaAviso \/>/);
  // o aviso não aparece na tela de bloqueio: ele só é montado junto das telas (o ramo do bloqueio retorna antes)
  assert.ok(guarda.indexOf("ForaDoExpedienteView") < guarda.indexOf("<PausaAutomaticaAviso"));
});

test("a configuração libera a pausa, deixa claro que não faz logout nem retoma, e mantém o logout separado", () => {
  const view = semComentarios(ler("components/regra-expediente/RegraExpedienteView.tsx"));
  assert.match(view, /checked=\{regra\.pausarNoFimPeriodo\}/);
  assert.match(view, /pausarNoFimPeriodo: regra\.pausarNoFimPeriodo/);
  assert.match(view, /não são retomadas automaticamente/i);
  assert.match(view, /Não faz logout/);
  assert.match(view, /checked=\{regra\.logoutAutomaticoAtivo\}/);
  assert.equal(/Em breve/.test(view), false);
});
