// Fase 10B/10B.1 — onboarding de nova empresa pela Gestão (senha TEMPORÁRIA, sem convite/SMTP). `npm run test:gestao-onboarding` (node --test, sem dependências).
// Lógica pura (helpers do formulário, validações, payload, textos da entrega da senha, URL final) exercitada de verdade; telas/API (alias `@/`) são lidas como texto para provar
// o que tipos não mostram: slug sugerido e editável, reservados, branding pelo mecanismo existente, senha temporária única, loading/erro/sucesso, copiar endereço, sem tenant
// switch nem impersonação.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  ONBOARDING_VAZIO,
  AVISO_SENHA_UNICA,
  CONFIRMACAO_NOVA_SENHA_TEMPORARIA,
  brandingDoRascunho,
  erroDaCorOpcional,
  erroDoEmailDoGestor,
  erroDoNomeDoGestor,
  payloadDoOnboarding,
  sugerirSlug,
  urlDeAcessoDaEmpresa,
  validarOnboarding,
  type RascunhoOnboarding,
} from "./plataforma.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const valido: RascunhoOnboarding = {
  ...ONBOARDING_VAZIO,
  nome: "Empresa Teste Onboarding",
  codigoInterno: "EMPRESA-TESTE-ONBOARDING",
  slug: "empresa-teste-onboarding",
  gestorNome: "Gestora Sintética",
  gestorEmail: "gestora@sintetico.test",
};

// ── slug: sugerido, editável, reservado ──────────────────────────────────────────────────────────────────────

