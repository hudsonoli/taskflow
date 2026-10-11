// Fase 10B — onboarding de nova empresa pela Gestão. `npm run test:gestao-onboarding` (node --test, sem dependências).
// Lógica pura (helpers do formulário, validações, payload, textos do convite, URL final) exercitada de verdade; telas/API (alias `@/`) são lidas como texto para provar
// o que tipos não mostram: slug sugerido e editável, reservados, branding pelo mecanismo existente, convite sem senha, loading/erro/sucesso, copiar endereço, sem tenant
// switch nem impersonação.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  ONBOARDING_VAZIO,
  absolutizarLink,
  brandingDoRascunho,
  descreverConvite,
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

// ── convite: sem senha ───────────────────────────────────────────────────────────────────────────────────────

test("convite: estado claro (enviado × não enviado com o MOTIVO) e nunca esconde a falha de SMTP", () => {
  assert.equal(descreverConvite({ enviado: true, motivo: null }).tom, "green");
  const sem = descreverConvite({ enviado: false, motivo: "email_nao_configurado" });
  assert.equal(sem.titulo, "Convite não enviado");
  assert.match(sem.detalhe, /SMTP/);
  assert.match(sem.detalhe, /criados normalmente/); // não desfaz a empresa
  assert.equal(sem.tom, "amber");
  assert.match(descreverConvite({ enviado: false, motivo: "falha_envio" }).detalhe, /não aceitou/);
  assert.match(descreverConvite({ enviado: false, motivo: "url_publica_ausente" }).detalhe, /endereço público/);
  assert.equal(absolutizarLink("https://taskflow.exemplo.com/", "/e/acme/redefinir-senha#token=x"), "https://taskflow.exemplo.com/e/acme/redefinir-senha#token=x");
  assert.equal(absolutizarLink("https://x.com", "https://y.com/e/a/redefinir-senha#token=x"), "https://y.com/e/a/redefinir-senha#token=x");
});

test("NENHUMA senha é pedida, gerada ou exibida: só convite; o link manual aparece uma vez e some ao fechar", () => {
  const todos = [
    "components/plataforma/NovaEmpresaModal.tsx",
    "components/plataforma/NovaEmpresaSecoes.tsx",
    "components/plataforma/ConviteGestorAviso.tsx",
    "components/plataforma/DefinirGestorModal.tsx",
    "components/plataforma/EmpresaUsuariosSection.tsx",
  ].map((c) => semComentarios(ler(c)));
  for (const texto of todos) assert.doesNotMatch(texto, /senhaTemporaria|type="password"|senha-temporaria|deveAlterarSenha/);
  assert.doesNotMatch(ler("types/plataforma.ts"), /senhaTemporaria/);
  const aviso = ler("components/plataforma/ConviteGestorAviso.tsx");
  assert.match(aviso, /uma única vez/);
  assert.match(aviso, /Copiar link/);
  const modal = ler("components/plataforma/NovaEmpresaModal.tsx");
  assert.match(modal, /function fechar\(\) \{\s*if \(salvando\) return;\s*reiniciar\(\);/); // descarta resultado e link
  assert.match(modal, /setResultado\(null\)/);
});

test("reenviar convite: só para quem tem convite pendente (sinal do servidor), com confirmação de resultado e link manual", () => {
  const secao = semComentarios(ler("components/plataforma/EmpresaUsuariosSection.tsx"));
  assert.match(secao, /usuario\.primeiroAcessoPendente \? \(/);
  assert.match(secao, /Convite pendente/);
  assert.match(secao, /reenviarConviteGestor\(empresa\.id, usuario\.id\)/);
  assert.match(secao, /<ConviteGestorAviso convite=\{convite\.convite\} \/>/);
  assert.match(ler("lib/plataforma-api.ts"), /\/usuarios\/\$\{encodeURIComponent\(usuarioId\)\}\/convite/);
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
  assert.match(modal, /<EmpresaAcessoCard slug=\{dados\.empresa\.slug\} urlAcesso=\{dados\.urlAcesso\} \/>/);
  assert.match(modal, /dados\.gestor\.nome/);
  const cartao = semComentarios(ler("components/plataforma/EmpresaAcessoCard.tsx"));
  assert.match(cartao, /navigator\.clipboard\.writeText\(url\)/);
  assert.match(cartao, /Copiar endereço/);
  assert.doesNotMatch(cartao, /token|tf_session|accessToken/);
});

test("a Gestão permanece na Gestão: sem tenant switch, sem impersonação, sem abrir /e/<slug> automaticamente", () => {
  const arquivos = ["NovaEmpresaModal", "NovaEmpresaSecoes", "EmpresaAcessoCard", "ConviteGestorAviso"].map((n) => semComentarios(ler(`components/plataforma/${n}.tsx`)));
  for (const texto of arquivos) {
    assert.doesNotMatch(texto, /impersonate|useBranding|aplicarBranding|useTenantPath|tf_session|window\.open|location\.(href|assign|replace)/);
    assert.doesNotMatch(texto, /router\.(push|replace)\(`\/e\/|router\.(push|replace)\("\/e\//);
  }
  const modal = semComentarios(ler("components/plataforma/NovaEmpresaModal.tsx"));
  assert.match(modal, /router\.push\(`\/gestao\/empresas\/\$\{id\}`\)/); // "Abrir empresa na Gestão" — nunca o tenant
  assert.match(modal, /nenhuma sessão da empresa foi aberta e ninguém foi impersonado/);
  assert.match(semComentarios(ler("lib/plataforma-api.ts")), /onboardingEmpresaPlataforma = \(dados: PlataformaOnboardingCreate\)/);
});

test("detalhe da empresa na Gestão mostra nome, slug, status, endereço de acesso e Gestor(es) com convite — sem segredos", () => {
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
