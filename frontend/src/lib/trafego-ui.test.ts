// Hotfix 11B.2A — Tráfego: seletor de Demanda com seleção explícita (mesmo com UMA demanda), cabeçalho sem selos e com tooltip, faixa superior compacta.
// `npm run test:trafego-ui` (node --test, sem DOM): lógica pura exercitada de verdade; telas (alias `@/`) lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { PLACEHOLDER_DEMANDA, TEXTO_INFO_TRAFEGO, opcoesDeDemanda, podeIniciarSessao } from "./trafego-ui.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const demanda = (id: string) => ({ id, nome: `Demanda ${id}` });
const paraOpcao = (d: { id: string; nome: string }) => ({ value: d.id, label: d.nome });

// ── seletor de Demanda ───────────────────────────────────────────────────────────────────────────────────────

test("UMA demanda: a lista começa pelo placeholder 'Selecione uma demanda...' (value vazio, desabilitado) e a demanda vem depois — nada auto-selecionado", () => {
  const opcoes = opcoesDeDemanda([demanda("d1")], paraOpcao);
  assert.equal(PLACEHOLDER_DEMANDA, "Selecione uma demanda...");
  assert.deepEqual(opcoes, [
    { value: "", label: "Selecione uma demanda...", disabled: true },
    { value: "d1", label: "Demanda d1" },
  ]);
});

test("UMA demanda: estado inicial vazio mantém o botão desabilitado; escolher a única demanda (onChange) preenche o id e, com usuário, HABILITA", () => {
  let demandaId = ""; // estado inicial do componente
  const usuarioId = "u1";
  assert.equal(podeIniciarSessao({ enviando: false, demandaId, usuarioId }), false); // o bug: o navegador mostrava a demanda, o estado seguia vazio
  const valorDoSelect = (valor: string) => (demandaId = valor); // o que onChange={(e) => setDemandaId(e.target.value)} faz
  valorDoSelect("d1");
  assert.equal(demandaId, "d1");
  assert.equal(podeIniciarSessao({ enviando: false, demandaId, usuarioId }), true);
  valorDoSelect(""); // voltar ao placeholder desfaz a escolha
  assert.equal(podeIniciarSessao({ enviando: false, demandaId, usuarioId }), false);
});

test("ZERO demandas: só o placeholder existe — não há como iniciar", () => {
  const opcoes = opcoesDeDemanda([], paraOpcao);
  assert.deepEqual(opcoes, [{ value: "", label: PLACEHOLDER_DEMANDA, disabled: true }]);
  assert.equal(podeIniciarSessao({ enviando: false, demandaId: opcoes[0].value, usuarioId: "u1" }), false);
});

test("DUAS ou mais demandas: o placeholder continua primeiro, a ordem original é preservada e qualquer uma pode ser escolhida", () => {
  const opcoes = opcoesDeDemanda([demanda("a"), demanda("b"), demanda("c")], paraOpcao);
  assert.deepEqual(opcoes.map((o) => o.value), ["", "a", "b", "c"]);
  assert.equal(opcoes.filter((o) => o.disabled).length, 1);
  for (const escolhida of ["a", "b", "c"]) assert.equal(podeIniciarSessao({ enviando: false, demandaId: escolhida, usuarioId: "u1" }), true);
});

test("a regra de habilitação NÃO mudou: precisa de Demanda E Usuário e de não estar enviando (tabela-verdade igual à expressão original)", () => {
  for (const enviando of [false, true]) {
    for (const demandaId of ["", "d1"]) {
      for (const usuarioId of ["", "u1"]) {
        const desabilitadoOriginal = enviando || !demandaId || !usuarioId; // disabled={loading || !demandaId || !usuarioId}
        assert.equal(podeIniciarSessao({ enviando, demandaId, usuarioId }), !desabilitadoOriginal, `${enviando}/${demandaId}/${usuarioId}`);
      }
    }
  }
});

