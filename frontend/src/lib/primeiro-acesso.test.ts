// Fase 10B.1 — primeiro acesso por senha TEMPORÁRIA e troca obrigatória. `npm run test:primeiro-acesso` (node --test, sem dependências).
// Lógica pura (validação/corpo/rota da troca inicial) exercitada de verdade; telas e BFF (alias `@/`) lidos como texto para provar: login normal → redirect para
// /e/<slug>/trocar-senha-inicial; a tela pede SÓ "Nova senha" e "Repita a nova senha"; loading/erro/sucesso; volta para /e/<slug>/meu-dia com o mesmo slug e a mesma marca.
// (A imposição real é do SERVIDOR — 403 SENHA_TROCA_OBRIGATORIA em toda a aplicação — e é provada nos testes de backend e na validação DEV.)
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";
import { SENHA_MIN, corpoDaTrocaInicial, rotaDaTrocaInicial, validarTrocaInicial } from "./senha-inicial.ts";
import { caminhoDoTenant, ehRotaDeLogin, ehRotaDeTrocaDeSenhaInicial, ehRotaDeRecuperacaoDeSenha, slugDaRota, usaTemaDaEmpresa } from "./tenant.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const existe = (caminho: string) => existsSync(new URL(caminho, SRC));
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

// ── lógica pura ──────────────────────────────────────────────────────────────────────────────────────────────

test("validação da troca inicial: mínimo 8, confirmação igual; senhas diferentes ou curtas geram erro; ok = sem erros", () => {
  assert.equal(SENHA_MIN, 8);
  assert.deepEqual(validarTrocaInicial("SenhaPessoal1!", "SenhaPessoal1!"), {});
  assert.match(validarTrocaInicial("curta", "curta").novaSenha ?? "", /pelo menos 8/);
  assert.match(validarTrocaInicial("SenhaPessoal1!", "OutraSenha1!").confirmacaoSenha ?? "", /não confere/);
  assert.equal(validarTrocaInicial("SenhaPessoal1!", "OutraSenha1!").novaSenha, undefined);
  const vazio = validarTrocaInicial("", "");
  assert.ok(vazio.novaSenha);
  assert.equal(vazio.confirmacaoSenha, undefined); // vazias coincidem; o erro útil é o da nova senha
});

test("o corpo enviado ao servidor tem SÓ novaSenha e confirmacaoSenha — nunca senha atual/temporária, token ou código", () => {
  const corpo = corpoDaTrocaInicial("SenhaPessoal1!", "SenhaPessoal1!");
  assert.deepEqual(Object.keys(corpo).sort(), ["confirmacaoSenha", "novaSenha"]);
  assert.doesNotMatch(JSON.stringify(corpo), /atual|temporari|token|codigo/i);
});

test("a rota da troca é /e/<slug>/trocar-senha-inicial e mantém o slug; é tela 'nua' que usa o tema da empresa, não pública sem sessão", () => {
  assert.equal(rotaDaTrocaInicial("boxcom"), "/e/boxcom/trocar-senha-inicial");
  assert.equal(caminhoDoTenant("boxcom", "trocar-senha-inicial"), "/e/boxcom/trocar-senha-inicial");
  assert.equal(slugDaRota("/e/boxcom/trocar-senha-inicial"), "boxcom");
  assert.ok(ehRotaDeTrocaDeSenhaInicial("/e/boxcom/trocar-senha-inicial"));
  assert.ok(!ehRotaDeTrocaDeSenhaInicial("/trocar-senha-inicial")); // a rota sem slug não existe mais
  assert.ok(usaTemaDaEmpresa("/e/boxcom/trocar-senha-inicial")); // marca da EMPRESA (logo, cores) também aqui
  assert.ok(!ehRotaDeLogin("/e/boxcom/trocar-senha-inicial") && !ehRotaDeRecuperacaoDeSenha("/e/boxcom/trocar-senha-inicial"));
  assert.equal(existe("app/e/[slug]/trocar-senha-inicial/page.tsx"), true);
  assert.equal(existe("app/trocar-senha-inicial/page.tsx"), false);
});

// ── login com a temporária → redirect obrigatório ────────────────────────────────────────────────────────────

