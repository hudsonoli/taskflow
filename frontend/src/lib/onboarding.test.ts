// Fase 3 — Gestor existente/novo, BrasilAPI (Clientes e Fornecedores) e exemplo "GRUPO ACME".
// `npm run test:onboarding` (node --test, sem dependências). A consulta de CNPJ é exercitada de verdade com `fetch`
// MOCKADO (nenhum teste usa a internet); telas e rotas (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  MENSAGENS_CONSULTA,
  camposParaFormulario,
  cnpjValido,
  consultarCnpj,
  falhaPorStatus,
  mapearRespostaBrasilApi,
  somenteDigitos,
} from "./brasilApi.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const UFS = ["SP", "RJ", "MG", "DF"];
const CNPJ = "00000000000191"; // CNPJ público válido (dígitos verificadores corretos)
const CNPJ_MASCARA = "00.000.000/0001-91";

// Resposta no formato real de GET /api/cnpj/v1/{cnpj}
const RESPOSTA = {
  cnpj: CNPJ,
  razao_social: "BANCO DO BRASIL SA",
  nome_fantasia: "DIRETORIA GERAL",
  descricao_tipo_logradouro: "SETOR",
  logradouro: "DE AUTARQUIAS NORTE",
  numero: "QUADRA 5",
  complemento: "LOTE B",
  bairro: "ASA NORTE",
  cep: "70040912",
  municipio: "BRASILIA",
  uf: "DF",
  ddd_telefone_1: "6134939002",
  email: null,
};

function respostaJson(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } });
}

// ── CNPJ: validação e normalização ───────────────────────────────────────────────────────────────────
test("cnpjValido aceita com e sem máscara e recusa inválidos", () => {
  assert.ok(cnpjValido(CNPJ));
  assert.ok(cnpjValido(CNPJ_MASCARA));
  assert.ok(cnpjValido("11.222.333/0001-81"));
  for (const ruim of ["", "123", "00000000000192", "11111111111111", "00.000.000/0001-9", "abc", "0000000000019100"]) {
    assert.equal(cnpjValido(ruim), false, ruim);
  }
  assert.equal(somenteDigitos(CNPJ_MASCARA), CNPJ);
});

// ── mapeamento da resposta ───────────────────────────────────────────────────────────────────────────
test("mapearRespostaBrasilApi converte só o que conhece e formata CEP, telefone e endereço", () => {
  const d = mapearRespostaBrasilApi(RESPOSTA);
  assert.deepEqual(d, {
    razaoSocial: "BANCO DO BRASIL SA",
    nomeFantasia: "DIRETORIA GERAL",
    cep: "70040-912",
    bairro: "ASA NORTE",
    enderecoCompleto: "SETOR DE AUTARQUIAS NORTE, QUADRA 5 - LOTE B",
    cidade: "BRASILIA",
    uf: "DF",
    telefone: "(61) 3493-9002",
    email: null,
  });
});

test("resposta parcial: campos ausentes/nulos viram null; sem nome nenhum não é cadastro utilizável", () => {
  const parcial = mapearRespostaBrasilApi({ razao_social: "ACME LTDA", cep: null, uf: "xx", email: "  CONTATO@ACME.COM ", ddd_telefone_1: "123" });
  assert.equal(parcial?.razaoSocial, "ACME LTDA");
  assert.equal(parcial?.nomeFantasia, null);
  assert.equal(parcial?.cep, null);
  assert.equal(parcial?.uf, "XX"); // formato de UF (2 letras) normalizado; só UF existente no formulário é aplicada (teste abaixo)
  assert.equal(parcial?.telefone, null);
  assert.equal(parcial?.email, "contato@acme.com");
  for (const ruim of [null, undefined, "x", 42, [], {}, { razao_social: "", nome_fantasia: "   " }]) {
    assert.equal(mapearRespostaBrasilApi(ruim), null, String(ruim));
  }
});