test("o componente usa o placeholder e a regra extraídos, não auto-seleciona a primeira demanda e não toca no seletor de usuário", () => {
  const tela = semComentarios(ler("components/trafego/TrafegoIniciarSessao.tsx"));
  assert.match(tela, /options=\{opcoesDeDemanda\(demandas,/);
  assert.match(tela, /disabled=\{!podeIniciarSessao\(\{ enviando: loading, demandaId, usuarioId \}\)\}/);
  assert.match(tela, /const \[demandaId, setDemandaId\] = useState\(""\)/); // começa vazio
  assert.doesNotMatch(tela, /setDemandaId\(demandas\[0\]|useEffect/); // sem auto-seleção
  assert.match(tela, /onChange=\{\(values\) => setUsuarioId\(values\[0\] \?\? ""\)\}/); // MemberSelector intacto
  assert.match(ler("components/ui/Select.tsx"), /disabled=\{option\.disabled\}/);
});

// ── cabeçalho ────────────────────────────────────────────────────────────────────────────────────────────────

test("o cabeçalho não tem mais os selos 'Dados reais' e 'Motor de horas' (em nenhum componente do Tráfego)", () => {
  for (const arquivo of ["TrafegoHeader", "TrafegoView", "TrafegoFilters", "TrafegoIniciarSessao"]) {
    assert.doesNotMatch(ler(`components/trafego/${arquivo}.tsx`), /Dados reais|Motor de horas/, arquivo);
  }
});

test("'Central de Tráfego' ganha o ícone de informação com tooltip exato, acessível por hover E teclado", () => {
  assert.equal(TEXTO_INFO_TRAFEGO, "Sessões de trabalho abertas e encerradas via API, calculadas pelo motor de horas do backend.");
  const cabecalho = semComentarios(ler("components/trafego/TrafegoHeader.tsx"));
  assert.match(cabecalho, /Central de Tráfego/);
  assert.match(cabecalho, /<Info className=/); // ícone de informação
  assert.match(cabecalho, /<InfoTooltip texto=\{TEXTO_INFO_TRAFEGO\} \/>/); // trigger + conteúdo = o texto exato
  assert.match(cabecalho, /role="tooltip"/);
  assert.match(cabecalho, /aria-describedby=\{id\}/);
  assert.match(cabecalho, /group-hover:opacity-100/);
  assert.match(cabecalho, /group-focus-within:opacity-100/);
  assert.match(cabecalho, /<button\s+type="button"/); // focável por teclado
  // o texto saiu do parágrafo fixo: aparece só no tooltip (vem da constante)
  assert.doesNotMatch(cabecalho, /Sessões de trabalho abertas e encerradas/);
});

// ── faixa superior compacta ───────────────────────────────────────────────────────────────────────────────────

test("Usuário + Demanda + iniciar + período + busca ficam numa só faixa (um cartão, quebra por largura); filtros avançados logo abaixo", () => {
  const view = semComentarios(ler("components/trafego/TrafegoView.tsx"));
  const faixa = view.slice(view.indexOf('<section aria-label="Iniciar sessão e filtros operacionais"'), view.indexOf("</section>"));
  assert.match(faixa, /flex flex-wrap items-end/); // mesma linha quando há largura; quebra sozinha quando não há
  const ordem = ["<TrafegoIniciarSessao", "<TrafegoFilters", "<FiltrosAvancados"].map((marca) => faixa.indexOf(marca));
  assert.ok(ordem.every((i) => i >= 0) && ordem[0] < ordem[1] && ordem[1] < ordem[2], String(ordem));
  // cada parte deixou de ser um cartão próprio
  assert.doesNotMatch(semComentarios(ler("components/trafego/TrafegoIniciarSessao.tsx")), /rounded-2xl border/);
  assert.doesNotMatch(semComentarios(ler("components/trafego/TrafegoFilters.tsx")), /rounded-2xl border/);
  // período e busca continuam ligados à URL
  assert.match(faixa, /definirParam\("periodo"/);
  assert.match(faixa, /definirParam\("q"/);
  assert.match(faixa, /<FiltrosAvancados definicoes=\{definicoesFiltros\} filtros=\{filtros\} onChange=\{definirFiltros\} \/>/);
});
