// P1_GLASS_CALENDAR_THEME — estilo visual (default | glass), DateField e superfícies de data. `npm run test:glass-calendar`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import {
  ATRIBUTO_ESTILO_VISUAL,
  CHAVE_ESTILO_VISUAL,
  ESTILO_VISUAL_PADRAO,
  ESTILOS_VISUAIS,
  estiloVisualValido,
  normalizarEstiloVisual,
  ROTULOS_ESTILO_VISUAL,
  SCRIPT_ESTILO_VISUAL,
} from "./estilo-visual.ts";
import { diaForaDoIntervalo, interpretarData, MENSAGEM_DATA_INVALIDA, montarGrade, parseDataBr, somarMeses } from "./data-hora-campo.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (codigo: string) => codigo.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");

// ── modelo do estilo ────────────────────────────────────────────────────────────────────────────────────────────

test("o estilo visual é um eixo próprio (default | glass), com padrão 'default' — nunca um terceiro tema de cor", () => {
  assert.deepEqual([...ESTILOS_VISUAIS], ["default", "glass"]);
  assert.equal(ESTILO_VISUAL_PADRAO, "default");
  assert.equal(ATRIBUTO_ESTILO_VISUAL, "data-visual-style");
  assert.notEqual(ATRIBUTO_ESTILO_VISUAL, "data-theme");
  assert.deepEqual(ROTULOS_ESTILO_VISUAL, { default: "Padrão", glass: "Glass" });
  const tema = semComentarios(ler("lib/tema.ts"));
  assert.doesNotMatch(tema, /glass/i); // os modos de cor continuam sendo só claro/escuro/sistema
});

test("normalização: valor desconhecido, nulo ou adulterado cai no padrão", () => {
  assert.equal(normalizarEstiloVisual("glass"), "glass");
  assert.equal(normalizarEstiloVisual("default"), "default");
  for (const ruim of [null, undefined, "", "Glass", "GLASS", "neon", 1, {}, "claro"]) assert.equal(normalizarEstiloVisual(ruim), "default", String(ruim));
  assert.equal(estiloVisualValido("glass"), true);
  assert.equal(estiloVisualValido("claro"), false);
});

test("persistência só no navegador: chave 'taskflow.*' no localStorage e nada de servidor/banco", () => {
  assert.equal(CHAVE_ESTILO_VISUAL, "taskflow.estilo-visual");
  assert.match(CHAVE_ESTILO_VISUAL, /^taskflow\.[a-z-]+$/); // grafia oficial do produto
  for (const arquivo of ["lib/estilo-visual.ts", "lib/useEstiloVisual.ts"]) {
    const codigo = semComentarios(ler(arquivo));
    assert.doesNotMatch(codigo, /fetch\(|api-backend|cookies?\(|document\.cookie/, arquivo);
  }
});

test("script pré-paint: lê o localStorage, grava data-visual-style antes da hidratação e cai no padrão sem armazenamento", () => {
  const atributos = new Map<string, string>();
  const documento = { documentElement: { setAttribute: (nome: string, valor: string) => atributos.set(nome, valor) } };
  const executar = (armazenamento: unknown) => {
    atributos.clear();
    new Function("document", "localStorage", SCRIPT_ESTILO_VISUAL)(documento, armazenamento);
    return atributos.get("data-visual-style");
  };
  assert.equal(executar({ getItem: () => "glass" }), "glass");
  assert.equal(executar({ getItem: () => "default" }), "default");
  assert.equal(executar({ getItem: () => null }), "default");
  assert.equal(executar({ getItem: () => "valor-estranho" }), "default");
  assert.equal(executar({ getItem: () => { throw new Error("bloqueado"); } }), "default"); // navegação privada / armazenamento bloqueado
  assert.doesNotMatch(SCRIPT_ESTILO_VISUAL, /fetch|XMLHttpRequest|cookie/);
});

test("hidratação: o layout emite o script e NÃO renderiza o atributo em JSX (sem mismatch nem flash Padrão → Glass)", () => {
  const layout = semComentarios(ler("app/layout.tsx"));
  assert.match(layout, /SCRIPT_ESTILO_VISUAL/);
  assert.match(layout, /<script dangerouslySetInnerHTML=\{\{ __html: SCRIPT_ESTILO_VISUAL \}\} \/>/);
  assert.doesNotMatch(layout, /data-visual-style/); // o servidor não conhece o estilo; só o script/hook gravam o atributo
  assert.match(layout, /suppressHydrationWarning/);
  const hook = semComentarios(ler("lib/useEstiloVisual.ts"));
  assert.match(hook, /useSyncExternalStore\(assinar, lerAtributo, \(\) => ESTILO_VISUAL_PADRAO\)/); // snapshot de servidor = padrão
});

test("o controle fica no menu do perfil (seção Estilo: Padrão | Glass), sem toggle permanente na barra principal", () => {
  const menu = semComentarios(ler("components/layout/ProfileMenu.tsx"));
  assert.match(menu, /titulo="Estilo"/);
  assert.match(menu, /useEstiloVisual\(\)/);
  assert.match(menu, /role="radiogroup" aria-labelledby="menu-estilo-rotulo"/);
  for (const arquivo of ["components/layout/TopNav.tsx", "components/layout/AppShell.tsx"]) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /useEstiloVisual/, arquivo);
  }
});

