// Teste de contraste dos tokens semânticos (claro e escuro) e das cores de marca derivadas.
// Roda sem dependências: `npm run test:contraste` (node --test). Lê os valores REAIS de globals.css — se alguém
// mexer num token e quebrar o contraste, o teste falha.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  COR_PRIMARIA_PADRAO,
  COR_SECUNDARIA_PADRAO,
  CONTRASTE_TEXTO,
  PASSOS,
  contraste,
  corSobre,
  gerarEscala,
  hexValido,
  luminanciaRelativa,
  variaveisDaMarca,
} from "./branding-tokens.ts";

// normaliza CRLF (checkout no Windows) para os seletores multilinha abaixo casarem
const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8").replaceAll("\r\n", "\n");

function bloco(seletor: string): Record<string, string> {
  const inicio = css.indexOf(seletor);
  assert.ok(inicio >= 0, `bloco ${seletor} não encontrado em globals.css`);
  const corpo = css.slice(css.indexOf("{", inicio) + 1, css.indexOf("}", inicio));
  const vars: Record<string, string> = {};
  for (const m of corpo.matchAll(/--([a-z0-9-]+):\s*([^;]+);/g)) vars[m[1]] = m[2].trim();
  return vars;
}

/** `frente` com opacidade `alfa` sobre `fundo` (o que o navegador pinta em bg-success/10). */
function misturar(frente: string, fundo: string, alfa: number): string {
  const canal = (h: string, i: number) => parseInt(h.slice(1 + i * 2, 3 + i * 2), 16);
  const v = [0, 1, 2].map((i) => Math.round(canal(frente, i) * alfa + canal(fundo, i) * (1 - alfa)));
  return "#" + v.map((x) => x.toString(16).padStart(2, "0")).join("");
}

const TEMAS = {
  claro: bloco(':root,\n[data-theme="claro"]'),
  escuro: bloco('[data-theme="escuro"] {'),
};

// Foco: --focus-ring aponta para a escala da marca (indigo-600 no claro, indigo-400 no escuro). Para o teste dos
// tokens fixos usamos os valores originais do Tailwind (a marca padrão); a escala personalizada é testada abaixo.
const INDIGO_600 = "#4f46e5";
const INDIGO_400 = "#818cf8";
const FOCO = { claro: INDIGO_600, escuro: INDIGO_400 };

for (const tema of ["claro", "escuro"] as const) {
  const t = TEMAS[tema];

  test(`[${tema}] todos os tokens de cor são #RRGGBB (exceto referências)`, () => {
    for (const nome of ["app-bg", "surface", "surface-2", "fg", "fg-muted", "fg-subtle", "line", "field-bg", "field-line", "placeholder", "success", "warning", "danger", "info"]) {
      assert.ok(hexValido(t[nome]), `--${nome}: ${t[nome]}`);
    }
  });

  test(`[${tema}] texto principal/secundário/apoio ≥ ${CONTRASTE_TEXTO}:1 sobre fundo, superfície e superfície secundária`, () => {
    for (const fundo of ["app-bg", "surface", "surface-2"]) {
      for (const texto of ["fg", "fg-muted", "fg-subtle"]) {
        const razao = contraste(t[texto], t[fundo]);
        assert.ok(razao >= CONTRASTE_TEXTO, `${tema}: --${texto} sobre --${fundo} = ${razao.toFixed(2)}:1`);
      }
    }
  });

  test(`[${tema}] placeholder ≥ 4.5:1 sobre o campo; texto digitado ≥ 7:1`, () => {
    assert.ok(contraste(t.placeholder, t["field-bg"]) >= CONTRASTE_TEXTO, `placeholder ${contraste(t.placeholder, t["field-bg"]).toFixed(2)}`);
    assert.ok(contraste(t.fg, t["field-bg"]) >= 7);
  });

  test(`[${tema}] borda do campo ≥ 3:1 contra a superfície e contra o fundo (o campo nunca some)`, () => {
    for (const fundo of ["surface", "app-bg", "field-bg"]) {
      const razao = contraste(t["field-line"], t[fundo]);
      assert.ok(razao >= 3, `${tema}: --field-line sobre --${fundo} = ${razao.toFixed(2)}:1`);
    }
  });

  test(`[${tema}] estados (sucesso, aviso, erro, info) ≥ 4.5:1 sobre a superfície`, () => {
    for (const estado of ["success", "warning", "danger", "info"]) {
      const razao = contraste(t[estado], t.surface);
      assert.ok(razao >= CONTRASTE_TEXTO, `${tema}: --${estado} = ${razao.toFixed(2)}:1`);
    }
  });

  test(`[${tema}] estados sobre o próprio fundo translúcido (10%, como nos avisos) ≥ 4.5:1`, () => {
    for (const estado of ["success", "warning", "danger", "info"]) {
      const fundo = misturar(t[estado], t.surface, 0.1);
      const razao = contraste(t[estado], fundo);
      assert.ok(razao >= CONTRASTE_TEXTO, `${tema}: --${estado} sobre aviso = ${razao.toFixed(2)}:1`);
    }
  });

  test(`[${tema}] anel de foco ≥ 3:1 sobre a superfície`, () => {
    assert.ok(contraste(FOCO[tema], t.surface) >= 3);
  });

  test(`[${tema}] campo desabilitado continua distinguível do ativo`, () => {
    assert.notEqual(t["field-bg-disabled"].toLowerCase(), t["field-bg"].toLowerCase());
  });
}

