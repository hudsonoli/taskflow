// Fase 6.1 — filtros avançados de MEU DEPARTAMENTO. `npm run test:filtros-meu-departamento`.
// O comportamento genérico do componente (chips, operadores, teclado, mobile, URL) já é provado em `test:advanced-filters`;
// aqui: tradução para a API, escopo fixo do departamento e a ligação da tela com o componente COMPARTILHADO.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { decodificarFiltros, filtrosParaParametros, filtrosIguais, PRESETS_DATA } from "./filtros-avancados.ts";
import { CAMPO_MEU_DEPARTAMENTO, filtrosMeuDepartamentoParaApi, listaMostraSoOperacaoAberta } from "./filtros-meu-departamento.ts";
import type { DefinicaoFiltro, FiltroAtivo } from "../types/filtros.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const A = "0b8f7e0e-4c2d-4f0a-9d37-1f2e3a4b5c6d";
const B = "7a1c2d3e-4f50-4617-8899-aabbccddeeff";
const AGORA = new Date(2026, 9, 8, 15, 30);

// ── tradução para a API ───────────────────────────────────────────────────────────────────────────────────────────

test("um filtro: 'é' e 'não é' vão para o parâmetro e para a versão Excluir", () => {
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "cliente", operador: "is", valores: [A] }]), { clienteId: A });
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "cliente", operador: "is_not", valores: [A] }]), { clienteIdExcluir: A });
});

test("vários valores viram CSV (OR no servidor), em todos os campos de lista", () => {
  const filtros: FiltroAtivo[] = [
    { campo: "responsavel", operador: "in", valores: [A, B] },
    { campo: "equipe", operador: "not_in", valores: [A, B] },
    { campo: "projeto", operador: "in", valores: [A, B] },
    { campo: "status", operador: "in", valores: ["em_execucao", "aguardando_cliente"] },
    { campo: "prioridade", operador: "not_in", valores: ["baixa", "media"] },
  ];
  assert.deepEqual(filtrosMeuDepartamentoParaApi(filtros), {
    responsavelId: `${A},${B}`,
    equipeIdExcluir: `${A},${B}`,
    projetoId: `${A},${B}`,
    status: "em_execucao,aguardando_cliente",
    prioridadeExcluir: "baixa,media",
  });
});

test("vários filtros combinados: um parâmetro por campo (AND no servidor)", () => {
  const api = filtrosMeuDepartamentoParaApi(
    [
      { campo: "status", operador: "is", valores: ["em_execucao"] },
      { campo: "responsavel", operador: "is", valores: [A] },
      { campo: "origem", operador: "is", valores: ["cliente"] },
    ],
    AGORA,
  );
  assert.deepEqual(api, { status: "em_execucao", responsavelId: A, origem: "cliente" });
});

test("prazo: 'atrasado' mantém o significado antigo da tela (atrasada=true); datas e atalhos viram intervalo ISO", () => {
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "prazo", operador: "is", valores: ["atrasado"] }], AGORA), { atrasada: true });
  const hoje = filtrosMeuDepartamentoParaApi([{ campo: "prazo", operador: "is", valores: ["hoje"] }], AGORA);
  assert.equal(new Date(hoje.prazoInicio!).getTime(), new Date(2026, 9, 8, 0, 0, 0, 0).getTime());
  assert.equal(new Date(hoje.prazoFim!).getTime(), new Date(2026, 9, 8, 23, 59, 59, 999).getTime());
  const semana = filtrosMeuDepartamentoParaApi([{ campo: "prazo", operador: "is", valores: ["esta_semana"] }], AGORA);
  assert.equal(new Date(semana.prazoInicio!).getDay(), 1); // segunda
  assert.equal(new Date(semana.prazoFim!).getDay(), 0); // domingo
  const antes = filtrosMeuDepartamentoParaApi([{ campo: "prazo", operador: "before", valores: ["2026-10-15"] }], AGORA);
  assert.equal(antes.prazoInicio, undefined);
  assert.equal(new Date(antes.prazoFim!).getTime(), new Date(2026, 9, 15).getTime() - 1);
  const depois = filtrosMeuDepartamentoParaApi([{ campo: "prazo", operador: "after", valores: ["2026-10-15"] }], AGORA);
  assert.equal(new Date(depois.prazoInicio!).getTime(), new Date(2026, 9, 16).getTime());
  assert.match(depois.prazoInicio!, /Z$/);
});