test("slug sugerido a partir do nome (sem acento, minúsculas, hífen) e SEMPRE ajustável antes de salvar", () => {
  assert.equal(sugerirSlug("Empresa Teste Onboarding"), "empresa-teste-onboarding");
  assert.equal(sugerirSlug("BOX Comunicação"), "box-comunicacao"); // não assume que o slug é literal ("boxcom" é um ajuste manual válido)
  assert.equal(validarOnboarding({ ...valido, slug: "boxcom" }).slug, undefined);
  const modal = semComentarios(ler("components/plataforma/NovaEmpresaModal.tsx"));
  assert.match(modal, /if \(!slugEditado\) novo\.slug = base;/); // acompanha o nome enquanto ninguém mexeu
  assert.match(modal, /aoEditarSlug=\{\(valor\) => \{\s*setSlugEditado\(true\);/); // depois de editar, o slug é da pessoa
  assert.match(semComentarios(ler("components/plataforma/NovaEmpresaSecoes.tsx")), /onChange=\{\(e\) => aoEditarSlug\(e\.target\.value\.toLowerCase\(\)\)\}/);
});

test("slug reservado e inválido: o frontend ajuda (gestao, plataforma, api, e, login, aprovacao…); o BACKEND decide", () => {
  for (const reservado of ["gestao", "plataforma", "api", "login", "aprovacao", "logout", "admin", "suporte"]) {
    assert.match(validarOnboarding({ ...valido, slug: reservado }).slug ?? "", /reservado/, reservado);
  }
  assert.ok(validarOnboarding({ ...valido, slug: "e" }).slug); // reservado e curto demais: recusado de qualquer forma
  for (const ruim of ["Com Espaço", "-comeca", "termina-", "a_b", "ab", "x".repeat(41), "tem/barra"]) {
    assert.ok(validarOnboarding({ ...valido, slug: ruim }).slug, ruim);
  }
  // vazio vale (o servidor deriva do código); o payload manda minúsculas ou nulo
  assert.equal(validarOnboarding({ ...valido, slug: "" }).slug, undefined);
  assert.equal(payloadDoOnboarding({ ...valido, slug: "" }).empresa.slug, null);
  assert.equal(payloadDoOnboarding({ ...valido, slug: " Minha-Empresa " }).empresa.slug, "minha-empresa");
});

test("o slug é permanente na Gestão: somente leitura na edição e nunca enviado no PATCH", () => {
  const dados = semComentarios(ler("components/plataforma/EmpresaDadosSection.tsx"));
  assert.match(dados, /label="Slug \(endereço da empresa\)" value=\{empresa\.slug\} readOnly disabled/);
  assert.doesNotMatch(dados, /mudancas\.slug|atualizar\(\{ slug/);
});

// ── campos, validações, payload ──────────────────────────────────────────────────────────────────────────────

test("formulário em seções com SÓ campos reais do modelo: Dados da empresa · Identidade visual · Acesso inicial", () => {
  const secoes = semComentarios(ler("components/plataforma/NovaEmpresaSecoes.tsx"));
  for (const titulo of ["Dados da empresa", "Identidade visual (opcional)", "Acesso inicial — primeiro Gestor"]) assert.match(secoes, new RegExp(titulo.replace(/[()—]/g, "\\$&")));
  for (const campo of ["Nome da empresa", "Nome de exibição", "Documento", "Código interno", "Slug", "Logo", "Cor principal", "Cor de destaque", "Tema padrão", "Nome do Gestor", "E-mail do Gestor"]) {
    assert.match(secoes, new RegExp(campo), campo);
  }
  // nada de campo inventado: sem endereço/telefone/plano/status/perfil/senha no formulário
  assert.doesNotMatch(secoes, /Endereço|CEP|Telefone|Plano|Assinatura|Status|perfil|type="password"|Senha/);
  assert.deepEqual(Object.keys(payloadDoOnboarding(valido)).sort(), ["empresa", "gestor"]);
  assert.deepEqual(Object.keys(payloadDoOnboarding(valido).empresa).sort(), ["codigoInterno", "documento", "nome", "nomeFantasia", "slug"]);
  assert.deepEqual(Object.keys(payloadDoOnboarding(valido).gestor).sort(), ["email", "nome"]);
});

test("validações: nome, código, Gestor (nome/e-mail) e cores; tudo certo = sem erros; o servidor continua sendo a barreira", () => {
  assert.deepEqual(validarOnboarding(valido), {});
  const vazio = validarOnboarding(ONBOARDING_VAZIO);
  for (const campo of ["nome", "codigoInterno", "gestorNome", "gestorEmail"] as const) assert.ok(vazio[campo], campo);
  assert.equal(erroDoEmailDoGestor("sem-arroba"), "Informe um e-mail válido.");
  assert.equal(erroDoEmailDoGestor("a@b"), "Informe um e-mail válido.");
  assert.equal(erroDoEmailDoGestor(" ok@exemplo.com "), null);
  assert.match(erroDoNomeDoGestor("<b>Ana</b>") ?? "", /HTML/);
  assert.equal(erroDoNomeDoGestor("  Ana   Maria "), null);
  assert.equal(erroDaCorOpcional(""), null);
  assert.equal(erroDaCorOpcional("#16a34a"), null);
  assert.ok(erroDaCorOpcional("verde") && erroDaCorOpcional("#12345"));
  assert.equal(validarOnboarding({ ...valido, gestorNome: "Ana   Maria" }).gestorNome, undefined);
  assert.equal(payloadDoOnboarding({ ...valido, gestorNome: "Ana   Maria" }).gestor.nome, "Ana Maria"); // espaços normalizados
});

test("o status (ativa) e o perfil (gestor) são decididos pelo servidor: nunca vão no payload", () => {
  const texto = JSON.stringify(payloadDoOnboarding(valido));
  assert.doesNotMatch(texto, /status|perfilBase|senha|empresaId|acessoSistema/i);
});

// ── identidade visual: mecanismo existente ───────────────────────────────────────────────────────────────────

test("identidade visual pelo mecanismo EXISTENTE: cores/tema via PATCH de personalização e logo via upload da Gestão — falha vira aviso, não desfaz a empresa", () => {
  assert.equal(brandingDoRascunho(valido), null);
  assert.deepEqual(brandingDoRascunho({ ...valido, corPrimaria: "#16a34a", tema: "escuro" }), { corPrimaria: "#16a34a", tema: "escuro" });
  assert.deepEqual(brandingDoRascunho({ ...valido, corPrimaria: " #16a34a ", corSecundaria: "#9333ea", tema: "claro" }), { corPrimaria: "#16a34a", corSecundaria: "#9333ea", tema: "claro" });
  const modal = semComentarios(ler("components/plataforma/NovaEmpresaModal.tsx"));
  assert.match(modal, /atualizarBrandingEmpresa\(dados\.empresa\.id, marca\)/);
  assert.match(modal, /enviarLogoEmpresa\(dados\.empresa\.id, logo\)/);
  assert.match(modal, /validarLogoNoNavegador\(arquivo\)/); // tipo, tamanho e dimensões validados no navegador (o servidor revalida a assinatura real)
  assert.match(modal, /avisos\.push\(/);
  // sem novo sistema de temas nem logo por URL externa
  const secoes = semComentarios(ler("components/plataforma/NovaEmpresaSecoes.tsx"));
  assert.match(secoes, /accept="image\/png,image\/gif"/);
  assert.doesNotMatch(secoes + modal, /type="url"|logoUrl|http:\/\/|https:\/\//);
  assert.match(semComentarios(ler("app/api/plataforma/[...path]/route.ts")), /if \(hasBody && resposta\.ok\) invalidarBranding\(\);/); // /e/<slug>/login reflete já
});

// ── senha temporária: gerada no servidor, exibida UMA vez ────────────────────────────────────────────────────

test("o onboarding NÃO usa convite nem SMTP: nenhum token, link manual, reenvio de convite ou motivo de e-mail no frontend", () => {
  const todos = [
    "components/plataforma/NovaEmpresaModal.tsx",
    "components/plataforma/NovaEmpresaSecoes.tsx",
    "components/plataforma/SenhaTemporariaAviso.tsx",
    "components/plataforma/DefinirGestorModal.tsx",
    "components/plataforma/EmpresaUsuariosSection.tsx",
    "lib/plataforma-api.ts",
    "lib/plataforma.ts",
    "types/plataforma.ts",
  ].map((c) => semComentarios(ler(c)));
  for (const texto of todos) {
    assert.doesNotMatch(texto, /ConviteGestorAviso|reenviarConvite|linkAcesso|\/convite|PlataformaConvite|descreverConvite|email_nao_configurado|url_publica_ausente|falha_envio|SMTP|#token=/);
  }
  assert.throws(() => ler("components/plataforma/ConviteGestorAviso.tsx"), /ENOENT/);
});

test("texto do onboarding descreve o fluxo final: sem 'convite' e sem 'nenhuma senha é gerada'; com senha temporária, exibida uma única vez e senha pessoal no primeiro acesso", () => {
  // telas do onboarding (criar empresa + entregar a senha + regenerar): texto E comentários não podem voltar a descrever convite como mecanismo do primeiro acesso
  const telas = [
    "components/plataforma/NovaEmpresaModal.tsx",
    "components/plataforma/NovaEmpresaSecoes.tsx",
    "components/plataforma/SenhaTemporariaAviso.tsx",
    "components/plataforma/EmpresaUsuariosSection.tsx",
    "lib/useOrigem.ts",
  ];
  for (const caminho of telas) {
    const bruto = ler(caminho);
    assert.doesNotMatch(bruto, /convit|convida/i, `${caminho}: referência a convite`);
    assert.doesNotMatch(semComentarios(bruto), /nenhuma senha (é|foi|será) (criada|gerada|exibida)|sem senha/i, `${caminho}: afirma que não há senha`);
  }
  // o modal de "Definir Gestor" também não pode prometer convite (a frase 'nenhuma senha foi gerada' de lá trata de usuário EXISTENTE e é legítima)
  assert.doesNotMatch(semComentarios(ler("components/plataforma/DefinirGestorModal.tsx")), /convit|convida/i);
  // a seção "Acesso inicial" explica o fluxo real
  const secao = semComentarios(ler("components/plataforma/NovaEmpresaSecoes.tsx"));
  const acesso = secao.slice(secao.indexOf("export function SecaoAcessoInicial"));
  assert.match(acesso, /senha temporária/i);
  assert.match(acesso, /única vez/i);
  assert.match(acesso, /primeiro acesso/i);
  assert.match(acesso, /senha pessoal/i);
});

test("a senha temporária vem do SERVIDOR: a tela só a mostra; nada de gerar/derivar no navegador", () => {
  const modal = semComentarios(ler("components/plataforma/NovaEmpresaModal.tsx"));
  assert.match(modal, /senha=\{dados\.senhaTemporaria\}/);
  for (const arquivo of ["NovaEmpresaModal", "NovaEmpresaSecoes", "SenhaTemporariaAviso", "EmpresaUsuariosSection", "DefinirGestorModal"]) {
    const texto = semComentarios(ler(`components/plataforma/${arquivo}.tsx`));
    assert.doesNotMatch(texto, /Math\.random|crypto\.(getRandomValues|randomUUID)|new Date\(\)\.getTime|btoa\(|type="password"/);
  }
  // o formulário não pede nem envia senha
  assert.doesNotMatch(JSON.stringify(payloadDoOnboarding(valido)), /senha/i);
});

test("tela de sucesso: acesso (URL), usuário e senha temporária com Copiar endereço/usuário/senha e o aviso de exibição única", () => {
  const aviso = semComentarios(ler("components/plataforma/SenhaTemporariaAviso.tsx"));
  for (const botao of ["Copiar endereço", "Copiar usuário", "Copiar senha"]) assert.match(aviso, new RegExp(botao), botao);
  for (const teste of ["url-acesso", "usuario-gestor", "senha-temporaria"]) assert.match(aviso, new RegExp(`teste: "${teste}"`), teste);
  assert.match(aviso, /navigator\.clipboard\.writeText\(valor\)/);
  assert.match(aviso, /\{AVISO_SENHA_UNICA\}/);
  assert.equal(AVISO_SENHA_UNICA, "Esta senha será exibida somente agora. No primeiro acesso, o usuário deverá criar sua senha pessoal.");
  assert.match(aviso, /Entregue por um canal seguro/);
  // a senha nunca é gravada em storage, URL, console ou rota
  assert.doesNotMatch(aviso, /localStorage|sessionStorage|indexedDB|document\.cookie|console\.|router\.|location\.|history\./);
  const modal = ler("components/plataforma/NovaEmpresaModal.tsx");
  assert.match(modal, /function fechar\(\) \{\s*if \(salvando\) return;\s*reiniciar\(\);/); // fechar descarta a senha
  assert.match(modal, /setResultado\(null\)/);
  assert.doesNotMatch(semComentarios(modal), /localStorage|sessionStorage|console\./);
});

test("fechou a tela = a senha some: sem persistência no cliente e o servidor nunca a devolve de novo (nem em GET)", () => {
  const api = ler("lib/plataforma-api.ts");
  // o tipo da senha existe só nas respostas de criação/regeneração
  const tipos = ler("types/plataforma.ts");
  assert.equal((semComentarios(tipos).match(/senhaTemporaria/g) ?? []).length, 2); // PlataformaGestorCriado e PlataformaOnboarding
  const usuario = tipos.slice(tipos.indexOf("export type PlataformaUsuario"), tipos.indexOf("export type PlataformaGestorCreate"));
  assert.doesNotMatch(usuario, /senha|hash|token/i);
  const empresa = tipos.slice(tipos.indexOf("export type PlataformaEmpresa ="), tipos.indexOf("export type PlataformaEmpresaCreate"));
  assert.doesNotMatch(empresa, /senha|hash|token/i);
  assert.doesNotMatch(semComentarios(api), /localStorage|sessionStorage|cache:\s*"force-cache"/);
  // as respostas da Gestão nunca são cacheadas
  assert.match(semComentarios(ler("app/api/plataforma/[...path]/route.ts")), /headers: \{ "Cache-Control": "no-store" \}/);
});

test("regenerar: só para quem tem o primeiro acesso PENDENTE, com confirmação explícita e a nova senha exibida uma vez", () => {
  const secao = semComentarios(ler("components/plataforma/EmpresaUsuariosSection.tsx"));
  assert.match(secao, /usuario\.primeiroAcessoPendente \? \(/);
  assert.match(secao, /Primeiro acesso pendente/);
  assert.match(secao, /Gerar nova senha temporária/);
  assert.match(secao, /gerarNovaSenhaTemporaria\(empresa\.id, usuario\.id\)/);
  assert.match(secao, /role="alertdialog"/);
  assert.match(secao, /\{CONFIRMACAO_NOVA_SENHA_TEMPORARIA\}/);
  assert.match(secao, /<SenhaTemporariaAviso slug=\{empresa\.slug\} email=\{senhaGerada\.usuario\.email\} senha=\{senhaGerada\.senhaTemporaria\} \/>/);
  assert.match(secao, /<Badge tone="green">Concluído<\/Badge>/); // quem já concluiu o primeiro acesso não tem a ação
  assert.match(CONFIRMACAO_NOVA_SENHA_TEMPORARIA, /deixa de funcionar imediatamente/);
  assert.doesNotMatch(secao, /window\.confirm|confirm\(/); // confirmação na própria interface (o confirm nativo é frágil)
  assert.match(ler("lib/plataforma-api.ts"), /\/usuarios\/\$\{encodeURIComponent\(usuarioId\)\}\/senha-temporaria/);
});

// ── loading, erro, sucesso, URL final, copiar ────────────────────────────────────────────────────────────────

test("loading e erro do backend: botão desabilitado com 'Criando…', campos travados, mensagem do servidor (conflito de slug etc.) sem derrubar a Gestão", () => {
  const modal = semComentarios(ler("components/plataforma/NovaEmpresaModal.tsx"));
  assert.match(modal, /setSalvando\(true\)/);
  assert.match(modal, /\{salvando \? "Criando…" : "Criar empresa"\}/);
  assert.match(modal, /<Button type="submit" disabled=\{salvando\}>/);
  assert.match(modal, /setErro\(falha instanceof Error \? falha\.message : "Não foi possível criar a empresa\."\)/);
  assert.match(modal, /<p role="alert"/);
  assert.match(modal, /if \(invalido \|\| salvando\) return;/); // sem duplo envio
  assert.match(modal, /finally \{\s*setSalvando\(false\);/);
});

test("sucesso: mostra 'Empresa criada', o endereço /e/<slug>/login (sem token) e o Gestor; o slug exibido é o do SERVIDOR", () => {
  assert.equal(urlDeAcessoDaEmpresa("https://taskflow.technetgo.com.br", "empresa-teste-onboarding"), "https://taskflow.technetgo.com.br/e/empresa-teste-onboarding/login");
  assert.equal(urlDeAcessoDaEmpresa("https://x.com/", "acme"), "https://x.com/e/acme/login");
  assert.doesNotMatch(urlDeAcessoDaEmpresa("https://x.com", "acme"), /token|#|\?/);
  const modal = semComentarios(ler("components/plataforma/NovaEmpresaModal.tsx"));
  assert.match(modal, /Empresa criada/);
  assert.match(modal, /<SenhaTemporariaAviso slug=\{dados\.empresa\.slug\} urlAcesso=\{dados\.urlAcesso\} email=\{dados\.gestor\.email\} senha=\{dados\.senhaTemporaria\} \/>/);
  assert.match(modal, /dados\.gestor\.nome/);
  const cartao = semComentarios(ler("components/plataforma/EmpresaAcessoCard.tsx"));
  assert.match(cartao, /navigator\.clipboard\.writeText\(url\)/); // detalhe da empresa: só o endereço público
  assert.match(cartao, /Copiar endereço/);
  assert.doesNotMatch(cartao, /token|tf_session|accessToken|senha/i);
});

test("a Gestão permanece na Gestão: sem tenant switch, sem impersonação, sem abrir /e/<slug> automaticamente", () => {
  const arquivos = ["NovaEmpresaModal", "NovaEmpresaSecoes", "EmpresaAcessoCard", "SenhaTemporariaAviso"].map((n) => semComentarios(ler(`components/plataforma/${n}.tsx`)));
  for (const texto of arquivos) {
    assert.doesNotMatch(texto, /impersonate|useBranding|aplicarBranding|useTenantPath|tf_session|window\.open|location\.(href|assign|replace)/);
    assert.doesNotMatch(texto, /router\.(push|replace)\(`\/e\/|router\.(push|replace)\("\/e\//);
  }
  const modal = semComentarios(ler("components/plataforma/NovaEmpresaModal.tsx"));
  assert.match(modal, /router\.push\(`\/gestao\/empresas\/\$\{id\}`\)/); // "Abrir empresa na Gestão" — nunca o tenant
  assert.match(modal, /nenhuma sessão da empresa foi aberta e ninguém foi impersonado/);
  assert.match(modal, /usuário e a senha temporária do Gestor/);
  assert.match(semComentarios(ler("lib/plataforma-api.ts")), /onboardingEmpresaPlataforma = \(dados: PlataformaOnboardingCreate\)/);
});

test("detalhe da empresa na Gestão mostra nome, slug, status, endereço de acesso e Gestor(es) com sinal de primeiro acesso — sem segredos", () => {
  const detalhe = semComentarios(ler("components/plataforma/EmpresaPlataformaView.tsx"));
  assert.match(detalhe, /<EmpresaAcessoCard slug=\{empresa\.slug\} \/>/);
  assert.match(detalhe, /STATUS_EMPRESA_ROTULO\[empresa\.status\]/);
  const tipos = ler("types/plataforma.ts");
  const usuario = tipos.slice(tipos.indexOf("export type PlataformaUsuario"), tipos.indexOf("export type PlataformaGestorCreate"));
  assert.doesNotMatch(usuario, /senha|hash|token|smtp|credencial/i);
});

test("'Nova empresa' abre o formulário na lista de empresas da Gestão (sem wizard)", () => {
  const lista = semComentarios(ler("components/plataforma/EmpresasPlataformaView.tsx"));
  assert.match(lista, /Nova empresa/);
  assert.match(lista, /<NovaEmpresaModal/);
  assert.equal(ler("components/plataforma/NovaEmpresaModal.tsx").includes("wizard"), false);
});
