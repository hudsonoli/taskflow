// Fase 5 — consulta automática de CEP (BrasilAPI via BFF). `npm run test:cep` (node --test, sem dependências).
// A consulta é exercitada de verdade com `fetch` MOCKADO (nenhum teste usa a internet); rota, hook e formulário são lidos como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  MENSAGENS_CONSULTA_CEP,
  camposCepParaFormulario,
  cepValido,
  consultarCep,
  formatarCep,
  mapearRespostaBrasilApiCep,
} from "./brasilApi.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const UFS = ["SP", "RJ", "MG", "DF"];
const RESPOSTA = { cep: "01001000", state: "SP", city: "São Paulo", neighborhood: "Sé", street: "Praça da Sé", service: "open-cep" };
const ENDERECO = { logradouro: "Praça da Sé", bairro: "Sé", cidade: "São Paulo", uf: "SP" };

const json = (corpo: unknown, status = 200) => new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } });
function mock(resposta: () => Response | Promise<Response>) {
  const chamadas: string[] = [];
  return {
    chamadas,
    fetchImpl: async (entrada: string) => {
      chamadas.push(entrada);
      return resposta();
    },
  };
}

test("CEP: só é válido com 8 dígitos (com ou sem máscara) e a máscara é 00000-000", () => {
  assert.equal(cepValido("01001000"), true);
  assert.equal(cepValido("01001-000"), true);
  for (const ruim of ["", "0100", "01001-00", "010010000", "abcdefgh"]) assert.equal(cepValido(ruim), false, ruim);
  assert.equal(formatarCep("01001000"), "01001-000");
  assert.equal(formatarCep("01001-000"), "01001-000");
  assert.equal(formatarCep("0100"), "0100");
  assert.equal(formatarCep("01001"), "01001");
  assert.equal(formatarCep("010010009999"), "01001-000"); // no máximo 8 dígitos
  assert.equal(formatarCep("a1b0c0"), "100");
});

test("mapeamento: street/neighborhood/city/state viram logradouro/bairro/cidade/uf", () => {
  assert.deepEqual(mapearRespostaBrasilApiCep(RESPOSTA), ENDERECO);
  const parcial = mapearRespostaBrasilApiCep({ city: "Brasília", state: "df", street: null, neighborhood: "" });
  assert.deepEqual(parcial, { logradouro: null, bairro: null, cidade: "Brasília", uf: "DF" });
  for (const ruim of [null, undefined, "x", 42, [], {}, { street: "", city: "  " }]) assert.equal(mapearRespostaBrasilApiCep(ruim), null, String(ruim));
});

test("campos do formulário: só o que veio preenchido, nunca número/complemento, UF só se existir", () => {
  const campos = camposCepParaFormulario(ENDERECO, UFS);
  assert.deepEqual(Object.keys(campos).sort(), ["bairro", "cidade", "enderecoCompleto", "uf"]);
  assert.equal(campos.enderecoCompleto, "Praça da Sé"); // só a rua: o número a pessoa digita
  assert.equal(/\d/.test(campos.enderecoCompleto ?? ""), false);
  // null/vazio da API NUNCA apaga o que a pessoa digitou
  assert.deepEqual(camposCepParaFormulario({ logradouro: null, bairro: null, cidade: "Brasília", uf: null }, UFS), { cidade: "Brasília" });
  assert.deepEqual(camposCepParaFormulario({ logradouro: null, bairro: null, cidade: null, uf: null }, UFS), {});
  assert.equal("uf" in camposCepParaFormulario({ ...ENDERECO, uf: "ZZ" }, UFS), false);
});

test("CEP incompleto/inválido nem chama a rede", async () => {
  const m = mock(() => json({ dados: ENDERECO }));
  for (const ruim of ["", "0100", "01001-00", "abc"]) {
    const r = await consultarCep(ruim, { fetchImpl: m.fetchImpl });
    assert.equal(r.ok, false);
    assert.equal(!r.ok && r.falha, "invalido");
    assert.equal(!r.ok && r.mensagem, MENSAGENS_CONSULTA_CEP.invalido);
  }
  assert.equal(m.chamadas.length, 0);
});

test("CEP com e sem máscara chamam o mesmo caminho do BFF e devolvem o endereço", async () => {
  const m = mock(() => json({ dados: ENDERECO }));
  for (const cep of ["01001000", "01001-000"]) {
    const r = await consultarCep(cep, { fetchImpl: m.fetchImpl });
    assert.deepEqual(r.ok && r.dados, ENDERECO);
  }
  assert.deepEqual(m.chamadas, ["/api/consulta/cep/01001000", "/api/consulta/cep/01001000"]);
});

