// Precedência do tema (empresa × usuário × sistema), acompanhamento de prefers-color-scheme em tempo de execução,
// rollback da troca otimista e isolamento no logout. Sem dependências: `npm run test:tema` (node --test).
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  SCRIPT_TEMA_SISTEMA,
  normalizarPreferencia,
  observarSistemaEscuro,
  resolveEffectiveTheme,
  temaPreferenciaValido,
  trocarPreferencia,
  type ConsultaMidia,
  type TemaPreferencia,
  type TemaVisual,
} from "./tema.ts";

const casos: [TemaVisual, TemaPreferencia, boolean, TemaVisual][] = [
  // empresa, preferência, sistema escuro?, esperado
  ["claro", null, false, "claro"],
  ["escuro", null, false, "escuro"],
  ["claro", null, true, "claro"], // sem override o dispositivo NÃO interfere
  ["escuro", null, true, "escuro"],
  ["claro", "escuro", false, "escuro"],
  ["escuro", "claro", true, "claro"],
  ["claro", "claro", true, "claro"],
  ["escuro", "escuro", false, "escuro"],
  ["claro", "sistema", true, "escuro"],
  ["claro", "sistema", false, "claro"],
  ["escuro", "sistema", true, "escuro"],
  ["escuro", "sistema", false, "claro"], // sistema ignora o padrão da empresa
];

for (const [temaEmpresa, preferencia, sistemaEscuro, esperado] of casos) {
  test(`empresa ${temaEmpresa} + preferência ${preferencia ?? "NULL"} + SO ${sistemaEscuro ? "escuro" : "claro"} → ${esperado}`, () => {
    assert.equal(resolveEffectiveTheme({ temaEmpresa, preferencia, sistemaEscuro }), esperado);
  });
}

test("sem usuário autenticado (ou página pública) vale sempre o tema da empresa — logout remove o override efetivo", () => {
  for (const preferencia of ["claro", "escuro", "sistema", null] as TemaPreferencia[]) {
    for (const sistemaEscuro of [true, false]) {
      for (const temaEmpresa of ["claro", "escuro"] as TemaVisual[]) {
        assert.equal(resolveEffectiveTheme({ temaEmpresa, preferencia, sistemaEscuro, autenticado: false }), temaEmpresa);
      }
    }
  }
});

test("preferência inválida vinda de fora vira null (herdar a empresa)", () => {
  for (const ruim of ["azul", "", "CLARO", 1, undefined, {}, ["claro"]]) assert.equal(normalizarPreferencia(ruim), null);
  for (const bom of ["claro", "escuro", "sistema"]) assert.equal(normalizarPreferencia(bom), bom);
  assert.equal(temaPreferenciaValido("empresa"), false);
});

// ---------------------------------------------------------------- matchMedia em tempo de execução
function midiaFalsa(inicial: boolean) {
  const ouvintes = new Set<(e: { matches: boolean }) => void>();
  const midia: ConsultaMidia & { disparar: (escuro: boolean) => void; ouvintes: Set<unknown> } = {
    matches: inicial,
    addEventListener: (_tipo, o) => void ouvintes.add(o),
    removeEventListener: (_tipo, o) => void ouvintes.delete(o),
    disparar(escuro) {
      midia.matches = escuro;
      for (const o of [...ouvintes]) o({ matches: escuro });
    },
    ouvintes,
  };
  return midia;
}

test("sistema: acompanha a mudança do SO em tempo de execução, sem polling, e remove o listener no cleanup", () => {
  const midia = midiaFalsa(false);
  let temaEmpresa: TemaVisual = "escuro";
  let efetivo: TemaVisual | null = null;
  const cleanup = observarSistemaEscuro(midia, (escuro) => {
    efetivo = resolveEffectiveTheme({ temaEmpresa, preferencia: "sistema", sistemaEscuro: escuro });
  });
  assert.equal(efetivo, "claro"); // valor inicial já aplicado
  midia.disparar(true);
  assert.equal(efetivo, "escuro");
  midia.disparar(false);
  assert.equal(efetivo, "claro");
  assert.equal(midia.ouvintes.size, 1);
  cleanup();
  assert.equal(midia.ouvintes.size, 0, "listener removido");
  midia.disparar(true);
  assert.equal(efetivo, "claro", "depois do cleanup o SO não mexe mais");
  temaEmpresa = "claro";
});

// ---------------------------------------------------------------- troca otimista + rollback
test("troca: aplica na hora, persiste e mantém", async () => {
  const aplicados: TemaPreferencia[] = [];
  let persistido: TemaPreferencia | undefined;
  await trocarPreferencia({
    anterior: null,
    nova: "escuro",
    aplicar: (p) => aplicados.push(p),
    persistir: async (p) => {
      assert.deepEqual(aplicados, ["escuro"], "a UI já mudou ANTES da resposta do servidor");
      persistido = p;
    },
  });
  assert.deepEqual(aplicados, ["escuro"]);
  assert.equal(persistido, "escuro");
});

test("troca: se o PATCH falha, restaura a preferência anterior e relança o erro", async () => {
  const aplicados: TemaPreferencia[] = [];
  await assert.rejects(
    trocarPreferencia({
      anterior: "claro",
      nova: "sistema",
      aplicar: (p) => aplicados.push(p),
      persistir: async () => {
        throw new Error("503");
      },
    }),
    /503/,
  );
  assert.deepEqual(aplicados, ["sistema", "claro"]);
});

test("'Usar padrão da empresa' persiste null e volta a herdar (rollback também volta ao override anterior)", async () => {
  const aplicados: TemaPreferencia[] = [];
  await trocarPreferencia({ anterior: "escuro", nova: null, aplicar: (p) => aplicados.push(p), persistir: async (p) => assert.equal(p, null) });
  assert.deepEqual(aplicados, [null]);
  assert.equal(resolveEffectiveTheme({ temaEmpresa: "claro", preferencia: aplicados[0], sistemaEscuro: true }), "claro");

  const falhou: TemaPreferencia[] = [];
  await assert.rejects(
    trocarPreferencia({ anterior: "escuro", nova: null, aplicar: (p) => falhou.push(p), persistir: async () => Promise.reject(new Error("x")) }),
  );
  assert.deepEqual(falhou, [null, "escuro"]);
});

test("script anti-flash do 'sistema' só lê prefers-color-scheme (nada sensível) e só grava data-theme", () => {
  assert.match(SCRIPT_TEMA_SISTEMA, /prefers-color-scheme: dark/);
  assert.match(SCRIPT_TEMA_SISTEMA, /setAttribute\("data-theme"/);
  for (const proibido of ["cookie", "localStorage", "sessionStorage", "fetch", "XMLHttpRequest", "token"]) assert.ok(!SCRIPT_TEMA_SISTEMA.includes(proibido), proibido);
  // executa de verdade num DOM mínimo
  for (const escuro of [true, false]) {
    const attrs: Record<string, string> = {};
    const fake = {
      document: { documentElement: { setAttribute: (k: string, v: string) => void (attrs[k] = v) } },
      window: { matchMedia: () => ({ matches: escuro }) },
    };
    new Function("document", "window", SCRIPT_TEMA_SISTEMA)(fake.document, fake.window);
    assert.equal(attrs["data-theme"], escuro ? "escuro" : "claro");
  }
});