test("número 'SN' vira S/N e o User-Agent identificável é enviado pelo BFF", () => {
  const d = mapearRespostaBrasilApi({ razao_social: "X LTDA", logradouro: "SAUN QUADRA 5", numero: "SN", complemento: null });
  assert.equal(d?.enderecoCompleto, "SAUN QUADRA 5, S/N");
  const bff = ler("lib/server/brasilApiBff.ts"); // infraestrutura de servidor compartilhada (CNPJ e CEP)
  assert.match(bff, /"User-Agent": USER_AGENT_CONSULTA/);
  assert.match(ler("lib/brasilApi.ts"), /USER_AGENT_CONSULTA = "TaskFloww\/1\.0"/);
});

test("camposParaFormulario devolve SÓ o que veio preenchido e só UF existente no formulário", () => {
  const campos = camposParaFormulario(mapearRespostaBrasilApi(RESPOSTA)!, UFS);
  assert.deepEqual(Object.keys(campos).sort(), ["bairro", "cep", "cidade", "enderecoCompleto", "nome", "razaoSocial", "telefone", "uf"]);
  assert.equal(campos.nome, "DIRETORIA GERAL"); // nome fantasia primeiro
  assert.equal("email" in campos, false); // null da API nunca vira campo (nunca apaga o que a pessoa digitou)

  const semFantasia = camposParaFormulario({ ...mapearRespostaBrasilApi(RESPOSTA)!, nomeFantasia: null }, UFS);
  assert.equal(semFantasia.nome, "BANCO DO BRASIL SA"); // sem fantasia, razão social
  const ufDesconhecida = camposParaFormulario({ ...mapearRespostaBrasilApi(RESPOSTA)!, uf: "ZZ" }, UFS);
  assert.equal("uf" in ufDesconhecida, false);
  const vazio = camposParaFormulario(
    { razaoSocial: null, nomeFantasia: null, cep: null, bairro: null, enderecoCompleto: null, cidade: null, uf: null, telefone: null, email: null },
    UFS,
  );
  assert.deepEqual(vazio, {});
});

test("valor vazio da API não substitui o digitado (simulação do merge usado pelos formulários)", () => {
  const digitado = { nome: "Meu Nome", email: "meu@email.com", bairro: "Centro", cidade: "" };
  const campos = camposParaFormulario(
    { ...mapearRespostaBrasilApi(RESPOSTA)!, email: null, bairro: null, cidade: "BRASILIA" },
    UFS,
  );
  const depois = { ...digitado, ...(campos.nome ? { nome: campos.nome } : {}), ...(campos.email ? { email: campos.email } : {}), ...(campos.bairro ? { bairro: campos.bairro } : {}), ...(campos.cidade ? { cidade: campos.cidade } : {}) };
  assert.equal(depois.email, "meu@email.com");
  assert.equal(depois.bairro, "Centro");
  assert.equal(depois.cidade, "BRASILIA");
});

// ── consulta: sucesso e todas as falhas (fetch mockado) ──────────────────────────────────────────────
test("consultarCnpj: com e sem máscara chamam a MESMA URL do BFF e devolvem os dados", async () => {
  const urls: string[] = [];
  const fetchImpl = async (url: string) => {
    urls.push(url);
    return respostaJson(200, { dados: mapearRespostaBrasilApi(RESPOSTA) });
  };
  const a = await consultarCnpj(CNPJ, { fetchImpl });
  const b = await consultarCnpj(CNPJ_MASCARA, { fetchImpl });
  assert.deepEqual(urls, [`/api/consulta/cnpj/${CNPJ}`, `/api/consulta/cnpj/${CNPJ}`]);
  assert.ok(a.ok && b.ok && a.dados.razaoSocial === "BANCO DO BRASIL SA");
});

test("CNPJ inválido (e CPF) nem chega ao fetch", async () => {
  let chamadas = 0;
  const fetchImpl = async () => {
    chamadas += 1;
    return respostaJson(200, {});
  };
  for (const ruim of ["", "123", "12345678901", "111.444.777-35", "00000000000192"]) {
    const r = await consultarCnpj(ruim, { fetchImpl });
    assert.ok(!r.ok && r.falha === "invalido", ruim);
  }
  assert.equal(chamadas, 0);
});

