// Funções puras da Central de Notificações e do Perfil: badge, telefone, validação da foto, URL do avatar, iniciais.
// `npm run test:perfil` (node --test, sem dependências).
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  FOTO_MAX_BYTES,
  formatarBadge,
  formatarTelefone,
  iniciais,
  mascararTelefoneDigitando,
  srcDoAvatar,
  validarFotoNoNavegador,
} from "./notificacoes.ts";

test("badge: 0 esconde, 1..99 mostra o número, >99 vira 99+", () => {
  assert.equal(formatarBadge(0), null);
  assert.equal(formatarBadge(-3), null);
  assert.equal(formatarBadge(Number.NaN), null);
  assert.equal(formatarBadge(1), "1");
  assert.equal(formatarBadge(99), "99");
  assert.equal(formatarBadge(100), "99+");
  assert.equal(formatarBadge(5000), "99+");
});

test("telefone: exibição BR a partir dos dígitos guardados", () => {
  assert.equal(formatarTelefone("11912345678"), "(11) 91234-5678");
  assert.equal(formatarTelefone("1133334444"), "(11) 3333-4444");
  assert.equal(formatarTelefone("+5511912345678"), "+55 (11) 91234-5678");
  assert.equal(formatarTelefone("12345"), "12345"); // fora do padrão: como veio
  assert.equal(formatarTelefone(null), "");
  assert.equal(formatarTelefone(""), "");
});

test("telefone: máscara progressiva ao digitar (não impõe formato ao banco)", () => {
  assert.equal(mascararTelefoneDigitando("1"), "1");
  assert.equal(mascararTelefoneDigitando("119"), "(11) 9");
  assert.equal(mascararTelefoneDigitando("1191234"), "(11) 9123-4");
  assert.equal(mascararTelefoneDigitando("11912345678"), "(11) 91234-5678");
  assert.equal(mascararTelefoneDigitando("119123456789999"), "(11) 91234-5678"); // corta no máximo
  assert.equal(mascararTelefoneDigitando("(11) 3333-4444"), "(11) 3333-4444");
  assert.equal(mascararTelefoneDigitando("+55 11 91234-5678"), "+5511912345678");
  assert.equal(mascararTelefoneDigitando("abc"), "");
});

test("foto: aceita PNG/JPG até 5 MB; recusa SVG, HTML, PDF, executável, vazio e grande", () => {
  const ok = (name: string, type: string, size = 1000) => validarFotoNoNavegador({ name, type, size });
  assert.equal(ok("a.png", "image/png"), null);
  assert.equal(ok("a.JPG", "image/jpeg"), null);
  assert.equal(ok("a.jpeg", "image/jpeg"), null);
  assert.equal(ok("a.png", "image/png", FOTO_MAX_BYTES), null);
  for (const [nome, tipo] of [["a.svg", "image/svg+xml"], ["a.html", "text/html"], ["a.pdf", "application/pdf"], ["a.exe", "application/octet-stream"], ["a.gif", "image/gif"], ["a.webp", "image/webp"], ["semextensao", "image/png"]]) {
    assert.ok(ok(nome, tipo), `${nome} deveria ser recusado`);
  }
  assert.ok(ok("a.png", "image/svg+xml"), "tipo declarado incoerente");
  assert.ok(ok("a.png", "image/png", 0));
  assert.ok(ok("a.png", "image/png", FOTO_MAX_BYTES + 1));
});

test("avatar: foto própria passa pelo proxy autenticado; URL externa e data URL ficam como estão", () => {
  assert.equal(srcDoAvatar("/usuarios/abc/avatar?v=123"), "/api/backend/usuarios/abc/avatar?v=123");
  assert.equal(srcDoAvatar("https://lh3.googleusercontent.com/a/x"), "https://lh3.googleusercontent.com/a/x");
  assert.equal(srcDoAvatar("blob:http://localhost/xyz"), "blob:http://localhost/xyz");
  assert.equal(srcDoAvatar(null), null);
  assert.equal(srcDoAvatar(undefined), null);
  assert.equal(srcDoAvatar(""), null);
});

test("iniciais do fallback", () => {
  assert.equal(iniciais("Hudson de Oliveira"), "HO");
  assert.equal(iniciais("Ana"), "A");
  assert.equal(iniciais("  maria  clara  "), "MC");
  assert.equal(iniciais(""), "");
});

// ── Fase 8C: notificação da próxima etapa de Workflow ─────────────────────────────────────────────────────────

import { readFileSync } from "node:fs";
import { TIPO_ETAPA_DE_WORKFLOW_ATUALIZADA, abaDaNotificacao, contextoDaNotificacao } from "./notificacoes.ts";

test("8C: clicar na notificação da etapa abre a aba Workflow; as demais abrem Dados", () => {
  assert.equal(TIPO_ETAPA_DE_WORKFLOW_ATUALIZADA, "demanda.workflow_etapa_atualizada");
  assert.equal(abaDaNotificacao("demanda.workflow_etapa_atualizada"), "workflow");
  assert.equal(abaDaNotificacao("demanda.status_alterado"), "dados");
  assert.equal(abaDaNotificacao("demanda.responsavel_adicionado"), "dados");
});

test("8C: contexto usa o identificador emitido da demanda (fallback: referência) e nunca monta #número", () => {
  assert.equal(contextoDaNotificacao({ demandaIdentificador: "BOX-2026-00846", demandaReferencia: "T26000012", demandaNome: "Post" }), "BOX-2026-00846 · Post");
  assert.equal(contextoDaNotificacao({ demandaIdentificador: "#845", demandaReferencia: "T26000012", demandaNome: "Post" }), "#845 · Post");
  assert.equal(contextoDaNotificacao({ demandaReferencia: "T26000012", demandaNome: "Post" }), "T26000012 · Post");
  assert.equal(contextoDaNotificacao({ demandaIdentificador: null, demandaReferencia: null, demandaNome: "Post" }), "Post");
});

test("8C: a central e o sino usam os mesmos helpers (sem segunda UI) e a aba vem do tipo", () => {
  const ler = (c: string) => readFileSync(new URL(`../${c}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
  for (const arquivo of ["components/notificacoes/NotificacoesView.tsx", "components/layout/NotificationBell.tsx"]) {
    const fonte = ler(arquivo);
    assert.match(fonte, /abaDaNotificacao\(notificacao\.tipo\)/, arquivo);
    assert.match(fonte, /contextoDaNotificacao\(notificacao\)/, arquivo);
    assert.doesNotMatch(fonte, /`#\$\{/, arquivo);
  }
});