test("login normal com a senha temporária redireciona para /e/<slug>/trocar-senha-inicial (e o AppShell mantém o redirect em qualquer rota tenant)", () => {
  const login = semComentarios(ler("components/auth/LoginView.tsx"));
  assert.equal((login.match(/router\.replace\(mustChangePassword \? caminhoDoTenant\(slug, "trocar-senha-inicial"\) : destinoAposLogin\(slug, proximo, caminhoDoTenant\(slug, "meu-dia"\)\)\)/g) ?? []).length, 2); // senha + Google
  const shell = semComentarios(ler("components/layout/AppShell.tsx"));
  assert.match(shell, /if \(autenticado && mustChangePassword && !rotaTrocaSenha\) \{\s*router\.replace\(caminhoDoTenant\(slugUrl, "trocar-senha-inicial"\)\);/);
  // enquanto a troca está pendente a área autenticada nem renderiza (sem flash de conteúdo)
  assert.match(shell, /if \(sessaoCarregando \|\| !autenticado \|\| mustChangePassword\) \{/);
  // o login por slug não tem campo de "senha atual": é o login comum (e-mail + senha)
  assert.doesNotMatch(login, /senha temporária|senhaTemporaria/i);
});

test("o redirect do React NÃO é a barreira: o servidor responde 403 SENHA_TROCA_OBRIGATORIA e o cliente trata a sessão pelo mustChangePassword do servidor", () => {
  const dados = semComentarios(ler("lib/AppDataContext.tsx"));
  assert.match(dados, /setMustChangePassword\(sessao\.mustChangePassword\)/);
  assert.match(dados, /if \(sessao\.mustChangePassword\) \{/); // perfil completo só depois da troca (o servidor também bloqueia /usuarios/me)
  assert.match(ler("types/plataforma.ts"), /primeiroAcessoPendente/); // sinal discreto na Gestão (nunca a senha)
});

// ── a tela ───────────────────────────────────────────────────────────────────────────────────────────────────

test("a tela de troca tem SOMENTE 'Nova senha' e 'Repita a nova senha' — sem senha atual/temporária, token ou código", () => {
  const tela = semComentarios(ler("components/auth/TrocarSenhaInicialView.tsx"));
  assert.match(tela, /label="Nova senha"/);
  assert.match(tela, /label="Repita a nova senha"/);
  assert.equal((tela.match(/<Input\b/g) ?? []).length, 2); // exatamente dois campos
  assert.doesNotMatch(tela, /Senha atual|senha atual|senhaAtual|temporária|Token|token|Código|código|current-password/);
  assert.match(tela, /Criar minha senha/);
  assert.match(tela, /autoComplete="new-password"/);
});

test("senhas diferentes/curtas são recusadas antes de enviar; loading, erro do servidor e sucesso estão tratados", () => {
  const tela = semComentarios(ler("components/auth/TrocarSenhaInicialView.tsx"));
  assert.match(tela, /validarTrocaInicial\(novaSenha, confirmacaoSenha\)/);
  assert.match(tela, /if \(erros\.novaSenha \|\| erros\.confirmacaoSenha \|\| enviando\) return;/);
  assert.match(tela, /\{tentou && erros\.confirmacaoSenha &&/);
  assert.match(tela, /setEnviando\(true\)/);
  assert.match(tela, /\{enviando \? "Salvando…" : "Criar minha senha"\}/);
  assert.match(tela, /disabled=\{enviando\}/);
  assert.match(tela, /setErro\(error instanceof Error \? error\.message : "Não foi possível criar a senha"\)/);
  assert.match(tela, /<p role="alert"/);
});

test("sucesso: recarrega a sessão (a obrigação some) e vai para /e/<slug>/meu-dia — mesmo slug, mesma marca, sem novo login", () => {
  const tela = semComentarios(ler("components/auth/TrocarSenhaInicialView.tsx"));
  assert.match(tela, /await definirSenhaInicial\(novaSenha, confirmacaoSenha\);\s*await recarregarSessao\(\);\s*router\.replace\(tp\("meu-dia"\)\);/);
  assert.match(tela, /<BrandLogo variant="auth"/); // marca da empresa (a do slug) também aqui
  assert.doesNotMatch(tela, /router\.(push|replace)\("\/|"\/meu-dia"|\/login|logout/); // nada de rota sem slug nem logout forçado
  assert.doesNotMatch(tela, /localStorage|sessionStorage|console\./); // senha nunca persistida/registrada
});

// ── cliente e BFF ────────────────────────────────────────────────────────────────────────────────────────────

test("o cliente chama o BFF dedicado com corpo estrito; a troca antiga com 'senha atual' deixou de ser usada no primeiro acesso", () => {
  const auth = semComentarios(ler("lib/auth.ts"));
  assert.match(auth, /fetch\("\/api\/auth\/definir-senha-inicial"/);
  assert.match(auth, /JSON\.stringify\(corpoDaTrocaInicial\(novaSenha, confirmacaoSenha\)\)/);
  assert.doesNotMatch(auth, /alterarSenhaInicial/);
  assert.equal(existe("app/api/auth/definir-senha-inicial/route.ts"), true);
});

test("BFF /api/auth/definir-senha-inicial: exige sessão, repassa SÓ novaSenha/confirmacaoSenha ao backend, sem cache e sem registrar a senha", () => {
  const bff = semComentarios(ler("app/api/auth/definir-senha-inicial/route.ts"));
  assert.match(bff, /cookieStore\.get\(SESSION_COOKIE_NAME\)/);
  assert.match(bff, /status: 401/);
  assert.match(bff, /\$\{BACKEND_URL\}\/auth\/definir-senha-inicial/);
  assert.match(bff, /body: JSON\.stringify\(\{ novaSenha, confirmacaoSenha \}\)/);
  assert.doesNotMatch(bff, /senhaAtual|console\.|request\.text\(\)/);
  assert.match(bff, /"Cache-Control": "no-store"/);
  assert.match(bff, /backendResponse\.status === 204/);
});

test("regeneração e onboarding NÃO enviam e-mail nem criam token: a entrega da senha é manual, pela Gestão", () => {
  const api = semComentarios(ler("lib/plataforma-api.ts"));
  assert.match(api, /gerarNovaSenhaTemporaria = /);
  assert.match(api, /onboardingEmpresaPlataforma = /);
  assert.doesNotMatch(api, /email|smtp|convite/i);
});
