// Fase 5 — contexto do usuário logado após troca de departamento/perfil. `npm run test:gestor-departamento` (node --test).
// Helpers puros exercitados de verdade; AppDataContext/escopo-operacional (alias `@/`) são lidos como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  REVALIDACAO_MIN_MS,
  REVALIDACAO_PERIODO_MS,
  contextoOperacionalMudou,
  escolherDepartamentoHead,
  podeRevalidar,
  usuarioMudou,
  type UsuarioComparavel,
} from "./sessaoUsuario.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const gestorTi: UsuarioComparavel = {
  id: "u1",
  perfil: "gestor",
  departamentoId: "dep-ti",
  liderDepartamento: true,
  ativo: true,
  updatedAt: "2026-10-01T10:00:00Z",
  permissoes: [],
};

test("trocar TI → Criação é detectado; o perfil Gestor NÃO muda (autoridade independente do departamento)", () => {
  const depois = { ...gestorTi, departamentoId: "dep-criacao", updatedAt: "2026-10-02T10:00:00Z" };
  assert.equal(usuarioMudou(gestorTi, depois), true);
  assert.equal(contextoOperacionalMudou(gestorTi, depois), true);
  assert.equal(depois.perfil, "gestor");
});

test("sem mudança relevante não há atualização de estado (evita re-render e flicker)", () => {
  assert.equal(usuarioMudou(gestorTi, { ...gestorTi }), false);
  assert.equal(usuarioMudou(gestorTi, { ...gestorTi, permissoes: [] }), false);
  assert.equal(contextoOperacionalMudou(gestorTi, { ...gestorTi }), false);
});

test("perfil, líder, ativo, updatedAt e permissões individuais disparam atualização", () => {
  for (const mudanca of [{ perfil: "operador" }, { liderDepartamento: false }, { ativo: false }, { updatedAt: "2026-10-03T00:00:00Z" }, { permissoes: ["clientes:criar"] }]) {
    assert.equal(usuarioMudou(gestorTi, { ...gestorTi, ...mudanca }), true, JSON.stringify(mudanca));
  }
  // permissões em outra ordem = igual
  const a = { ...gestorTi, permissoes: ["a", "b"] };
  assert.equal(usuarioMudou(a, { ...a, permissoes: ["b", "a"] }), false);
  // só dado cadastral (updatedAt) muda o estado, mas NÃO descarta os diretórios em cache
  const cadastral = { ...gestorTi, updatedAt: "2026-10-03T00:00:00Z" };
  assert.equal(usuarioMudou(gestorTi, cadastral), true);
  assert.equal(contextoOperacionalMudou(gestorTi, cadastral), false);
});

test("sem estado anterior, ou outra pessoa na sessão, sempre conta como mudança", () => {
  assert.equal(usuarioMudou(undefined, gestorTi), true);
  assert.equal(usuarioMudou(gestorTi, { ...gestorTi, id: "u2" }), true);
  assert.equal(contextoOperacionalMudou(undefined, gestorTi), true);
});

test("revalidação: intervalo mínimo entre tentativas (foco/visibilidade chegam em rajada)", () => {
  assert.equal(podeRevalidar(0, REVALIDACAO_MIN_MS), true);
  assert.equal(podeRevalidar(1_000, 1_000 + REVALIDACAO_MIN_MS - 1), false);
  assert.equal(podeRevalidar(1_000, 1_000 + REVALIDACAO_MIN_MS), true);
  assert.ok(REVALIDACAO_PERIODO_MS > REVALIDACAO_MIN_MS);
});

test("Meu Departamento: com mais de um departamento como Head, vale o do contexto ATUAL; sem ele, o primeiro", () => {
  const ti = { id: "dep-ti" };
  const criacao = { id: "dep-criacao" };
  const atual = (id: string) => (d: { id: string }) => d.id === id;
  // dono formal de TI (antigo) + líder em Criação (atual): a ordem da lista não manda
  assert.equal(escolherDepartamentoHead([ti, criacao], atual("dep-criacao")), criacao);
  assert.equal(escolherDepartamentoHead([criacao, ti], atual("dep-criacao")), criacao);
  assert.equal(escolherDepartamentoHead([ti, criacao], atual("dep-inexistente")), ti);
  assert.equal(escolherDepartamentoHead([], atual("dep-ti")), undefined);
});

test("AppDataProvider revalida o usuário ao voltar à aba/foco/periodicamente, sem window.location.reload", () => {
  const ctx = ler("lib/AppDataContext.tsx");
  const codigo = semComentarios(ctx);
  assert.match(codigo, /fetchUsuarioAtualCompleto\(\)/);
  assert.match(codigo, /document\.addEventListener\("visibilitychange"/);
  assert.match(codigo, /window\.addEventListener\("focus"/);
  assert.match(codigo, /setInterval\(.*REVALIDACAO_PERIODO_MS\)/);
  assert.match(codigo, /podeRevalidar\(ultimaRevalidacaoRef\.current, agora\)/);
  assert.match(codigo, /if \(!usuarioMudou\(anterior, completo\)\) return;/);
  assert.match(codigo, /contextoOperacionalMudou\(anterior, completo\)/);
  for (const invalidar of ["invalidarDiretorioDepartamentos()", "invalidarDiretorioUsuarios()", "invalidarDiretorioEquipes()"]) {
    assert.ok(codigo.includes(invalidar), invalidar);
  }
  assert.match(codigo, /setUsuarioAtual\(completo\)/);
  assert.doesNotMatch(codigo, /location\.reload/);
  // só com sessão ativa e sem troca de senha pendente
  assert.match(codigo, /habilitarRevalidacao = autenticado && !mustChangePassword && usuarioAtual !== undefined/);
  // limpeza dos listeners
  assert.match(codigo, /removeEventListener\("visibilitychange"/);
  assert.match(codigo, /clearInterval/);
});

test("resolverHeadDepartamento usa a escolha determinística do contexto atual (não a ordem da lista)", () => {
  const escopo = semComentarios(ler("lib/escopo-operacional.ts"));
  assert.match(escopo, /escolherDepartamentoHead\(candidatos, \(departamento\) => correspondeDepartamento\(usuario\.departamentoId, departamento\)\)/);
  assert.match(escopo, /departamento\.responsavelUsuarioId === usuario\.id/);
});

test("a autoridade do Gestor não depende do departamento na interface (acesso por perfil, não por departamento)", () => {
  const autoridade = semComentarios(ler("lib/autoridadeUsuarios.ts"));
  assert.doesNotMatch(autoridade, /departamentoId|departamento\.nome/i);
});
