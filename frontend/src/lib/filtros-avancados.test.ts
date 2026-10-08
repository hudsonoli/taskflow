// Fase 6 — componente compartilhado de filtros avançados (modelo, operadores, datas, URL). `npm run test:advanced-filters`.
// Lógica pura exercitada de verdade; componentes (.tsx com alias `@/`) são lidos como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  ROTULO_OPERADOR,
  alternarValor,
  aplicarFiltro,
  campoBuscavel,
  codificarFiltro,
  dataIsoValida,
  decodificarFiltro,
  decodificarFiltros,
  filtroDeData,
  filtrosIguais,
  filtrosParaParametros,
  intervaloDaData,
  limparFiltros,
  operadoresEscolhiveis,
  removerFiltro,
  resumirValores,
  trocarOperador,
  PRESETS_DATA,
} from "./filtros-avancados.ts";
import type { DefinicaoFiltro, FiltroAtivo } from "../types/filtros.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");

const STATUS: DefinicaoFiltro = {
  id: "status",
  label: "Status",
  tipo: "enum",
  opcoes: [
    { value: "em_andamento", label: "Em andamento" },
    { value: "aguardando", label: "Aguardando" },
    { value: "concluida", label: "Concluída" },
  ],
};
const RESPONSAVEL: DefinicaoFiltro = { id: "responsavel", label: "Responsável", tipo: "enum", valoresAbertos: true, buscarOpcoes: async () => [] };
const CLIENTE: DefinicaoFiltro = { id: "cliente", label: "Cliente", tipo: "enum", valoresAbertos: true, opcoes: [] };
const PRAZO: DefinicaoFiltro = { id: "prazo", label: "Prazo", tipo: "data", presets: [PRESETS_DATA.hoje, PRESETS_DATA.atrasado] };
const SESSAO: DefinicaoFiltro = { id: "sessao", label: "Sessão", tipo: "enum", multiplo: false, permiteExcluir: false, opcoes: [{ value: "ativa", label: "Ativa" }] };
const DEFINICOES = [STATUS, RESPONSAVEL, CLIENTE, PRAZO, SESSAO];

const UUID_A = "0b8f7e0e-4c2d-4f0a-9d37-1f2e3a4b5c6d";
const UUID_B = "7a1c2d3e-4f50-4617-8899-aabbccddeeff";

// ── adicionar / remover / limpar / trocar operador ───────────────────────────────────────────────────────────────

test("adicionar filtro: o primeiro valor cria 'é'; o segundo vira 'é um de' (OR) e preserva a ordem", () => {
  let filtros: FiltroAtivo[] = [];
  const um = alternarValor(undefined, STATUS, "em_andamento");
  assert.deepEqual(um, { campo: "status", operador: "is", valores: ["em_andamento"] });
  filtros = aplicarFiltro(filtros, um!);
  const dois = alternarValor(filtros[0], STATUS, "aguardando");
  assert.deepEqual(dois, { campo: "status", operador: "in", valores: ["em_andamento", "aguardando"] });
  filtros = aplicarFiltro(filtros, dois!);
  assert.equal(filtros.length, 1); // um campo aparece uma vez
  assert.equal(ROTULO_OPERADOR[filtros[0].operador], "é um de");
});

test("desmarcar o último valor remove o filtro; desmarcar um de vários volta para 'é'", () => {
  const dois: FiltroAtivo = { campo: "status", operador: "in", valores: ["em_andamento", "aguardando"] };
  assert.deepEqual(alternarValor(dois, STATUS, "aguardando"), { campo: "status", operador: "is", valores: ["em_andamento"] });
  assert.equal(alternarValor({ campo: "status", operador: "is", valores: ["aguardando"] }, STATUS, "aguardando"), null);
});

test("remover um filtro não toca nos outros; limpar remove todos", () => {
  const a: FiltroAtivo = { campo: "status", operador: "is", valores: ["aguardando"] };
  const b: FiltroAtivo = { campo: "cliente", operador: "is", valores: [UUID_A] };
  const lista = aplicarFiltro(aplicarFiltro([], a), b);
  assert.deepEqual(removerFiltro(lista, "status"), [b]);
  assert.deepEqual(lista, [a, b]); // imutável
  assert.deepEqual(limparFiltros(), []);
});