test("filtro sem valores, campo desconhecido, origem inválida e data inválida não geram parâmetro; sem filtros = nada", () => {
  assert.deepEqual(filtrosMeuDepartamentoParaApi([]), {});
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "cliente", operador: "is", valores: [] }]), {});
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "inventado", operador: "is", valores: [A] }]), {});
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "origem", operador: "is", valores: ["qualquer"] }]), {});
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "prazo", operador: "is", valores: ["2026-99-99"] }], AGORA), {});
});

// ── escopo: o departamento NÃO é filtro ───────────────────────────────────────────────────────────────────────────

test("não existe filtro de Departamento: o departamento é o escopo (nem o mapeamento aceita um)", () => {
  assert.equal("departamento" in CAMPO_MEU_DEPARTAMENTO, false);
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "departamento", operador: "is", valores: [A] }]), {}); // ignorado
  const api = filtrosMeuDepartamentoParaApi([{ campo: "departamentoId", operador: "in", valores: [A] }, { campo: "departamento", operador: "is", valores: [A] }]);
  assert.equal("departamentoId" in api, false);
  const defs = ler("components/meu-departamento/useDefinicoesFiltrosMeuDepartamento.ts");
  assert.doesNotMatch(defs, /label: "Departamento"/);
  assert.doesNotMatch(defs, /listDiretorioDepartamentos|useDiretorioDepartamentos/);
});

test("URL: um ?departamento=... na URL é ignorado (não é campo conhecido) e nunca vira escopo", () => {
  const defs: DefinicaoFiltro[] = Object.values(CAMPO_MEU_DEPARTAMENTO).map((id) =>
    id === "prazo"
      ? { id, label: id, tipo: "data" as const, presets: [PRESETS_DATA.hoje, PRESETS_DATA.atrasado] }
      : { id, label: id, tipo: "enum" as const, valoresAbertos: true, opcoes: [{ value: "x", label: "x" }] },
  );
  const params = new URLSearchParams({ departamento: `is:${A}`, departamentoId: A, cliente: `is:${A}` });
  const lidos = decodificarFiltros((nome) => params.get(nome), defs);
  assert.deepEqual(lidos.map((filtro) => filtro.campo), ["cliente"]);
});

test("URL: refresh reconstrói os mesmos filtros (ids estáveis) e valores inválidos são ignorados", () => {
  const defs: DefinicaoFiltro[] = [
    { id: "status", label: "Status", tipo: "enum", opcoes: [{ value: "em_execucao", label: "Em execução" }, { value: "pausada", label: "Pausada" }] },
    { id: "responsavel", label: "Responsável", tipo: "enum", valoresAbertos: true, buscarOpcoes: async () => [] },
    { id: "prazo", label: "Prazo", tipo: "data", presets: [PRESETS_DATA.atrasado] },
  ];
  const filtros: FiltroAtivo[] = [
    { campo: "status", operador: "in", valores: ["em_execucao", "pausada"] },
    { campo: "responsavel", operador: "not_in", valores: [A, B] },
    { campo: "prazo", operador: "is", valores: ["atrasado"] },
  ];
  const params = new URLSearchParams();
  for (const [nome, valor] of filtrosParaParametros(filtros)) params.set(nome, valor);
  const recarregada = new URLSearchParams(params.toString());
  assert.ok(filtrosIguais(decodificarFiltros((n) => recarregada.get(n), defs), filtros));
  const ruim = new URLSearchParams({ status: "in:inexistente", responsavel: "is:<script>", prazo: "before:hoje" });
  assert.deepEqual(decodificarFiltros((n) => ruim.get(n), defs), []);
});

// ── ligação da tela ───────────────────────────────────────────────────────────────────────────────────────────────

