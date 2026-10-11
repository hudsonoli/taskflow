// Fase 4 — Dashboard da Administração da Plataforma. `npm run test:platform-dashboard` (node --test, sem dependências).
// Lógica pura (`plataformaDashboard.ts`) exercitada de verdade; a view/rotas (.tsx com alias `@/`) são lidas como texto para
// provar o que não aparece em tipos: KPIs, tabela, atenção, estados, abrir empresa sem trocar sessão e console neutro.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { formatarProporcao, hrefDaEmpresa, kpisDoResumo, rotuloUltimoAcesso } from "./plataformaDashboard.ts";
import type { DashboardResumo } from "../types/plataforma.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const RESUMO: DashboardResumo = {
  empresasTotal: 4, empresasAtivas: 3, usuarios: 10, cadastrados: 12, jaAcessaram: 7, nuncaAcessaram: 3, ativos7d: 4, ativos30d: 5, gestores: 5,
};

// ── helpers puros ────────────────────────────────────────────────────────────────────────────────────
test("formatarProporcao mostra absoluto e percentual; total zero não divide", () => {
  assert.equal(formatarProporcao(7, 10), "7/10 · 70%");
  assert.equal(formatarProporcao(1, 3), "1/3 · 33%");
  assert.equal(formatarProporcao(0, 5), "0/5 · 0%");
  assert.equal(formatarProporcao(5, 5), "5/5 · 100%");
  assert.equal(formatarProporcao(0, 0), "0/0"); // empresa sem usuários: sem NaN%
});

test("kpisDoResumo: seis indicadores, na ordem pedida, com números absolutos do backend", () => {
  const kpis = kpisDoResumo(RESUMO);
  assert.deepEqual(kpis.map((k) => k.label), ["Empresas ativas", "Usuários", "Já acessaram", "Ativos 30 dias", "Nunca acessaram", "Gestores"]);
  assert.deepEqual(kpis.map((k) => k.value), [3, 10, 7, 5, 3, 5]);
  assert.match(kpis[2].description, /7\/10 · 70%/);
  assert.match(kpis[3].description, /não indica presença em tempo real/i);
  assert.match(kpis[0].description, /4 cadastradas/);
});

test("zero em tudo continua válido (sem empresas/usuários)", () => {
  const zero: DashboardResumo = { empresasTotal: 0, empresasAtivas: 0, usuarios: 0, cadastrados: 0, jaAcessaram: 0, nuncaAcessaram: 0, ativos7d: 0, ativos30d: 0, gestores: 0 };
  const kpis = kpisDoResumo(zero);
  assert.deepEqual(kpis.map((k) => k.value), [0, 0, 0, 0, 0, 0]);
  assert.ok(kpis.every((k) => !/NaN|Infinity/.test(k.description)));
});

test("rotuloUltimoAcesso: Hoje/Ontem/dias/meses e 'Nunca' sem login; data inválida não quebra", () => {
  const agora = new Date("2026-10-08T12:00:00Z");
  const ha = (ms: number) => new Date(agora.getTime() - ms).toISOString();
  const dia = 24 * 60 * 60 * 1000;
  assert.equal(rotuloUltimoAcesso(null, agora), "Nunca");
  assert.equal(rotuloUltimoAcesso(ha(3 * 60 * 60 * 1000), agora), "Hoje");
  assert.equal(rotuloUltimoAcesso(ha(1.5 * dia), agora), "Ontem");
  assert.equal(rotuloUltimoAcesso(ha(5 * dia), agora), "Há 5 dias");
  assert.equal(rotuloUltimoAcesso(ha(45 * dia), agora), "Há 1 mês");
  assert.equal(rotuloUltimoAcesso(ha(100 * dia), agora), "Há 3 meses");
  assert.equal(rotuloUltimoAcesso(ha(500 * dia), agora), "Há mais de 1 ano");
  assert.equal(rotuloUltimoAcesso("não é data", agora), "—");
});

test("abrir empresa leva ao console da empresa (id codificado), sem sessão tenant", () => {
  assert.equal(hrefDaEmpresa({ id: "abc-123" }), "/gestao/empresas/abc-123");
  assert.equal(hrefDaEmpresa({ id: "a/b" }), "/gestao/empresas/a%2Fb");
});

// ── view: estrutura ──────────────────────────────────────────────────────────────────────────────────
test("a view usa o KpiStrip existente e consome SÓ o endpoint agregado", () => {
  const view = ler("components/plataforma/PlataformaDashboardView.tsx");
  const codigo = semComentarios(view);
  assert.match(codigo, /KpiStrip ariaLabel="Indicadores globais da plataforma"/);
  assert.match(codigo, /kpisDoResumo\(dados\.resumo\)/);
  assert.match(codigo, /obterDashboardPlataforma\(\)/);
  assert.doesNotMatch(codigo, /listarUsuariosEmpresa|obterEmpresaPlataforma|listarEmpresasPlataforma/); // sem N+1 no cliente
  assert.match(ler("lib/plataforma-api.ts"), /obterDashboardPlataforma = \(\) => pedir<PlataformaDashboard>\("\/dashboard"\)/);
});