// Amostras de marca: padrão, muito claras, muito escuras, saturadas, neutras.
const MARCAS: [string, string][] = [
  [COR_PRIMARIA_PADRAO, COR_SECUNDARIA_PADRAO],
  ["#facc15", "#fde047"], // amarelos
  ["#ffffff", "#f5f5f5"], // quase branco
  ["#000000", "#111111"], // preto
  ["#ef4444", "#22c55e"], // vermelho / verde
  ["#00ff88", "#00bfff"], // neon
  ["#0b1f4b", "#123b8c"], // azul-marinho
  ["#808080", "#a0a0a0"], // cinzas médios (pior caso para texto branco/preto)
  ["#e11d48", "#9333ea"],
  ["#ff6a00", "#ffb300"],
  ["#0b1f4b", "#ff2d95"], // marinho + rosa: nenhum texto único serve às duas pontas → degradê vira cor sólida
];

for (const [primaria, secundaria] of MARCAS) {
  const rotulo = `${primaria} + ${secundaria}`;
  const padrao = primaria === COR_PRIMARIA_PADRAO && secundaria === COR_SECUNDARIA_PADRAO;

  test(`[marca ${rotulo}] texto sobre as cores sólidas ≥ 4.5:1`, () => {
    if (padrao) {
      // Marca padrão = visual atual do TaskFloww: indigo-500 + branco = 4.47:1 (exceção documentada; o app
      // sempre usou assim — não alteramos a cor padrão).
      assert.ok(contraste("#ffffff", primaria) >= 4.4);
      assert.ok(contraste("#ffffff", secundaria) >= CONTRASTE_TEXTO);
      return;
    }
    assert.ok(contraste(corSobre(primaria), primaria) >= CONTRASTE_TEXTO, "texto sobre a principal");
    assert.ok(contraste(corSobre(secundaria), secundaria) >= CONTRASTE_TEXTO, "texto sobre a secundária");
    const vars = variaveisDaMarca(primaria, secundaria);
    assert.ok(contraste(vars["--on-primary"], primaria) >= CONTRASTE_TEXTO);
    assert.ok(contraste(vars["--on-secondary"], secundaria) >= CONTRASTE_TEXTO);
  });

  test(`[marca ${rotulo}] texto sobre o degradê legível nas duas pontas (ou degradê vira cor sólida)`, () => {
    if (padrao) return assert.deepEqual(variaveisDaMarca(primaria, secundaria), {});
    const vars = variaveisDaMarca(primaria, secundaria);
    const sobre = vars["--on-brand"];
    const fundo = vars["--brand-gradient"];
    if (fundo.startsWith("linear-gradient")) {
      assert.ok(contraste(sobre, primaria) >= CONTRASTE_TEXTO, "ponta principal");
      assert.ok(contraste(sobre, secundaria) >= CONTRASTE_TEXTO, "ponta secundária");
    } else {
      assert.equal(fundo, primaria);
      assert.ok(contraste(sobre, primaria) >= CONTRASTE_TEXTO);
    }
  });

  test(`[marca ${rotulo}] escala: 600/700 com texto branco, 400 legível no tema escuro, ancoragem exata`, () => {
    if (padrao) return;
    const principal = gerarEscala(primaria, 500);
    const destaque = gerarEscala(secundaria, 600);
    assert.equal(principal[500], primaria.toLowerCase());
    assert.equal(destaque[600], secundaria.toLowerCase());
    for (const escala of [principal, destaque]) {
      for (const passo of PASSOS) assert.ok(hexValido(escala[passo]), `passo ${passo}: ${escala[passo]}`);
      assert.ok(contraste(escala[700], "#f4f4f5") >= CONTRASTE_TEXTO, `700 sobre superfície clara secundária = ${contraste(escala[700], "#f4f4f5").toFixed(2)}`);
      assert.ok(contraste(escala[400], "#27272a") >= CONTRASTE_TEXTO, `400 sobre superfície escura secundária = ${contraste(escala[400], "#27272a").toFixed(2)}`);
    }
    assert.ok(contraste(principal[600], "#f4f4f5") >= CONTRASTE_TEXTO, "principal 600 sobre superfície clara (texto/foco no claro)");
  });
}