// ── tokens e CSS ────────────────────────────────────────────────────────────────────────────────────────────────

const css = ler("app/globals.css");
const blocoGlass = css.slice(css.indexOf("/* ── Estilo visual Glass"));

test("tokens Glass centralizados: todos definidos, nos dois modos de cor", () => {
  for (const token of ["surface", "surface-hover", "border", "shadow", "blur", "text", "muted", "selected", "selected-text", "today", "focus", "navigation", "overlay"]) {
    assert.match(blocoGlass, new RegExp(`--glass-${token}:`), `--glass-${token}`);
  }
  for (const token of ["surface", "surface-hover", "border", "shadow", "today", "navigation", "overlay"]) {
    const claro = /\[data-visual-style="glass"\]\[data-theme="claro"\] \{([\s\S]*?)\n\}/.exec(blocoGlass)?.[1] ?? "";
    const escuro = /\[data-visual-style="glass"\]\[data-theme="escuro"\] \{([\s\S]*?)\n\}/.exec(blocoGlass)?.[1] ?? "";
    assert.match(claro, new RegExp(`--glass-${token}:`), `claro ${token}`);
    assert.match(escuro, new RegExp(`--glass-${token}:`), `escuro ${token}`);
  }
});

test("Glass só existe sob o atributo global (o padrão não muda) e funciona sem imagem externa", () => {
  const regras = blocoGlass.replace(/\/\*[\s\S]*?\*\//g, "");
  const seletores = regras.split("{").slice(0, -1).map((trecho) => trecho.split("}").pop()!.trim()).filter((s) => s && !s.startsWith("@") && !s.startsWith("from") && !s.startsWith("to"));
  assert.ok(seletores.length > 10);
  for (const seletor of seletores) assert.match(seletor, /\[data-visual-style="glass"\]/, seletor); // nenhuma regra Glass vaza para o estilo padrão
  assert.doesNotMatch(blocoGlass, /url\(|https?:|unsplash|21st|@import/i); // sem CDN, imagem de fundo ou fonte remota
  assert.doesNotMatch(css.slice(0, css.indexOf("/* ── Estilo visual Glass")), /data-visual-style/); // o resto do CSS não conhece o estilo
});

test("modo claro não depende de texto branco fixo: texto/mudo/seleção vêm de tokens (só o fallback da marca é #fff)", () => {
  const regras = blocoGlass.replace(/\/\*[\s\S]*?\*\//g, "");
  assert.doesNotMatch(regras, /(?<!-)color:\s*(#fff\b|#ffffff\b|white)/i);
  assert.match(regras, /--glass-text: var\(--fg\)/);
  assert.match(regras, /--glass-muted: var\(--fg-muted\)/);
  assert.match(regras, /--glass-selected-text: var\(--on-brand, #ffffff\)/); // texto sobre a marca: o mesmo token já validado por contraste
});

test("acessibilidade: anel de foco próprio, 'Hoje' com marcador além da cor, opaco sem blur/com 'reduzir transparência', movimento só quando permitido", () => {
  assert.match(blocoGlass, /\[data-cal="dia"\]:focus-visible[\s\S]*?outline: 2px solid var\(--glass-focus\)/);
  assert.match(blocoGlass, /\[data-cal="dia"\]\[data-hoje\]::after/); // pontinho
  assert.match(blocoGlass, /\[data-hoje\]:not\(\[data-selecionado\]\) \{\s*box-shadow: inset/); // anel
  assert.match(blocoGlass, /@supports not \(\(backdrop-filter: blur\(1px\)\)/);
  assert.match(blocoGlass, /@media \(prefers-reduced-transparency: reduce\)/);
  assert.match(blocoGlass, /@media \(prefers-reduced-motion: no-preference\) \{\s*\[data-visual-style="glass"\] \[data-superficie="calendario"\] \{\s*animation:/);
});

test("a marca da empresa participa da seleção (gradiente da marca + texto sobre a marca), sem rosa/neon fixo", () => {
  assert.match(blocoGlass, /--glass-selected: var\(--brand-gradient,/);
  assert.doesNotMatch(blocoGlass.replace(/\/\*[\s\S]*?\*\//g, ""), /(pink|rose|fuchsia)|#ff(?!ffff)[0-9a-f]{4}/i); // (#ffffff é só o fallback do texto sobre a marca)
});

// ── componentes: sem estilo Glass embutido, só ganchos ─────────────────────────────────────────────────────────

test("Calendario/DateTimeField/DateField não carregam classe Glass: só ganchos data-* (o estilo vem do CSS global)", () => {
  for (const arquivo of ["components/ui/Calendario.tsx", "components/ui/DateTimeField.tsx", "components/ui/DateField.tsx"]) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /backdrop-blur|glass|bg-gradient/i, arquivo);
  }
  const calendario = semComentarios(ler("components/ui/Calendario.tsx"));
  for (const gancho of ['data-cal="titulo"', 'data-cal="nav"', 'data-cal="semana"', 'data-cal="dia"', 'data-cal="rodape"', 'data-cal="acao"']) assert.ok(calendario.includes(gancho), gancho);
  assert.match(calendario, /aria-current=\{ehHoje \? "date" : undefined\}/);
  assert.match(calendario, /aria-selected=\{escolhido\}/);
  for (const arquivo of ["components/ui/DateTimeField.tsx", "components/ui/DateField.tsx"]) {
    assert.match(semComentarios(ler(arquivo)), /superficie="calendario"/, arquivo);
  }
  assert.match(semComentarios(ler("components/filtros/PainelFlutuante.tsx")), /data-superficie=\{superficie \?\? "painel"\}/);
});

test("DateField reaproveita Calendario + PainelFlutuante e a hora NÃO entra no calendário", () => {
  const campo = semComentarios(ler("components/ui/DateField.tsx"));
  assert.match(campo, /import \{ PainelFlutuante \} from "@\/components\/filtros\/PainelFlutuante";/);
  assert.match(campo, /import \{ Calendario \} from "\.\/Calendario";/);
  assert.match(campo, /placeholder="DD\/MM\/AAAA"/);
  assert.match(campo, /inputMode="numeric"/);
  assert.doesNotMatch(campo, /type="date"|type="time"|type="datetime-local"|HH:MM|<select/);
  assert.doesNotMatch(semComentarios(ler("components/ui/Calendario.tsx")), /(?<![-\w])(horas?|minutos?)(?![-\w])|HH:MM/i);
});

test("nenhuma dependência nova: calendário/vidro sem biblioteca de data nem de UI", () => {
  const pacote = JSON.parse(readFileSync(new URL("../../package.json", import.meta.url), "utf8")) as { dependencies: Record<string, string> };
  for (const proibida of ["date-fns", "dayjs", "react-day-picker", "react-datepicker", "luxon", "moment", "@radix-ui/react-popover", "class-variance-authority", "tailwind-merge"]) {
    assert.equal(proibida in pacote.dependencies, false, proibida);
  }
});

// ── regras do DateField ────────────────────────────────────────────────────────────────────────────────────────

test("interpretarData: mesma semântica do input date nativo (completa e válida → ISO; vazio/parcial/inválido → '')", () => {
  assert.deepEqual(interpretarData("21/10/2026"), { valor: "2026-10-21", erro: null });
  assert.deepEqual(interpretarData("1/2/2026"), { valor: "2026-02-01", erro: null });
  assert.deepEqual(interpretarData(""), { valor: "", erro: null });
  assert.deepEqual(interpretarData("   "), { valor: "", erro: null });
  for (const parcial of ["21", "21/10", "21/10/20", "31/02/2026", "00/01/2026", "21/13/2026"]) {
    assert.deepEqual(interpretarData(parcial), { valor: "", erro: MENSAGEM_DATA_INVALIDA }, parcial);
  }
  assert.equal(parseDataBr("29/02/2028"), "2028-02-29"); // bissexto
  assert.equal(parseDataBr("29/02/2026"), null);
});

test("min/max: dias fora do intervalo ficam inertes; o limite em si é permitido; sem limites nada é bloqueado", () => {
  assert.equal(diaForaDoIntervalo("2026-10-10", "2026-10-11"), true);
  assert.equal(diaForaDoIntervalo("2026-10-11", "2026-10-11"), false);
  assert.equal(diaForaDoIntervalo("2026-10-12", "2026-10-11", "2026-10-12"), false);
  assert.equal(diaForaDoIntervalo("2026-10-13", "2026-10-11", "2026-10-12"), true);
  assert.equal(diaForaDoIntervalo("2026-10-13"), false);
  assert.equal(diaForaDoIntervalo("2026-10-13", undefined, undefined), false);
  assert.equal(diaForaDoIntervalo("2026-10-13", "", ""), false);
});

test("calendário: virada de ano, fevereiro e ano bissexto continuam corretos", () => {
  assert.equal(somarMeses("2026-12-15", 1), "2027-01-15");
  assert.equal(somarMeses("2027-01-15", -1), "2026-12-15");
  const fev2028 = montarGrade(2028, 2).flat().filter((d) => d.doMes);
  const fev2026 = montarGrade(2026, 2).flat().filter((d) => d.doMes);
  assert.equal(fev2028.length, 29);
  assert.equal(fev2026.length, 28);
});

// ── superfícies migradas ───────────────────────────────────────────────────────────────────────────────────────

const MIGRADAS = [
  "components/demandas/PlanejamentoEtapa.tsx",
  "components/projetos/NovoProjetoModal.tsx",
  "components/projetos/ProjetoFormSections.tsx",
  "components/regra-expediente/DiasEspeciaisSection.tsx",
  "components/usuarios/capacidade/UsuarioAusenciaModal.tsx",
  "components/usuarios/UsuarioFormModal.tsx",
];

test("superfícies de data-only migradas para o DateField: nenhuma usa mais input type=date nativo", () => {
  for (const arquivo of MIGRADAS) {
    const codigo = semComentarios(ler(arquivo));
    assert.doesNotMatch(codigo, /type="date"/, arquivo);
    assert.match(codigo, /<DateField/, arquivo);
    assert.match(codigo, /import \{ DateField \} from "@\/components\/ui\/DateField";/, arquivo);
  }
});

test("contratos preservados nas migrações: DATE 'YYYY-MM-DD' sem UTC, planejamento nullable e ausência com min", () => {
  const plan = semComentarios(ler("components/demandas/PlanejamentoEtapa.tsx"));
  assert.match(plan, /rotuloAcessivel=\{`Planejado de, etapa \$\{etapa\.nome\}`\}/);
  assert.match(plan, /onChange=\{setInicio\}/);
  assert.match(plan, /onChange=\{setFim\}/);
  assert.match(plan, /salvarPlanejamento\(atual, \{ inicio, fim \}/); // o caminho de salvar não mudou
  const ausencia = semComentarios(ler("components/usuarios/capacidade/UsuarioAusenciaModal.tsx"));
  assert.match(ausencia, /min=\{draft\.inicio \|\| undefined\}/);
  for (const arquivo of MIGRADAS) assert.doesNotMatch(semComentarios(ler(arquivo)), /toISOString|getTimezoneOffset/, arquivo); // nenhuma conversão de fuso nas migrações
});

test("time-only (regra de expediente) e o filtro de período NÃO foram migrados — decisão consciente desta fase", () => {
  for (const arquivo of ["components/regra-expediente/PeriodosDoDia.tsx", "components/regra-expediente/RegraExpedienteView.tsx"]) {
    assert.match(semComentarios(ler(arquivo)), /type="time"/, arquivo);
  }
  assert.match(semComentarios(ler("components/filtros/FiltroPainelData.tsx")), /type="date"/); // painel já flutuante: calendário aninhado fica para outra fase
});

test("timezone: nenhuma mudança de semântica (Prazo atual ISO/Z; Retorno até local cru)", () => {
  const form = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
  assert.match(form, /inputLocalParaIso\(valor\)/);
  const envio = semComentarios(ler("components/demandas/EnvioClienteCard.tsx"));
  assert.match(envio, /prazoRetornoCliente: prazoRetorno,/);
  assert.doesNotMatch(envio, /inputLocalParaIso/);
});

// ── P1_GLASS_APP_THEME: Glass no app inteiro ────────────────────────────────────────────────────────────────────

const regrasGlass = blocoGlass.replace(/\/\*[\s\S]*?\*\//g, "");
const blocoApp = regrasGlass.slice(regrasGlass.indexOf("--glass-canvas"));

test("tokens do app: canvas, casca, painel, input, divisor, sombra, modal, scrim — nos dois modos de cor", () => {
  const claro = /\[data-visual-style="glass"\]\[data-theme="claro"\] \{([\s\S]*?)\n\}/g;
  const escuro = /\[data-visual-style="glass"\]\[data-theme="escuro"\] \{([\s\S]*?)\n\}/g;
  const juntar = (re: RegExp) => [...regrasGlass.matchAll(re)].map((m) => m[1]).join("\n");
  for (const token of ["canvas", "shell", "panel", "panel-2", "nested", "input", "input-disabled", "divider", "divider-strong", "hover", "card-shadow", "modal-surface", "scrim", "sticky"]) {
    assert.match(juntar(claro), new RegExp(`--glass-${token}:`), `claro ${token}`);
    assert.match(juntar(escuro), new RegExp(`--glass-${token}:`), `escuro ${token}`);
  }
});

test("canvas só com CSS interno: gradientes radiais com a cor da empresa (sem imagem, sem wallpaper), sutil no claro e um pouco mais no escuro", () => {
  const juntarBlocos = (tema: string) =>
    [...regrasGlass.matchAll(new RegExp(`\\[data-visual-style="glass"\\]\\[data-theme="${tema}"\\] \\{([\\s\\S]*?)\\n\\}`, "g"))].map((m) => m[1]).join("\n");
  const claro = juntarBlocos("claro");
  assert.match(claro, /--glass-canvas:[\s\S]*?radial-gradient[\s\S]*?var\(--color-indigo-500\)[\s\S]*?var\(--app-bg\)/);
  const pct = (bloco: string) => [...(/--glass-canvas:([\s\S]*?);/.exec(bloco)?.[1] ?? "").matchAll(/--color-(?:indigo|violet)-\d+\) (\d+)%/g)].map((m) => Number(m[1]));
  const escuro = juntarBlocos("escuro");
  assert.ok(Math.max(...pct(claro)) <= 12, "claro: muito sutil");
  assert.ok(Math.max(...pct(escuro)) > Math.max(...pct(claro)) && Math.max(...pct(escuro)) <= 22, "escuro: um pouco mais perceptível, sem neon");
  assert.match(regrasGlass, /\[data-visual-style="glass"\] body \{\s*background: var\(--glass-canvas\);\s*background-attachment: fixed;/);
});

test("orçamento de blur: backdrop-filter SÓ no cabeçalho, nos flutuantes, no scrim/modal e no cartão central — nunca em card, tabela, linha, input ou card do Kanban", () => {
  const regras = [...regrasGlass.matchAll(/([^{}@]+)\{([^{}]*)\}/g)].map((m) => ({ seletor: m[1].trim(), corpo: m[2] }));
  const comBlur = regras.filter((r) => /(?<!-)backdrop-filter:\s*(?!none)/.test(r.corpo)).map((r) => r.seletor);
  assert.ok(comBlur.length > 0 && comBlur.length <= 10, `blur em poucas regras (${comBlur.length})`);
  for (const seletor of comBlur) {
    assert.match(seletor, /data-superficie/, seletor); // só superfícies que se declaram
    assert.doesNotMatch(seletor, /\.bg-surface|thead|\btr\b|\btd\b|\.field|kanban|input|select|textarea|button/, seletor);
  }
  for (const proibido of ["kanban", "thead", ".field", "input", "select", "textarea", " td", " tr"]) {
    const regra = regras.find((r) => r.seletor.includes(proibido) && /backdrop-filter:\s*(?!none)/.test(r.corpo));
    assert.equal(regra, undefined, proibido);
  }
});

test("vidro aninhado: o container flutuante recalibra --surface/--surface-2 para um tom PLANO e os filhos não ganham outro blur", () => {
  for (const superficie of ["menu", "painel", "tooltip", "modal"]) {
    const regra = new RegExp(`\\[data-superficie="${superficie}"\\][\\s\\S]*?\\{([^}]*)\\}`).exec(regrasGlass)?.[1] ?? "";
    assert.match(regra, /--surface: var\(--glass-nested\)/, superficie);
    assert.match(regra, /--surface-2: var\(--glass-panel-2\)/, superficie);
  }
  assert.match(regrasGlass, /\.sticky\.bg-surface \{\s*background-color: var\(--glass-sticky\)/); // células fixas quase opacas: nada que rola aparece por baixo
});

test("tokens semânticos remapeados centralmente (bg-surface/border-line/.field) e o select nativo mantém fundo opaco", () => {
  for (const mapa of ["--surface: var(--glass-panel)", "--surface-2: var(--glass-panel-2)", "--line: var(--glass-divider)", "--line-strong: var(--glass-divider-strong)", "--field-bg: var(--glass-input)"]) {
    assert.ok(regrasGlass.includes(mapa), mapa);
  }
  assert.match(regrasGlass, /\[data-theme="claro"\] select\.field \{\s*background-color: #ffffff;/);
  assert.match(regrasGlass, /\[data-theme="escuro"\] select\.field \{\s*background-color: #0f0f11;/);
});

test("nada de genérico perigoso: bg-white (knob do Switch) e cores semânticas/de prioridade não são reescritos pelo Glass", () => {
  assert.doesNotMatch(regrasGlass, /\.bg-white\b|\.dark\\:bg-zinc-900\b/);
  assert.doesNotMatch(blocoApp, /amber|emerald|red-|green|--danger|--success|--warning|--info|prioridade|brand-gradient\s*\{/i);
  assert.doesNotMatch(regrasGlass, /\[data-kanban-card\][^{]*\{[^}]*border-left/); // a borda esquerda de prioridade do card nunca é tocada
  assert.match(regrasGlass, /:not\(\[class\*="bg-indigo-50"\]\)/); // o destaque de "soltar aqui" da coluna sobrevive
});

test("fallbacks do app: sem blur ou com 'reduzir transparência' o material vira opaco (tokens do app incluídos)", () => {
  const ultimoSupports = regrasGlass.slice(regrasGlass.lastIndexOf("@supports not"));
  const reduzido = regrasGlass.slice(regrasGlass.lastIndexOf("@media (prefers-reduced-transparency: reduce)"));
  for (const bloco of [ultimoSupports, reduzido]) {
    for (const token of ["shell", "panel", "input", "modal-surface", "scrim"]) assert.match(bloco, new RegExp(`--glass-${token}:`), token);
  }
  for (const superficie of ["cabecalho", "menu", "painel", "tooltip", "overlay", "modal", "cartao-central"]) assert.ok(reduzido.includes(`[data-superficie="${superficie}"]`), superficie);
});

test("ganchos nos primitivos: modal, scrim, cabeçalho, menus, tooltips e cartão central declaram a superfície (corrigir o primitivo, não 30 telas)", () => {
  const esperado: Record<string, string[]> = {
    "components/ui/Modal.tsx": ['data-superficie="overlay"', 'data-superficie="modal"'],
    "components/ui/DetailsModal.tsx": ['data-superficie="overlay"', 'data-superficie="modal"'],
    "components/layout/TopNav.tsx": ['data-superficie="cabecalho"'],
    "components/layout/GestaoTopBar.tsx": ['data-superficie="cabecalho"'],
    "components/layout/ProfileMenu.tsx": ['data-superficie="menu"'],
    "components/layout/NotificationBell.tsx": ['data-superficie="menu"'],
    "components/ui/Combobox.tsx": ['data-superficie="menu"'],
    "components/ui/MemberSelector.tsx": ['data-superficie="menu"'],
    "components/demandas/ProgressoDemanda.tsx": ['data-superficie="tooltip"'],
    "components/trafego/TrafegoHeader.tsx": ['data-superficie="tooltip"'],
    "components/auth/EsqueciSenhaView.tsx": ['data-superficie="cartao-central"'], // (o login tem tela própria, sempre clara: ver login-claro.test.ts)
    "components/demandas/DemandaKanbanCard.tsx": ["data-kanban-card"],
  };
  for (const [arquivo, ganchos] of Object.entries(esperado)) {
    const codigo = semComentarios(ler(arquivo));
    for (const gancho of ganchos) assert.ok(codigo.includes(gancho), `${arquivo}: ${gancho}`);
  }
  assert.match(semComentarios(ler("components/filtros/PainelFlutuante.tsx")), /data-superficie=\{superficie \?\? "painel"\}/);
});

test("o estilo padrão fica intacto: os primitivos só ganharam atributos data-*; nenhuma classe visual foi trocada", () => {
  // as classes de superfície que existiam continuam nos mesmos elementos (o Glass as sobrepõe só sob o atributo global)
  assert.match(semComentarios(ler("components/ui/Modal.tsx")), /"relative max-h-\[90vh\] w-full overflow-y-auto rounded-2xl border border-line bg-surface p-6 shadow-2xl"/);
  assert.match(semComentarios(ler("components/ui/DetailsModal.tsx")), /relative flex max-h-\[85vh\] w-full flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl/);
  assert.match(semComentarios(ler("components/layout/TopNav.tsx")), /sticky top-0 z-20 border-b border-line bg-white\/70 backdrop-blur-xl dark:bg-zinc-950\/70/);
  assert.match(semComentarios(ler("components/ui/Switch.tsx")), /rounded-full bg-white/); // o knob do Switch continua branco sólido
});

test("auditoria de superfícies Glass: TODA rota de src/app/**/page.tsx está classificada (nenhuma rota esquecida em silêncio)", async () => {
  const { readdirSync, statSync } = await import("node:fs");
  const { AUDITORIA_GLASS } = await import("./glass-superficies.ts");
  const raiz = new URL("../app/", import.meta.url);
  const achadas: string[] = [];
  const andar = (dir: URL, prefixo: string) => {
    for (const nome of readdirSync(dir)) {
      const caminho = new URL(`${nome}${statSync(new URL(`${nome}`, dir)).isDirectory() ? "/" : ""}`, dir);
      if (statSync(caminho).isDirectory()) andar(caminho, prefixo ? `${prefixo}/${nome}` : nome);
      else if (nome === "page.tsx") achadas.push(prefixo);
    }
  };
  andar(raiz, "");
  const classificadas = AUDITORIA_GLASS.map((item) => item.rota);
  assert.deepEqual([...achadas].filter((r) => r !== "").sort(), [...classificadas].sort());
  assert.equal(new Set(classificadas).size, classificadas.length);
  for (const item of AUDITORIA_GLASS) {
    assert.ok(item.superficies.length > 0, item.rota);
    assert.ok(item.glass === "aplicado" || item.glass === "intencionalmente-inalterado", item.rota);
  }
});

// ── Contraste automatizado do Glass: o texto continua legível sobre o material TRANSLÚCIDO (pior caso = canvas com o brilho máximo da marca) ─────────────────────────────────────────────

type Rgb = [number, number, number];
const hex = (h: string): Rgb => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const misturar = (frente: Rgb, alfa: number, fundo: Rgb): Rgb => [0, 1, 2].map((i) => Math.round(frente[i] * alfa + fundo[i] * (1 - alfa))) as Rgb;
const luminancia = (c: Rgb) => {
  const [r, g, b] = c.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
const contraste = (a: Rgb, b: Rgb) => {
  const [la, lb] = [luminancia(a), luminancia(b)];
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
};
/** "--glass-x: color-mix(in srgb, #rrggbb NN%, transparent)" do bloco do tema → { cor, alfa } */
function mixTransparente(tema: "claro" | "escuro", token: string): { cor: Rgb; alfa: number } {
  const blocos = [...regrasGlass.matchAll(new RegExp(`\\[data-visual-style="glass"\\]\\[data-theme="${tema}"\\] \\{([\\s\\S]*?)\\n\\}`, "g"))].map((m) => m[1]).join("\n");
  const m = new RegExp(`--glass-${token}: color-mix\\(in srgb, (#[0-9a-f]{6}) (\\d+(?:\\.\\d+)?)%, transparent\\)`).exec(blocos);
  assert.ok(m, `${tema} ${token}`);
  return { cor: hex(m[1]), alfa: Number(m[2]) / 100 };
}
const TOKENS_TEXTO = {
  claro: { fundo: hex("#fafafa"), fg: hex("#18181b"), muted: hex("#5b5b64"), subtle: hex("#6b6b74"), marca: hex("#6366f1"), brilho: 0.11 + 0.08 + 0.07 },
  escuro: { fundo: hex("#09090b"), fg: hex("#f4f4f5"), muted: hex("#a1a1aa"), subtle: hex("#8f8f99"), marca: hex("#6366f1"), brilho: 0.2 + 0.14 + 0.1 },
} as const;

test("contraste Glass: texto sobre painel/modal/menu translúcidos (pior caso: canvas com todo o brilho da marca) ≥ 4,5:1 nos dois modos", () => {
  const resultados: string[] = [];
  for (const tema of ["claro", "escuro"] as const) {
    const t = TOKENS_TEXTO[tema];
    const canvasPiorCaso = misturar(t.marca, t.brilho, t.fundo);
    for (const [nome, token] of [["painel", "panel"], ["cabeçalho", "shell"], ["modal", "modal-surface"], ["flutuante", "surface"]] as const) {
      const { cor, alfa } = mixTransparente(tema, token);
      const superficie = misturar(cor, alfa, canvasPiorCaso);
      for (const [rotulo, texto] of [["fg", t.fg], ["muted", t.muted], ["subtle", t.subtle]] as const) {
        const razao = contraste(texto, superficie);
        resultados.push(`${tema}/${nome}/${rotulo}=${razao.toFixed(2)}`);
        assert.ok(razao >= 4.5, `${tema} ${nome} ${rotulo}: ${razao.toFixed(2)}`);
      }
    }
  }
  console.log(`CONTRASTE_GLASS ${resultados.join(" ")}`);
});

test("contraste Glass: dia selecionado usa o texto-sobre-marca já validado (--on-brand) e o fallback opaco é ainda mais legível", () => {
  assert.match(regrasGlass, /--glass-selected-text: var\(--on-brand, #ffffff\)/);
  for (const tema of ["claro", "escuro"] as const) {
    const t = TOKENS_TEXTO[tema];
    const opaco = tema === "claro" ? hex("#ffffff") : hex("#18181b");
    assert.ok(contraste(t.fg, opaco) >= 7 && contraste(t.muted, opaco) >= 4.5, tema);
  }
});
