// @menções: lógica pura do autocomplete, da seleção e do destaque. `npm run test:mencoes`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  detectarMencaoAtiva,
  idsDasMencoes,
  inserirMencao,
  reconciliarSelecionadas,
  rotuloDaMencao,
  segmentarComMencoes,
} from "./mencoes.ts";
import { abaDaNotificacao, TIPO_USUARIOS_MENCIONADOS } from "./notificacoes.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (codigo: string) => codigo.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

test("'@' abre o autocomplete no início do texto e depois de espaço/quebra; a consulta é o que vem depois", () => {
  assert.deepEqual(detectarMencaoAtiva("@", 1), { inicio: 0, consulta: "" });
  assert.deepEqual(detectarMencaoAtiva("@Raq", 4), { inicio: 0, consulta: "Raq" });
  assert.deepEqual(detectarMencaoAtiva("oi @Raq", 7), { inicio: 3, consulta: "Raq" });
  assert.deepEqual(detectarMencaoAtiva("oi\n@Raq", 7), { inicio: 3, consulta: "Raq" });
  assert.deepEqual(detectarMencaoAtiva("oi @Raquel Ol", 13), { inicio: 3, consulta: "Raquel Ol" }); // nomes têm espaço
});

test("'@' no meio de palavra (e-mail), '@ ' solto, consulta longa ou com quebra NÃO abre o autocomplete", () => {
  assert.equal(detectarMencaoAtiva("fulano@empresa.com", 18), null);
  assert.equal(detectarMencaoAtiva("oi @ ", 5), null);
  assert.equal(detectarMencaoAtiva("oi @a b c d", 11), null); // espaços demais
  assert.equal(detectarMencaoAtiva(`@${"a".repeat(40)}`, 41), null);
  assert.equal(detectarMencaoAtiva("sem arroba", 5), null);
  assert.equal(detectarMencaoAtiva("@Raquel\nfim", 11), null); // o cursor já passou da quebra
});

test("o cursor manda: '@' DEPOIS do cursor não conta", () => {
  assert.equal(detectarMencaoAtiva("oi @Raq", 2), null);
});

test("selecionar substitui '@consulta' pelo rótulo + espaço e leva o cursor para depois dele", () => {
  const ativa = detectarMencaoAtiva("oi @Raq fim", 7)!;
  const r = inserirMencao("oi @Raq fim", ativa, 7, { nome: "Raquel Oliveira" });
  assert.equal(r.texto, "oi @Raquel Oliveira fim");
  assert.equal(r.cursor, "oi @Raquel Oliveira ".length);
  assert.equal(inserirMencao("@", { inicio: 0, consulta: "" }, 1, { nome: "Pedro" }).texto, "@Pedro ");
});

test("apagar o rótulo do texto desfaz a menção; pessoa repetida vale uma vez", () => {
  const raquel = { id: "r", nome: "Raquel Oliveira" };
  const pedro = { id: "p", nome: "Pedro Silva" };
  assert.deepEqual(reconciliarSelecionadas("@Raquel Oliveira e @pedro silva", [raquel, pedro, raquel]), [raquel, pedro]); // case-insensitive
  assert.deepEqual(reconciliarSelecionadas("só @Raquel", [raquel]), []); // o nome completo não está mais lá
  assert.deepEqual(reconciliarSelecionadas("nada", [raquel, pedro]), []);
  assert.deepEqual(idsDasMencoes([raquel, pedro, raquel]), ["r", "p"]);
});

test("destaque: só as menções guardadas pelo servidor, respeitando fronteira; '@Nome' digitado à mão e e-mail ficam texto", () => {
  const mencoes = [{ usuarioId: "r", nome: "Raquel Oliveira" }, { usuarioId: "p", nome: "Pedro" }];
  assert.deepEqual(segmentarComMencoes("@Raquel Oliveira revisar com @Pedro.", mencoes), [
    { tipo: "mencao", valor: "@Raquel Oliveira" },
    { tipo: "texto", valor: " revisar com " },
    { tipo: "mencao", valor: "@Pedro" },
    { tipo: "texto", valor: "." },
  ]);
  assert.deepEqual(segmentarComMencoes("@Joana oi", mencoes), [{ tipo: "texto", valor: "@Joana oi" }]); // não está entre as menções
  assert.deepEqual(segmentarComMencoes("@Pedrosa não é o Pedro", mencoes), [{ tipo: "texto", valor: "@Pedrosa não é o Pedro" }]);
  assert.deepEqual(segmentarComMencoes("mail x@Pedro", mencoes), [{ tipo: "texto", valor: "mail x@Pedro" }]);
  assert.deepEqual(segmentarComMencoes("sem nada", []), [{ tipo: "texto", valor: "sem nada" }]);
  assert.deepEqual(segmentarComMencoes("", mencoes), []);
  assert.equal(rotuloDaMencao("Ana"), "@Ana");
});

test("nomes com caracteres especiais de regex não quebram o destaque", () => {
  assert.deepEqual(segmentarComMencoes("ver com @Ana (Dir.) hoje", [{ usuarioId: "a", nome: "Ana (Dir.)" }]), [
    { tipo: "texto", valor: "ver com " },
    { tipo: "mencao", valor: "@Ana (Dir.)" },
    { tipo: "texto", valor: " hoje" },
  ]);
});

test("a notificação de menção abre o drawer na aba Atividade (onde está o comentário)", () => {
  assert.equal(TIPO_USUARIOS_MENCIONADOS, "demanda.usuarios_mencionados");
  assert.equal(abaDaNotificacao(TIPO_USUARIOS_MENCIONADOS), "atividade");
  assert.equal(abaDaNotificacao("demanda.status_alterado"), "dados");
  assert.equal(abaDaNotificacao("demanda.workflow_etapa_atualizada"), "workflow");
});

// ── fiação (source-scan) ────────────────────────────────────────────────────────────────────────────────────────────────

test("o comentário envia só os ids reconciliados com o texto e usa o endpoint de elegíveis do servidor", () => {
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /\/demandas\/\$\{encodeURIComponent\(demandaId\)\}\/mencionaveis\?/);
  assert.match(api, /JSON\.stringify\(\{ texto, mencoesUsuarioIds \}\)/);
  const secao = semComentarios(ler("components/demandas/AtividadeDemandaSection.tsx"));
  assert.match(secao, /<MencaoTextarea/);
  assert.match(secao, /idsDasMencoes\(reconciliarSelecionadas\(/);
  assert.match(secao, /segmentarComMencoes\(/);
});

test("o autocomplete tem teclado (↑ ↓ Enter Tab Esc), aria de combobox/listbox, debounce e reaproveita a superfície de menu (Glass/escuro)", () => {
  const c = semComentarios(ler("components/demandas/MencaoTextarea.tsx"));
  for (const tecla of ["ArrowDown", "ArrowUp", "Enter", "Tab", "Escape"]) assert.match(c, new RegExp(`"${tecla}"`), tecla);
  assert.match(c, /role="combobox"/);
  assert.match(c, /role="listbox"/);
  assert.match(c, /role="option"/);
  assert.match(c, /aria-activedescendant/);
  assert.match(c, /aria-expanded/);
  assert.match(c, /setTimeout\(/); // debounce
  assert.match(c, /data-superficie="menu"/); // o mesmo hook de superfície do Combobox: Padrão/Glass, claro/escuro
  assert.doesNotMatch(c, /dangerouslySetInnerHTML/);
});