test("trocar operador: em enum só a polaridade muda ('é um de' segue a quantidade)", () => {
  const um: FiltroAtivo = { campo: "status", operador: "is", valores: ["aguardando"] };
  assert.deepEqual(operadoresEscolhiveis(STATUS, um), ["is", "is_not"]);
  assert.equal(trocarOperador(um, STATUS, "is_not").operador, "is_not");
  const varios: FiltroAtivo = { campo: "status", operador: "in", valores: ["aguardando", "concluida"] };
  assert.deepEqual(operadoresEscolhiveis(STATUS, varios), ["in", "not_in"]);
  const negado = trocarOperador(varios, STATUS, "not_in");
  assert.equal(negado.operador, "not_in");
  assert.deepEqual(negado.valores, varios.valores);
  // sem exclusão (campo que o servidor não sabe negar): não há "não é"
  assert.deepEqual(operadoresEscolhiveis(SESSAO, { campo: "sessao", operador: "is", valores: ["ativa"] }), ["is"]);
  assert.equal(trocarOperador({ campo: "sessao", operador: "is", valores: ["ativa"] }, SESSAO, "is_not").operador, "is");
});

test("campo sem múltiplos: escolher outro valor substitui; 'não é' mantém a polaridade ao adicionar valores", () => {
  assert.deepEqual(alternarValor({ campo: "sessao", operador: "is", valores: ["ativa"] }, SESSAO, "encerrada"), { campo: "sessao", operador: "is", valores: ["encerrada"] });
  const negado: FiltroAtivo = { campo: "status", operador: "is_not", valores: ["concluida"] };
  assert.equal(alternarValor(negado, STATUS, "aguardando")!.operador, "not_in");
});

// ── múltiplos valores / resumo ───────────────────────────────────────────────────────────────────────────────────

test("resumo compacto: 'Maria', 'Maria, João' e 'Maria, João +1'; rótulo pendente nunca mostra o id", () => {
  const nomes: Record<string, string> = { a: "Maria", b: "João", c: "Carlos" };
  const r = (valor: string) => nomes[valor];
  assert.equal(resumirValores(["a"], r), "Maria");
  assert.equal(resumirValores(["a", "b"], r), "Maria, João");
  assert.equal(resumirValores(["a", "b", "c"], r), "Maria, João +1");
  assert.equal(resumirValores(["a", "zzz"], r, "Carregando…"), "Maria, Carregando…");
});

test("busca dentro das opções: campos com muitas opções ou no servidor são pesquisáveis", () => {
  assert.equal(campoBuscavel(STATUS), false);
  assert.equal(campoBuscavel(RESPONSAVEL), true);
  assert.equal(campoBuscavel({ ...STATUS, opcoes: Array.from({ length: 8 }, (_, i) => ({ value: String(i), label: `Opção ${i}` })) }), true);
  assert.equal(campoBuscavel({ ...STATUS, buscavel: true }), true);
});

// ── datas ───────────────────────────────────────────────────────────────────────────────────────────────────────

test("data real: 'é' = dia inteiro, 'antes de' = até a véspera, 'depois de' = a partir do dia seguinte", () => {
  const agora = new Date(2026, 9, 8, 15, 30);
  const dia = intervaloDaData("is", "2026-10-15", agora)!;
  assert.deepEqual([dia.inicio!.getDate(), dia.inicio!.getHours(), dia.fim!.getDate(), dia.fim!.getHours(), dia.fim!.getMinutes()], [15, 0, 15, 23, 59]);
  const antes = intervaloDaData("before", "2026-10-15", agora)!;
  assert.equal(antes.inicio, null);
  assert.equal(antes.fim!.getTime(), new Date(2026, 9, 15, 0, 0, 0, 0).getTime() - 1);
  const depois = intervaloDaData("after", "2026-10-15", agora)!;
  assert.equal(depois.fim, null);
  assert.equal(depois.inicio!.getTime(), new Date(2026, 9, 15, 23, 59, 59, 999).getTime() + 1); // 16/10 00:00
});

