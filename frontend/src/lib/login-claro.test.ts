// Tela de login: layout dividido (referência 21st.dev "Split Sign In Form") e SEMPRE em tema claro. `npm run test:login`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (codigo: string) => codigo.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

const login = semComentarios(ler("components/auth/LoginView.tsx"));
const css = ler("app/globals.css");

test("o login é sempre claro: escopo data-theme=claro próprio, sem variantes dark: e sem classes que o Glass sobrepõe", () => {
  assert.match(login, /<div data-theme="claro" data-login-claro className="min-h-screen bg-white text-fg lg:grid lg:grid-cols-2">/);
  assert.doesNotMatch(login, /dark:/);
  // o estilo Glass reescreve estas classes por descendência do <html>; o login não as usa, então nada do Glass/escuro vaza para dentro dele
  assert.doesNotMatch(login, /\bbg-app\b|\bbg-surface\b|border-zinc-|divide-zinc-|data-superficie|\bthead\b/);
  assert.doesNotMatch(login, /useBranding|temaEfetivo|useEstiloVisual|resolveEffectiveTheme/); // não consulta tema nem estilo
});

test("o <html> acompanha: esquema de cores claro e fundo branco enquanto a tela de login está montada (fora do bloco Glass)", () => {
  assert.match(css, /html:has\(\[data-login-claro\]\) \{\s*color-scheme: light;\s*\}/);
  assert.match(css, /html:has\(\[data-login-claro\]\) body \{\s*background: #ffffff;\s*\}/);
  assert.ok(css.indexOf("data-login-claro") < css.indexOf("/* ── Estilo visual Glass")); // a regra não faz parte do Glass
});

test("o layout é dividido (formulário + painel de marca) e o painel é decorativo, sem imagem externa nem depoimento", () => {
  assert.match(login, /<main className=/);
  assert.match(login, /<aside aria-hidden className="relative hidden overflow-hidden bg-brand-gradient lg:flex/);
  assert.doesNotMatch(login, /<img|url\(|unsplash|21st/i);
  assert.deepEqual(login.match(/https?:\/\/[^"'`\s)]+/g), ["https://accounts.google.com/gsi/client"]); // a única URL externa é o script do Google que já existia
});

test("a autenticação não mudou: mesmos campos, mesmas chamadas, link de recuperação por slug e Google só com e-mail válido", () => {
  assert.match(login, /await login\(email, senha, slug\)/);
  assert.match(login, /await loginGoogle\(email, idToken, slug\)/);
  assert.match(login, /autoComplete="username"/);
  assert.match(login, /autoComplete="current-password"/);
  assert.match(login, /hrefDoTenant\(slug, "esqueci-senha"\)/);
  assert.match(login, /googleClientId && emailValido && \(/);
  assert.match(login, /MENSAGEM_SESSAO_EXPIRADA/);
  assert.match(login, /destinoAposLogin\(slug, proximo, caminhoDoTenant\(slug, "meu-dia"\)\)/);
  assert.match(login, /\{nomeEmpresa \?\? `Entrar no \$\{NOME_PRODUTO\}`\}/);
  assert.doesNotMatch(login, /EMPRESA_CODIGO|boxcom/i);
});

test("campo de senha com botão de mostrar/ocultar acessível (tipo alterna entre password e text; nada é persistido)", () => {
  assert.match(login, /type=\{senhaVisivel \? "text" : "password"\}/);
  assert.match(login, /aria-label=\{senhaVisivel \? "Ocultar senha" : "Mostrar senha"\}/);
  assert.match(login, /aria-pressed=\{senhaVisivel\}/);
  assert.doesNotMatch(login, /localStorage|sessionStorage/);
});

test("a rota do login continua entregando a empresa do slug e as demais telas de auth não foram tocadas", () => {
  const pagina = semComentarios(ler("app/e/[slug]/login/page.tsx"));
  assert.match(pagina, /<LoginView googleClientId=\{GOOGLE_OAUTH_CLIENT_ID\} slug=\{empresa\.slug\} nomeEmpresa=\{empresa\.nome\}/);
  for (const arquivo of ["components/auth/EsqueciSenhaView.tsx", "components/auth/RedefinirSenhaView.tsx", "components/auth/TrocarSenhaInicialView.tsx"]) {
    assert.match(semComentarios(ler(arquivo)), /data-superficie="cartao-central"/, arquivo);
  }
});