test("404, 429, 5xx, rede e timeout viram falhas claras (sem lançar) e o formulário pode seguir manual", async () => {
  const caso = async (fetchImpl: (u: string, i?: RequestInit) => Promise<Response>, timeoutMs?: number) =>
    consultarCnpj(CNPJ, { fetchImpl, timeoutMs });

  const r404 = await caso(async () => respostaJson(404, { falha: "nao_encontrado" }));
  assert.ok(!r404.ok && r404.falha === "nao_encontrado" && /Não foi possível localizar os dados desse CNPJ/.test(r404.mensagem));

  const r429 = await caso(async () => respostaJson(429, { falha: "limite" }));
  assert.ok(!r429.ok && r429.falha === "limite");

  const r500 = await caso(async () => respostaJson(502, { falha: "indisponivel" }));
  assert.ok(!r500.ok && r500.falha === "indisponivel");
  const r500puro = await caso(async () => new Response("<html>erro</html>", { status: 500 })); // corpo não-JSON: usa o status
  assert.ok(!r500puro.ok && r500puro.falha === "indisponivel");

  const rRede = await caso(async () => {
    throw new TypeError("Failed to fetch");
  });
  assert.ok(!rRede.ok && rRede.falha === "rede");

  const rTimeout = await caso(
    (_url, init) =>
      new Promise((_resolve, rejeitar) => {
        init?.signal?.addEventListener("abort", () => rejeitar(new DOMException("abortado", "AbortError")));
      }),
    20,
  );
  assert.ok(!rTimeout.ok && rTimeout.falha === "timeout");

  const rVazia = await caso(async () => respostaJson(200, { dados: {} })); // 200 sem nome nenhum
  assert.ok(!rVazia.ok && rVazia.falha === "nao_encontrado");

  for (const r of [r404, r429, r500, rRede, rTimeout]) assert.ok(!r.ok && !/stack|undefined|Error/.test(r.mensagem));
  assert.equal(falhaPorStatus(404), "nao_encontrado");
  assert.equal(falhaPorStatus(429), "limite");
  assert.equal(falhaPorStatus(503), "indisponivel");
  assert.equal(Object.keys(MENSAGENS_CONSULTA).length, 6);
});