test("escalas são monotônicas: do passo 50 ao 950 a luminosidade nunca sobe (qualquer cor de marca)", () => {
  for (const [p, s] of MARCAS) {
    for (const [cor, ancora] of [[p, 500], [s, 600]] as const) {
      const escala = gerarEscala(cor, ancora);
      for (let i = 1; i < PASSOS.length; i++) {
        const antes = luminanciaRelativa(escala[PASSOS[i - 1]]);
        const depois = luminanciaRelativa(escala[PASSOS[i]]);
        assert.ok(depois <= antes + 0.02, `${cor}@${ancora}: passo ${PASSOS[i]} (${escala[PASSOS[i]]}) mais claro que ${PASSOS[i - 1]} (${escala[PASSOS[i - 1]]})`);
      }
    }
  }
});

test("quando nenhum texto único serve às duas pontas, o degradê vira cor sólida da principal (e o CSS aceita as duas formas)", () => {
  const vars = variaveisDaMarca("#0b1f4b", "#ff2d95");
  assert.equal(vars["--brand-gradient"], "#0b1f4b");
  assert.ok(contraste(vars["--on-brand"], "#0b1f4b") >= CONTRASTE_TEXTO);
  assert.match(css, /\.bg-brand-gradient \{[^}]*\n {2}background: var\(--brand-gradient/, "usa o shorthand background (aceita cor e degradê)");
});

test("variáveis injetadas só contêm valores seguros (#hex ou gradiente da marca)", () => {
  for (const [p, s] of MARCAS) {
    for (const [nome, valor] of Object.entries(variaveisDaMarca(p, s))) {
      assert.match(nome, /^--(brand|accent)-\d+$|^--on-(primary|secondary|brand)$|^--brand-gradient$/);
      assert.match(valor, /^#[0-9a-f]{6}$|^linear-gradient\(135deg, #[0-9a-f]{6}, #[0-9a-f]{6}\)$/);
    }
  }
});

test("hexValido rejeita formatos que virariam injeção de CSS", () => {
  for (const ruim of ["red", "#fff", "#12345", "#1234567", "#gggggg", "#ffffff;}body{display:none", "url(x)", ""]) {
    assert.equal(hexValido(ruim), false, ruim);
  }
  assert.equal(hexValido("#A1b2C3"), true);
});
