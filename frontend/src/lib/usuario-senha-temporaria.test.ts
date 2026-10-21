// Hotfix de onboarding — usuário criado na empresa recebe SENHA TEMPORÁRIA exibida uma única vez (sem convite/e-mail). `npm run test:usuario-senha` (node --test, sem dependências).
// As telas (alias `@/`) são lidas como texto para provar o que os tipos não mostram: a senha só vive no estado da tela, tem aviso de exibição única + Copiar, nada é gravado no
// navegador, a listagem só oferece "Senha temporária" a quem ainda não concluiu o primeiro acesso e nenhum GET devolve a senha.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { AVISO_SENHA_UNICA } from "./plataforma.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("o modal de entrega usa o aviso de exibição única + Copiar e nunca grava a senha no navegador", () => {
  const modal = semComentarios(ler("components/usuarios/UsuarioSenhaTemporariaModal.tsx"));
  assert.match(modal, /<SenhaTemporariaAviso /);
  assert.match(AVISO_SENHA_UNICA, /exibida somente agora/);
  assert.doesNotMatch(modal, /localStorage|sessionStorage|indexedDB|document\.cookie|console\.|router\.|location\.|history\.|Math\.random|crypto\./);
  assert.match(modal, /Gerar senha temporária/); // confirmação explícita antes de gerar (a senha anterior deixa de valer)
  const aviso = semComentarios(ler("components/plataforma/SenhaTemporariaAviso.tsx"));
  for (const botao of ["Copiar endereço", "Copiar usuário", "Copiar senha"]) assert.match(aviso, new RegExp(botao), botao);
  assert.match(aviso, /\{AVISO_SENHA_UNICA\}/);
});

test("a senha vem do servidor: criar devolve a senha uma vez e a regeneração é um POST (nunca um GET)", () => {
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /export async function criarUsuarioReal\([^)]*\): Promise<UsuarioCriado>/);
  assert.match(api, /senhaTemporaria\?: string \| null/);
  const gerar = api.slice(api.indexOf("export async function gerarSenhaTemporariaUsuarioReal"));
  assert.match(gerar.slice(0, 400), /\/senha-temporaria`, \{\s*method: "POST"/);
  assert.doesNotMatch(api, /\/senha-temporaria[^`]*`\s*\)/); // nenhuma leitura (GET) desse caminho
  // a senha não faz parte do tipo Usuario guardado em listas/estado compartilhado
  const tipos = semComentarios(ler("types/usuario.ts"));
  assert.doesNotMatch(tipos, /senha/i);
});

test("a view guarda a senha só em estado local, descarta ao fechar e a criação abre a entrega", () => {
  const view = semComentarios(ler("components/usuarios/UsuariosView.tsx"));
  assert.match(view, /const \{ usuario: criado, senhaTemporaria \} = await criarUsuarioReal\(draft, empresaId\);/);
  assert.match(view, /if \(senhaTemporaria\) setEntregaSenha\(/);
  assert.match(view, /onClose=\{\(\) => \{\s*setEntregaSenha\(null\);/); // fechou = a senha some
  assert.doesNotMatch(view, /localStorage|sessionStorage|console\./);
});

test('"Senha temporária" só aparece com primeiro acesso pendente, usuário ativo, autoridade e nunca sobre si mesmo', () => {
  const view = semComentarios(ler("components/usuarios/UsuariosView.tsx"));
  assert.match(
    view,
    /podeGerarSenha = \(alvo: Usuario\) => podeEditar\(alvo\) && alvo\.ativo && alvo\.primeiroAcessoPendente === true && alvo\.id !== usuarioAtual\?\.id/,
  );
  const tabela = semComentarios(ler("components/usuarios/UsuariosTable.tsx"));
  assert.match(tabela, /podeGerarSenha\(usuario\) && \(/);
  assert.match(tabela, /Primeiro acesso pendente/);
});

test("o cabeçalho do cadastro deixa de prometer 'senha própria' no ato da criação", () => {
  const form = ler("components/usuarios/UsuarioFormModal.tsx");
  assert.doesNotMatch(form, /login com e-mail e senha própria/);
  assert.match(form, /senha temporária de primeiro acesso, exibida uma única vez/);
});
