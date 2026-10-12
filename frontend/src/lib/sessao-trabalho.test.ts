// Fase 11B.2A — o 409 de domínio ao abrir sessão (SESSAO_ATIVA_EXISTENTE / DEMANDA_NAO_EXECUTAVEL) chega como `detail: { code, message }`. `npm run test:sessao-trabalho`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");

test("abrirSessaoTrabalho mostra a mensagem do 409 estruturado (não '[object Object]') e preserva erros em texto", () => {
  const api = ler("lib/api.ts");
  const funcao = api.slice(api.indexOf("export async function abrirSessaoTrabalho"), api.indexOf("export interface ListEventosParams"));
  assert.match(funcao, /typeof bruto === "string" \? bruto : bruto\?\.message/);
  assert.doesNotMatch(funcao, /new Error\(detail\?\.detail \?\?/);
  assert.match(funcao, /"Falha ao abrir sessão de trabalho"/);
});

test("a tela de Tráfego exibe o erro de abertura sem esconder o conflito", () => {
  const tela = ler("components/trafego/TrafegoIniciarSessao.tsx");
  assert.match(tela, /else setErro\(resultado\.mensagem\)/); // erros que não são o 409 de sessão ativa seguem exibindo a mensagem do servidor
  assert.match(tela, /\{erro && <p/);
});