test("a tela REUSA o componente compartilhado (sem implementação paralela) e removeu os 8 selects antigos", () => {
  const view = ler("components/meu-departamento/MeuDepartamentoView.tsx");
  assert.match(view, /import \{ FiltrosAvancados \} from "@\/components\/filtros\/FiltrosAvancados"/);
  assert.match(view, /<FiltrosAvancados definicoes=\{definicoesFiltros\} filtros=\{filtros\} onChange=\{definirFiltros\} \/>/);
  assert.match(view, /useFiltrosNaUrl\(definicoesFiltros, true\)/);
  assert.doesNotMatch(view, /<Select\b|<MemberSelector\b/);
  assert.doesNotMatch(view, /periodoParaFiltros|setColaboradorId|setPeriodo|alterarFiltro/);
  const arquivos = ler("components/meu-departamento/useDefinicoesFiltrosMeuDepartamento.ts");
  assert.doesNotMatch(arquivos, /FiltroChip|PainelFlutuante|useState/); // só definições
});

test("escopo: a consulta pede escopo=meu-departamento e estreita ao departamento ATUAL; filtros vão ao servidor", () => {
  const view = ler("components/meu-departamento/MeuDepartamentoView.tsx");
  assert.match(view, /\.\.\.parametrosFiltros,/);
  assert.match(view, /escopo: "meu-departamento",\s+departamentoId: departamentoHead\.id,/);
  assert.match(view, /departamentoHead = usuarioAtual \? resolverHeadDepartamento\(usuarioAtual, departamentos\)/); // contexto da Fase 5
  assert.doesNotMatch(view, /demandasPagina\.filter\(/); // nunca filtra só a página carregada
});

test("paginação e contexto: filtro ou departamento novo volta à 1ª página; resposta antiga não substitui a nova", () => {
  const view = ler("components/meu-departamento/MeuDepartamentoView.tsx");
  assert.match(view, /const chaveContexto = `\$\{departamentoHead\?\.id \?\? ""\}\\u0000\$\{JSON\.stringify\(parametrosFiltros\)\}`/);
  assert.match(view, /if \(chaveContexto !== chaveContextoVista\) \{[\s\S]*setOffset\(0\);/);
  assert.match(view, /const chaveBusca = \[departamentoHead\?\.id \?\? "", JSON\.stringify\(parametrosFiltros\), offset\]/);
  assert.match(view, /if \(cancelado\) return;/);
  assert.match(view, /\}, \[podeAcessar, departamentoHead, parametrosFiltros, offset\]\);/);
  assert.doesNotMatch(view, /location\.reload/);
});

test("KPIs: continuam do departamento inteiro (decisão antiga da tela) e não dependem dos filtros", () => {
  const view = ler("components/meu-departamento/MeuDepartamentoView.tsx");
  assert.match(view, /getResumoDepartamento\(departamentoHead\.id\)/);
  assert.match(view, /\}, \[podeAcessar, departamentoHead\]\);/);
  assert.match(view, /afetam só a lista/);
});

test("Responsável: opções do departamento ATUAL, recriadas quando o contexto muda (sem lista velha)", () => {
  const defs = ler("components/meu-departamento/useDefinicoesFiltrosMeuDepartamento.ts");
  assert.match(defs, /useUsuariosSelector\(\{ departamentoId \}\)/);
  assert.match(defs, /buscarOpcoes: async/);
  assert.match(defs, /resolverOpcoes: async/);
  assert.match(ler("components/meu-departamento/MeuDepartamentoView.tsx"), /departamentoId: departamentoHead\?\.id,/);
});

test("campos oferecidos refletem o domínio real: status e prioridade do produto, prazo com atalhos, origem sem 'não é'", () => {
  const defs = ler("components/meu-departamento/useDefinicoesFiltrosMeuDepartamento.ts");
  for (const campo of Object.keys(CAMPO_MEU_DEPARTAMENTO)) assert.ok(defs.includes(`CAMPO_MEU_DEPARTAMENTO.${campo}`), campo);
  assert.match(defs, /statusDemandaLabels/);
  assert.match(defs, /prioridadeDemandaLabels/);
  assert.match(defs, /PRESETS_DATA\.atrasado/);
  assert.match(defs, /multiplo: false,\s+permiteExcluir: false/);
  assert.doesNotMatch(defs, /Backlog|In Review|Andrew|Hotfix/);
});

test("API: o cliente HTTP envia as exclusões e aceita CSV; nenhum caller antigo muda", () => {
  const api = ler("lib/api-backend.ts");
  for (const nome of ["statusExcluir", "clienteIdExcluir", "projetoIdExcluir", "responsavelIdExcluir", "equipeIdExcluir", "prioridadeExcluir"]) {
    assert.ok(api.includes(`query.set("${nome}"`), nome);
  }
  assert.match(api, /prioridade\?: string;/);
});