test("atalhos: hoje, amanhã, ontem, esta semana (segunda a domingo), este mês e atrasado", () => {
  const quinta = new Date(2026, 9, 8, 15, 30); // quinta-feira
  const dia = (i: ReturnType<typeof intervaloDaData>) => [i!.inicio?.getDate(), i!.fim?.getDate()];
  assert.deepEqual(dia(intervaloDaData("is", "hoje", quinta)), [8, 8]);
  assert.deepEqual(dia(intervaloDaData("is", "amanha", quinta)), [9, 9]);
  assert.deepEqual(dia(intervaloDaData("is", "ontem", quinta)), [7, 7]);
  const semana = intervaloDaData("is", "esta_semana", quinta)!;
  assert.deepEqual([semana.inicio!.getDay(), semana.inicio!.getDate(), semana.fim!.getDay(), semana.fim!.getDate()], [1, 5, 0, 11]); // seg 5/10 a dom 11/10
  const mes = intervaloDaData("is", "este_mes", quinta)!;
  assert.deepEqual([mes.inicio!.getDate(), mes.fim!.getDate()], [1, 31]);
  const atrasado = intervaloDaData("is", "atrasado", quinta)!;
  assert.equal(atrasado.inicio, null);
  assert.equal(atrasado.fim!.getTime(), quinta.getTime() - 1);
  // domingo pertence à semana que termina nele
  const domingo = intervaloDaData("is", "esta_semana", new Date(2026, 9, 11, 10))!;
  assert.equal(domingo.inicio!.getDate(), 5);
});

test("data inválida ou atalho com 'antes de' não gera intervalo (o filtro simplesmente não é aplicado)", () => {
  for (const [op, valor] of [["is", "2026-02-30"], ["is", "ontem?"], ["before", "hoje"], ["after", "atrasado"], ["is", ""]] as const) {
    assert.equal(intervaloDaData(op, valor, new Date()), null, `${op} ${valor}`);
  }
  assert.equal(dataIsoValida("2026-02-30"), false);
  assert.equal(dataIsoValida("2026-2-3"), false);
  assert.equal(dataIsoValida("2028-02-29"), true);
});

test("trocar 'é hoje' para 'antes de' exige uma data real (vira a data de hoje)", () => {
  const hoje = filtroDeData("prazo", "is", "hoje");
  const antes = trocarOperador(hoje, PRAZO, "before");
  assert.equal(antes.operador, "before");
  assert.ok(dataIsoValida(antes.valores[0]));
  const data = filtroDeData("prazo", "after", "2026-10-15");
  assert.deepEqual(trocarOperador(data, PRAZO, "is").valores, ["2026-10-15"]);
});

// ── URL ─────────────────────────────────────────────────────────────────────────────────────────────────────────

function viaUrl(filtros: FiltroAtivo[], definicoes = DEFINICOES): FiltroAtivo[] {
  const params = new URLSearchParams();
  for (const [nome, valor] of filtrosParaParametros(filtros)) params.set(nome, valor);
  const recarregada = new URLSearchParams(params.toString()); // refresh: a URL é a única fonte
  return decodificarFiltros((nome) => recarregada.get(nome), definicoes);
}

test("encode/decode: ids e códigos estáveis, nunca rótulos; refresh reconstrói exatamente os mesmos filtros", () => {
  const filtros: FiltroAtivo[] = [
    { campo: "status", operador: "in", valores: ["em_andamento", "aguardando"] },
    { campo: "responsavel", operador: "not_in", valores: [UUID_A, UUID_B] },
    { campo: "cliente", operador: "is", valores: [UUID_A] },
    { campo: "prazo", operador: "before", valores: ["2026-10-15"] },
  ];
  assert.equal(codificarFiltro(filtros[0]), "in:em_andamento,aguardando");
  assert.equal(codificarFiltro(filtros[3]), "before:2026-10-15");
  const lidos = viaUrl(filtros);
  assert.ok(filtrosIguais(lidos, filtros));
  // nenhum rótulo em português vai para a URL
  const texto = JSON.stringify(filtrosParaParametros(filtros));
  assert.doesNotMatch(texto, /Em andamento|Aguardando|Responsável/);
});