test("tabela 'Uso por empresa': todas as colunas pedidas e proporção com absoluto", () => {
  const codigo = semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx"));
  for (const coluna of ["Empresa", "Usuários", "Já acessaram", "Ativos 30d", "Nunca acessaram", "Gestores", "Último acesso"]) {
    assert.ok(codigo.includes(coluna), coluna);
  }
  assert.match(codigo, /formatarProporcao\(empresa\.jaAcessaram, empresa\.usuarios\)/);
  assert.match(codigo, /Uso por empresa/);
  // não usa "Última atividade": só o login é rastreado
  assert.doesNotMatch(codigo, /Última atividade/);
});

test("multi-Gestores e zero Gestor: contagem numérica e selo 'Sem Gestor'", () => {
  const codigo = semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx"));
  assert.match(codigo, /empresa\.gestores > 0 \? empresa\.gestores : <Badge[^>]*>Sem Gestor<\/Badge>/);
  assert.match(codigo, /empresa\.gestores > 0 \? String\(empresa\.gestores\) : "Sem Gestor"/); // cartão mobile
});

test("'Precisa de atenção': lista objetiva com severidade, abrir empresa e estado vazio", () => {
  const codigo = semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx"));
  assert.match(codigo, /Precisa de atenção/);
  assert.match(codigo, /dados\.atencoes\.length === 0/);
  assert.match(codigo, /Nada precisa de atenção agora/);
  assert.match(codigo, /atencao\.severidade === "aviso"/);
  assert.match(codigo, /\{atencao\.empresaNome\}<\/span> — \{atencao\.mensagem\}/);
});

test("estados: loading, erro com 'tentar novamente' e vazio", () => {
  const codigo = semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx"));
  assert.match(codigo, /Carregando dashboard…/);
  assert.match(codigo, /<EstadoErro mensagem=\{erro\} onRetry=\{carregar\}/);
  assert.match(codigo, /Nenhuma empresa cadastrada/);
});

test("responsivo: tabela em md+, cartões no mobile; colunas extras só em xl", () => {
  const codigo = semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx"));
  assert.match(codigo, /hidden overflow-x-auto[^"]*md:block/);
  assert.match(codigo, /flex flex-col gap-2 md:hidden/);
  assert.match(codigo, /xl:table-cell/); // Projetos/Demandas só em telas largas
});

test("'Abrir' é um link para a empresa no console — nada de impersonação nem troca de sessão", () => {
  const view = semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx"));
  assert.match(view, /href=\{hrefDaEmpresa\(empresa\)\}/);
  assert.doesNotMatch(view, /tf_session|SESSION_COOKIE|impersonar|\/api\/auth|abrirSessao|sessaoSuporte|tf_support/i);
});

test("privacidade da tela: nenhum dado individual ou operacional é renderizado", () => {
  const codigo = semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx"));
  assert.doesNotMatch(codigo, /\.email|usuario\.nome|cliente|comentario|documento|demanda\.titulo/i);
  const tipos = ler("types/plataforma.ts");
  const bloco = tipos.slice(tipos.indexOf("export type DashboardResumo"));
  assert.doesNotMatch(bloco, /email|senha|token|nomeUsuario|usuarioId|isSystemAccount/i);
});

test("/gestao é a Dashboard; Empresas continua existindo; o console segue neutro", () => {
  assert.match(ler("app/gestao/page.tsx"), /<PlataformaDashboardView \/>/);
  assert.match(ler("app/gestao/empresas/page.tsx"), /<EmpresasPlataformaView \/>/);
  const shell = ler("components/plataforma/PlataformaShell.tsx");
  assert.match(shell, /rotulo: "Dashboard"/);
  assert.match(shell, /href: "\/gestao\/empresas", rotulo: "Empresas"/);
  assert.match(shell, /Em breve/); // Suporte continua só um marcador
  assert.doesNotMatch(semComentarios(ler("components/plataforma/PlataformaDashboardView.tsx")), /useBranding|aplicarBranding/);
  // a marca neutra do console vem do layout raiz (contexto "gestao") — inalterado
  assert.match(ler("app/layout.tsx"), /contextoPlataforma\s*\? \{ branding: BRANDING_PADRAO/);
  // acesso decidido no backend, nunca por perfil
  assert.doesNotMatch(semComentarios(ler("components/plataforma/PlataformaGuard.tsx")), /perfilBase|"gestor"|isSystemAccount/);
});