// ── Fase 7C.2 — lista aberta por padrão ───────────────────────────────────────────────────────────────────────────

const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("7C.2: sem filtro de Status a lista é a operação em aberto; Status = Concluída/Cancelada pede o que terminou; remover volta às abertas", () => {
  assert.equal(listaMostraSoOperacaoAberta([]), true); // padrão
  assert.equal(listaMostraSoOperacaoAberta([{ campo: "cliente", operador: "is", valores: [A] }]), true); // outros filtros não mudam o padrão
  const concluida: FiltroAtivo[] = [{ campo: "status", operador: "is", valores: ["concluida"] }];
  assert.equal(listaMostraSoOperacaoAberta(concluida), false);
  assert.equal(listaMostraSoOperacaoAberta([{ campo: "status", operador: "in", valores: ["concluida", "cancelada"] }]), false);
  assert.equal(listaMostraSoOperacaoAberta([{ campo: "status", operador: "is", valores: [] }]), true);
  // o pedido explícito chega ao servidor como `status=...` (é isso que desliga o padrão no backend); o padrão não envia status
  assert.deepEqual(filtrosMeuDepartamentoParaApi(concluida, AGORA), { status: "concluida" });
  assert.deepEqual(filtrosMeuDepartamentoParaApi([{ campo: "status", operador: "in", valores: ["concluida", "cancelada"] }], AGORA), { status: "concluida,cancelada" });
  assert.deepEqual(filtrosMeuDepartamentoParaApi([], AGORA), {}); // sem filtro: nada de status → servidor aplica "em aberto"
});

test("7C.2: Status = Concluída fica na URL e sobrevive ao refresh; a regra de abertas NÃO é feita no navegador", () => {
  const defs: DefinicaoFiltro[] = [{ id: "status", label: "Status", tipo: "enum", opcoes: [{ value: "concluida", label: "Concluída" }, { value: "cancelada", label: "Cancelada" }] }];
  const filtros: FiltroAtivo[] = [{ campo: "status", operador: "is", valores: ["concluida"] }];
  const params = new URLSearchParams();
  for (const [nome, valor] of filtrosParaParametros(filtros)) params.set(nome, valor);
  assert.equal(params.get("status"), "is:concluida");
  const recarregada = new URLSearchParams(params.toString());
  assert.ok(filtrosIguais(decodificarFiltros((n) => recarregada.get(n), defs), filtros));
  const view = semComentarios(ler("components/meu-departamento/MeuDepartamentoView.tsx"));
  assert.doesNotMatch(view, /demandasPagina\.filter\(|\.filter\(\(demanda\) => .*status/); // nada de filtrar status localmente
  assert.doesNotMatch(view, /naoFinalizada/); // o padrão é do servidor (antes de limit/offset), não um parâmetro do cliente
  assert.match(view, /useFiltrosNaUrl\(definicoesFiltros, true\)/);
});

test("7C.2: escopo, KPIs e 'quem está trabalhando agora' intactos; Departamento continua não sendo filtro", () => {
  const view = semComentarios(ler("components/meu-departamento/MeuDepartamentoView.tsx"));
  assert.match(view, /escopo: "meu-departamento",\s+departamentoId: departamentoHead\.id,/);
  assert.match(view, /<EquipeAgoraCard key=\{departamentoHead\.id\} departamentoId=\{departamentoHead\.id\} \/>/);
  assert.match(view, /key: "concluidas", title: "Concluídas", value: valorIndicador\(resumo\?\.concluidas\)/); // KPI de concluídas preservado
  assert.equal("departamento" in CAMPO_MEU_DEPARTAMENTO, false);
  const status = semComentarios(ler("components/meu-departamento/useDefinicoesFiltrosMeuDepartamento.ts"));
  assert.match(status, /Object\.entries\(statusDemandaLabels\)/); // Concluída/Cancelada continuam entre as opções de Status
  assert.doesNotMatch(semComentarios(ler("components/meu-departamento/EquipeAgoraCard.tsx")), /status/i); // presença só por sessão real
});