test("atalho de data vai para a URL como código ('hoje'), não como data fixa — o link continua relativo", () => {
  const lidos = viaUrl([filtroDeData("prazo", "is", "atrasado")]);
  assert.deepEqual(lidos, [{ campo: "prazo", operador: "is", valores: ["atrasado"] }]);
});

test("valores inválidos na URL são ignorados com segurança (nunca lança)", () => {
  const ruins: Array<[DefinicaoFiltro, string | null]> = [
    [STATUS, null],
    [STATUS, ""],
    [STATUS, "sem-dois-pontos"],
    [STATUS, "contem:x"], // operador desconhecido
    [STATUS, "in:"], // sem valores
    [STATUS, "in:inexistente,tambem"], // enum fechado: valores fora da lista
    [STATUS, "before:em_andamento"], // operador de data em enum
    [RESPONSAVEL, "in:<script>alert(1)</script>"],
    [RESPONSAVEL, "is:" + "x".repeat(200)],
    [RESPONSAVEL, "is:%E0%A4%A"], // % malformado
    [PRAZO, "is:2026-13-45"],
    [PRAZO, "before:hoje"], // 'antes de' exige data real
    [PRAZO, "in:2026-10-10"], // enum em data
    [PRAZO, "is_not:2026-10-10"],
    [SESSAO, "is_not:ativa"], // campo sem exclusão
  ];
  for (const [definicao, bruto] of ruins) {
    assert.equal(decodificarFiltro(definicao, bruto), null, `${definicao.id} <- ${String(bruto)}`);
  }
  // valores bons e ruins misturados: o que presta é mantido, o resto é descartado
  assert.deepEqual(decodificarFiltro(STATUS, "in:aguardando,lixo,concluida"), { campo: "status", operador: "in", valores: ["aguardando", "concluida"] });
});

test("normalização: quantidade manda no 'um de'; campo sem múltiplos mantém só o primeiro; duplicados somem; teto de valores", () => {
  assert.equal(decodificarFiltro(STATUS, "is:aguardando,concluida")!.operador, "in");
  assert.equal(decodificarFiltro(STATUS, "in:aguardando")!.operador, "is");
  assert.equal(decodificarFiltro(STATUS, "not_in:aguardando")!.operador, "is_not");
  assert.deepEqual(decodificarFiltro(STATUS, "in:aguardando,aguardando")!.valores, ["aguardando"]);
  assert.deepEqual(decodificarFiltro(SESSAO, "in:ativa,ativa")!.valores, ["ativa"]);
  const muitos = Array.from({ length: 80 }, (_, i) => `id${i}`).join(",");
  assert.equal(decodificarFiltro(RESPONSAVEL, `in:${muitos}`)!.valores.length, 50);
});

test("campos desconhecidos e parâmetros que não são filtros (q, periodo) são ignorados; a ordem segue as definições", () => {
  const params = new URLSearchParams({ q: "banner", periodo: "7d", intruso: "is:x", cliente: `is:${UUID_A}`, status: "is:aguardando" });
  const lidos = decodificarFiltros((nome) => params.get(nome), DEFINICOES);
  assert.deepEqual(lidos.map((filtro) => filtro.campo), ["status", "cliente"]);
});

test("ids de registro (valoresAbertos) são aceitos antes de a lista de opções chegar; enum fechado não", () => {
  assert.ok(decodificarFiltro({ ...CLIENTE, opcoes: [] }, `is:${UUID_A}`));
  assert.equal(decodificarFiltro({ ...STATUS, opcoes: [] }, "is:aguardando"), null);
});

// ── componente (leitura estrutural) ──────────────────────────────────────────────────────────────────────────────