test("falhas do BFF viram falha normalizada com mensagem e o cadastro segue manual", async () => {
  const casos: Array<[number, string, string | null]> = [
    [404, "nao_encontrado", "nao_encontrado"],
    [429, "limite", "limite"],
    [500, "indisponivel", null],
    [502, "indisponivel", null],
    [503, "indisponivel", null],
    [504, "timeout", "timeout"],
  ];
  for (const [status, esperada, corpoFalha] of casos) {
    const m = mock(() => json(corpoFalha ? { falha: corpoFalha } : { message: "x" }, status));
    const r = await consultarCep("01001000", { fetchImpl: m.fetchImpl });
    assert.equal(r.ok, false, String(status));
    assert.equal(!r.ok && r.falha, esperada, String(status));
    assert.equal(!r.ok && r.mensagem, MENSAGENS_CONSULTA_CEP[esperada as keyof typeof MENSAGENS_CONSULTA_CEP]);
  }
  // toda mensagem de falha orienta o preenchimento manual (exceto "inválido", que pede o CEP completo)
  for (const [falha, mensagem] of Object.entries(MENSAGENS_CONSULTA_CEP)) {
    if (falha !== "invalido" && falha !== "limite") assert.match(mensagem, /manualmente/i, falha);
    if (falha === "limite") assert.match(mensagem, /manualmente/i);
  }
});

test("corpo 200 sem endereço utilizável e corpo ilegível não quebram: viram 'não encontrado'", async () => {
  for (const corpo of [{ dados: null }, { dados: {} }, { dados: { logradouro: " ", cidade: null } }, {}]) {
    const r = await consultarCep("01001000", { fetchImpl: mock(() => json(corpo)).fetchImpl });
    assert.equal(!r.ok && r.falha, "nao_encontrado", JSON.stringify(corpo));
  }
  const ilegivel = await consultarCep("01001000", { fetchImpl: mock(() => new Response("<html>", { status: 200 })).fetchImpl });
  assert.equal(!ilegivel.ok && ilegivel.falha, "nao_encontrado");
});

test("timeout do cliente aborta a requisição; falha de rede vira 'rede' (nunca lança)", async () => {
  let abortou = false;
  const lento = (_entrada: string, init?: RequestInit) =>
    new Promise<Response>((_, rejeitar) => {
      init?.signal?.addEventListener("abort", () => {
        abortou = true;
        rejeitar(Object.assign(new Error("abortado"), { name: "AbortError" }));
      });
    });
  const r = await consultarCep("01001000", { fetchImpl: lento, timeoutMs: 20 });
  assert.equal(!r.ok && r.falha, "timeout");
  assert.equal(abortou, true);

  const sem = await consultarCep("01001000", {
    fetchImpl: async () => {
      throw new TypeError("Failed to fetch");
    },
  });
  assert.equal(!sem.ok && sem.falha, "rede");
});

test("BFF do CEP: exige sessão, valida 8 dígitos, usa o serviço público sem segredo e reaproveita a infra do CNPJ", () => {
  const rota = semComentarios(ler("app/api/consulta/cep/[cep]/route.ts"));
  const bff = semComentarios(ler("lib/server/brasilApiBff.ts"));
  assert.match(rota, /exigirSessaoTenant\(\)/);
  assert.match(rota, /cepValido\(digitos\)/);
  assert.match(rota, /URL_BRASILAPI_CEP/);
  assert.match(rota, /mapearRespostaBrasilApiCep/);
  assert.match(bff, /AbortSignal\.timeout\(TIMEOUT_SERVIDOR_MS\)/);
  assert.match(bff, /"User-Agent": USER_AGENT_CONSULTA/);
  assert.match(ler("lib/brasilApi.ts"), /https:\/\/brasilapi\.com\.br\/api\/cep\/v2/);
  assert.doesNotMatch(rota, /process\.env|API_KEY|apikey|Authorization|token|secret|senha/i); // CEP_SECRET: nenhum
  assert.doesNotMatch(rota, /console\./);
});

test("hook: só consulta com CEP completo, debounce, descarta resposta atrasada e nunca bloqueia o preenchimento manual", () => {
  const hook = semComentarios(ler("lib/useConsultaCep.ts"));
  assert.match(hook, /cepValido\(cep\)/);
  assert.match(hook, /DEBOUNCE_MS/);
  assert.match(hook, /setTimeout/);
  assert.match(hook, /minha !== sequencia\.current/); // resposta de CEP anterior é ignorada
  assert.match(hook, /ultimoConsultado/); // não repete a mesma consulta
  assert.match(hook, /camposCepParaFormulario\(resultado\.dados, ufsValidas\)/);
  assert.doesNotMatch(hook, /alert\(|toast|confirm\(|disabled/i); // sem modal/toast/bloqueio
});

test("formulário de Usuário (criação e edição): máscara do CEP + preenchimento automático, sem tocar em número/complemento", () => {
  const form = ler("components/usuarios/UsuarioFormModal.tsx");
  assert.match(form, /useConsultaCep\(ufsDisponiveis\)/);
  assert.match(form, /formatarCep\(event\.target\.value\)/);
  assert.match(form, /consultaCep\.agendar\(cep, updateDraft\)/);
  assert.match(form, /role=\{consultaCep\.aviso\.tipo === "erro" \? "alert" : "status"\}/);
  // o mesmo modal serve à criação e à edição (`usuario` opcional) e a consulta só dispara ao DIGITAR (não ao abrir)
  assert.match(form, /const editing = usuario !== undefined/);
  assert.equal((form.match(/consultaCep\.agendar/g) ?? []).length, 1);
});