// ── BrasilAPI: implementação ÚNICA, compartilhada, sem segredo ───────────────────────────────────────
test("Clientes e Fornecedores usam a MESMA lógica (hook + lib) e o stub falso foi removido", () => {
  for (const form of ["components/clientes/ClienteFormModal.tsx", "components/fornecedores/FornecedorFormModal.tsx"]) {
    const codigo = semComentarios(ler(form));
    assert.match(codigo, /useConsultaCnpj\(ufsDisponiveis\)/, form);
    assert.match(codigo, /cnpjValido\(draft\.documento\)/, form);
    assert.match(codigo, /consulta\.buscar\(draft\.documento/, form);
    assert.match(codigo, /draft\.tipoDocumento === "cnpj"/, form); // CPF nunca consulta o endpoint de CNPJ
    assert.match(codigo, /consulta\.aviso/, form);
    assert.doesNotMatch(codigo, /documento-lookup|buscarDadosPorDocumento|brasilapi\.com\.br/, form);
  }
  assert.throws(() => ler("lib/documento-lookup.ts")); // o stub que fabricava "Empresa NNNN" não existe mais
});

test("os formulários só preenchem campos que existem no rascunho e só com valor", () => {
  const cliente = semComentarios(ler("components/clientes/ClienteFormModal.tsx"));
  for (const campo of ["nome", "razaoSocial", "email", "cep", "bairro", "enderecoCompleto", "cidade", "uf"]) {
    assert.match(cliente, new RegExp(`\\.\\.\\.\\(${campo} \\? \\{ ${campo} \\} : \\{\\}\\)`), `cliente.${campo}`);
  }
  const fornecedor = semComentarios(ler("components/fornecedores/FornecedorFormModal.tsx"));
  for (const campo of ["nome", "email", "cep", "bairro", "enderecoCompleto", "cidade", "uf"]) {
    assert.match(fornecedor, new RegExp(`\\.\\.\\.\\(${campo} \\? \\{ ${campo} \\} : \\{\\}\\)`), `fornecedor.${campo}`);
  }
  assert.match(fornecedor, /\.\.\.\(telefone \? \{ whatsapp: telefone \} : \{\}\)/); // "WhatsApp / telefone"
  assert.doesNotMatch(cliente, /telefone \? \{/); // Cliente não tem campo de telefone: não adivinha
});

test("BFF da consulta: exige sessão, valida o CNPJ, tem timeout, não envia nem guarda dado do usuário e não tem segredo", () => {
  const rota = semComentarios(ler("app/api/consulta/cnpj/[cnpj]/route.ts"));
  const bff = semComentarios(ler("lib/server/brasilApiBff.ts")); // timeout/sessão/classificação compartilhados com o CEP
  assert.match(rota, /exigirSessaoTenant\(\)/);
  assert.match(bff, /SESSION_COOKIE_NAME/);
  assert.match(bff, /status: 401/);
  assert.match(rota, /cnpjValido\(digitos\)/);
  assert.match(bff, /AbortSignal\.timeout\(TIMEOUT_SERVIDOR_MS\)/);
  assert.match(bff, /timeout: 504/);
  assert.match(bff, /rede: 502/);
  for (const codigo of [rota, bff]) {
    assert.doesNotMatch(codigo, /process\.env|API_KEY|apikey|Authorization|token|secret|senha/i); // integração pública, sem segredo
    assert.doesNotMatch(codigo, /console\./);
  }
  // a URL externa vive num único lugar
  assert.match(ler("lib/brasilApi.ts"), /https:\/\/brasilapi\.com\.br\/api\/cnpj\/v1/);
});

// ── Gestor: UI e API ─────────────────────────────────────────────────────────────────────────────────
test("Definir Gestor: um modal com as duas opções, labels 'Usuário'/'Gestor' e senha única preservada", () => {
  const modal = ler("components/plataforma/DefinirGestorModal.tsx");
  assert.match(modal, /Escolher usuário existente/);
  assert.match(modal, /Criar novo Gestor/);
  assert.match(modal, /listarCandidatosGestor\(empresa\.id\)/);
  assert.match(modal, /promoverGestorEmpresa\(empresa\.id, escolhido\)/);
  assert.match(modal, /criarGestorEmpresa\(empresa\.id, \{ nome: nome\.trim\(\), email: email\.trim\(\) \}\)/);
  assert.match(modal, /uma única vez/);
  assert.match(modal, /setCriado\(null\)/); // fechar descarta a senha
  assert.doesNotMatch(semComentarios(modal), /operador|localStorage|sessionStorage|console\./);
  assert.doesNotMatch(semComentarios(modal), /perfilBase|type="password"/); // perfil e senha nunca vêm do formulário
  const secao = ler("components/plataforma/EmpresaUsuariosSection.tsx");
  assert.match(secao, /DefinirGestorModal/);
  assert.match(secao, /operador: perfilUsuarioLabels\.operador/); // exibido como "Usuário"
  assert.match(secao, /Adicionar Gestor/); // empresa com Gestor continua podendo adicionar outro
});

test("API de plataforma: candidatos e promoção por endpoints específicos (sem PATCH genérico de perfil)", () => {
  const api = ler("lib/plataforma-api.ts");
  assert.match(api, /\/candidatos-gestor/);
  assert.match(api, /\/usuarios\/\$\{encodeURIComponent\(usuarioId\)\}\/promover-gestor/);
  assert.doesNotMatch(api, /perfilBase/);
});

// ── Grupo ACME ───────────────────────────────────────────────────────────────────────────────────────
test("Grupo de Clientes: o exemplo visual é GRUPO ACME e nenhum BRETAS aparece na interface", () => {
  const view = ler("components/grupos-cliente/GruposClienteView.tsx");
  assert.match(view, /placeholder="Nome do novo grupo \(ex\.: GRUPO ACME\)"/);
  assert.doesNotMatch(view, /BRETAS/i);
});