test("componente: chips editáveis [campo][operador][valores][x], rótulo acessível do X e limpar só com filtros ativos", () => {
  const codigo = ler("components/filtros/FiltrosAvancados.tsx");
  assert.match(codigo, /aria-label=\{`Remover filtro \$\{definicao\.label\}`\}/);
  assert.match(codigo, /aria-expanded=\{painel\?\.tipo === "campos"\}/);
  assert.match(codigo, /aria-haspopup="dialog"/);
  assert.match(codigo, /\{ativos\.length > 0 && \(\s*<Button[^>]*onClick=\{\(\) => onChange\(limparFiltros\(\)\)\}/);
  assert.match(codigo, /onClick=\{\(evento\) => abrir\("operador"/);
  assert.match(codigo, /onClick=\{\(evento\) => abrir\("valores"/);
  assert.match(codigo, /role="group"\s+aria-label=\{`Filtro \$\{definicao\.label\}`\}/);
});

test("componente: mobile com rolagem horizontal dos chips, botão 'Filtrar' sempre visível e painel que cabe em 375px", () => {
  const codigo = ler("components/filtros/FiltrosAvancados.tsx");
  assert.match(codigo, /overflow-x-auto[^"]*sm:flex-wrap/);
  assert.match(codigo, /order-first shrink-0 sm:order-none/); // botão antes dos chips no mobile
  assert.equal((codigo.match(/aria-haspopup="dialog"\s+aria-expanded=\{painel\?\.tipo === "campos"\}/g) ?? []).length, 1); // um único botão Filtrar
  const painel = ler("components/filtros/PainelFlutuante.tsx");
  assert.match(painel, /createPortal\(/); // não é cortado pelo overflow dos chips
  assert.match(painel, /position: "fixed"/);
  assert.match(painel, /min\(\$\{largura\}px, calc\(100vw - /);
  assert.match(painel, /evento\.key !== "Escape"/);
});

test("opções: busca com debounce no servidor, resposta antiga descartada, teclado (setas/Enter) e aria de listbox", () => {
  const codigo = ler("components/filtros/FiltroPainelOpcoes.tsx");
  assert.match(codigo, /DEBOUNCE_MS = 300/);
  assert.match(codigo, /if \(cancelado\) return; \/\/ busca antiga/);
  assert.match(codigo, /role="listbox"/);
  assert.match(codigo, /role="option"/);
  assert.match(codigo, /aria-selected=\{marcada\}/);
  assert.match(codigo, /aria-activedescendant/);
  for (const tecla of ["ArrowDown", "ArrowUp", "Enter", "Home", "End"]) assert.ok(codigo.includes(`"${tecla}"`), tecla);
  assert.match(codigo, /aria-label=\{`Buscar em \$\{definicao\.label\}`\}/);
});

test("sem dependência nova e sem cores fixas da referência: só tokens do tema", () => {
  const pacote = JSON.parse(ler("../package.json")) as { dependencies: Record<string, string> };
  for (const proibida of ["nanoid", "@radix-ui/react-popover", "cmdk", "motion", "react-day-picker", "date-fns"]) {
    assert.equal(proibida in pacote.dependencies, false, proibida);
  }
  for (const arquivo of ["FiltrosAvancados", "FiltroPainelOpcoes", "FiltroPainelData", "PainelFlutuante"]) {
    const codigo = ler(`components/filtros/${arquivo}.tsx`);
    assert.doesNotMatch(codigo, /\b(red|yellow|blue|green|slate|gray|zinc)-\d{2,3}\b/, arquivo);
    assert.doesNotMatch(codigo, /Andrew Luo|Bug|Feature|Hotfix|Backlog|In Review/, arquivo);
  }
});

test("modelo genérico: a lib de filtros não conhece Arquivos nem Tráfego", () => {
  const lib = ler("lib/filtros-avancados.ts");
  assert.doesNotMatch(lib, /arquivo|trafego|cliente|projeto|sessao/i);
  assert.doesNotMatch(ler("components/filtros/FiltrosAvancados.tsx"), /arquivo|trafego/i);
});
