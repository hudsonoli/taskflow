// Fase 8B — Arquivos em lote. `npm run test:arquivos-lote`.
// Lógica pura exercitada de verdade; telas, API e proxy (.tsx/.ts com alias `@/`) são lidos como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  LIMITE_EXCLUIDOS,
  LIMITE_IDS_EXPLICITOS,
  alternarArquivo,
  confirmacaoDeExclusao,
  corpoDaSelecao,
  desmarcarPagina,
  deveOferecerTodosOsResultados,
  estaSelecionado,
  estadoDoCabecalho,
  nomeDoDownload,
  quantidadeSelecionada,
  removerDaSelecao,
  selecaoVazia,
  selecionarPagina,
  selecionarTodosOsResultados,
  textoDoContador,
} from "./selecao-arquivos.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const pagina = Array.from({ length: 5 }, (_, i) => `a${i + 1}`);

// ── checkbox individual e contador ────────────────────────────────────────────────────────────────────────────

test("checkbox individual: marca e desmarca por ID (não por posição) e conta", () => {
  let s = selecaoVazia();
  assert.equal(quantidadeSelecionada(s), 0);
  s = alternarArquivo(s, "a3");
  s = alternarArquivo(s, "a1");
  assert.equal(estaSelecionado(s, "a3"), true);
  assert.equal(estaSelecionado(s, "a2"), false);
  assert.equal(quantidadeSelecionada(s), 2);
  s = alternarArquivo(s, "a3");
  assert.equal(quantidadeSelecionada(s), 1);
});

test("contador: singular e plural", () => {
  assert.equal(textoDoContador(1), "1 selecionado");
  assert.equal(textoDoContador(3), "3 selecionados");
});

test("a seleção é imutável: alternar devolve outro objeto e não altera o anterior", () => {
  const antes = selecaoVazia();
  const depois = alternarArquivo(antes, "x");
  assert.notEqual(antes, depois);
  assert.equal(quantidadeSelecionada(antes), 0);
});

// ── selecionar página e indeterminado ─────────────────────────────────────────────────────────────────────────

test("selecionar página marca só os carregados; cabeçalho: nenhum → parcial → todos", () => {
  let s = selecaoVazia();
  assert.equal(estadoDoCabecalho(s, pagina), "nenhum");
  s = alternarArquivo(s, "a2");
  assert.equal(estadoDoCabecalho(s, pagina), "parcial"); // indeterminate
  s = selecionarPagina(s, pagina);
  assert.equal(estadoDoCabecalho(s, pagina), "todos");
  assert.equal(quantidadeSelecionada(s), 5);
  s = desmarcarPagina(s, pagina);
  assert.equal(estadoDoCabecalho(s, pagina), "nenhum");
  assert.equal(estadoDoCabecalho(s, []), "nenhum"); // página vazia nunca é "todos"
});

test("selecionar página NÃO é selecionar todos os resultados: o modo continua 'ids'", () => {
  const s = selecionarPagina(selecaoVazia(), pagina);
  assert.equal(s.modo, "ids");
  assert.equal(quantidadeSelecionada(s), 5);
});

test("a oferta 'Selecionar todos os N' só aparece com a página inteira marcada, total conhecido e maior que o carregado", () => {
  const marcada = selecionarPagina(selecaoVazia(), pagina);
  assert.equal(deveOferecerTodosOsResultados(marcada, pagina, 430), true);
  assert.equal(deveOferecerTodosOsResultados(marcada, pagina, null), false); // total ainda desconhecido: não assume
  assert.equal(deveOferecerTodosOsResultados(marcada, pagina, 5), false); // não há mais além da página
  assert.equal(deveOferecerTodosOsResultados(alternarArquivo(selecaoVazia(), "a1"), pagina, 430), false); // página não está inteira
  assert.equal(deveOferecerTodosOsResultados(selecionarTodosOsResultados(430), pagina, 430), false); // já está em "todos"
});

// ── todos os resultados do filtro + exceções ──────────────────────────────────────────────────────────────────

test("todos os resultados: não carrega IDs; só total e exceções; contador = total − exceções", () => {
  let s = selecionarTodosOsResultados(430);
  assert.equal(s.modo, "todos");
  assert.equal(quantidadeSelecionada(s), 430);
  assert.equal(estaSelecionado(s, "qualquer-id-de-pagina-nao-carregada"), true);
  s = alternarArquivo(s, "a2"); // desmarca um item → vira exceção
  assert.equal(estaSelecionado(s, "a2"), false);
  assert.equal(quantidadeSelecionada(s), 429);
  s = alternarArquivo(s, "a2"); // marca de novo → some a exceção
  assert.equal(quantidadeSelecionada(s), 430);
});

test("em 'todos', selecionar/desmarcar página mexe só nas exceções daquela página", () => {
  let s = selecionarTodosOsResultados(100);
  s = desmarcarPagina(s, pagina);
  assert.equal(quantidadeSelecionada(s), 95);
  assert.equal(estadoDoCabecalho(s, pagina), "nenhum");
  s = selecionarPagina(s, pagina);
  assert.equal(quantidadeSelecionada(s), 100);
});

test("tetos do contrato: acima deles a seleção fica intacta (a tela avisa)", () => {
  let s = selecaoVazia();
  for (let i = 0; i < LIMITE_IDS_EXPLICITOS; i += 1) s = alternarArquivo(s, `id${i}`);
  assert.equal(quantidadeSelecionada(s), LIMITE_IDS_EXPLICITOS);
  assert.equal(alternarArquivo(s, "um-a-mais"), s);
  assert.equal(quantidadeSelecionada(selecionarPagina(s, ["x1", "x2"])), LIMITE_IDS_EXPLICITOS);

  let t = selecionarTodosOsResultados(5000);
  for (let i = 0; i < LIMITE_EXCLUIDOS; i += 1) t = alternarArquivo(t, `ex${i}`);
  assert.equal(alternarArquivo(t, "ex-demais"), t);
});

// ── corpo do POST: contexto, filtros e exceções ───────────────────────────────────────────────────────────────

test("corpo 'ids': só IDs e contexto — filtros não viajam (o servidor recusaria a combinação)", () => {
  const corpo = corpoDaSelecao(alternarArquivo(selecaoVazia(), "a1"), {
    filtros: { search: "contrato", tipo: "layout" },
    contexto: { clienteId: "c1", projetoId: undefined },
  });
  assert.deepEqual(corpo, { mode: "ids", ids: ["a1"], contexto: { clienteId: "c1" } });
});

test("corpo 'all_filtered': filtros atuais + busca + contexto + exceções; sem IDs", () => {
  let s = selecionarTodosOsResultados(430);
  s = alternarArquivo(s, "a2");
  const corpo = corpoDaSelecao(s, {
    filtros: { search: "contrato", clienteId: "c1,c2", status: undefined, tipoExcluir: "link" },
    contexto: { projetoId: "p1" },
  });
  assert.deepEqual(corpo, {
    mode: "all_filtered",
    excludedIds: ["a2"],
    filtros: { search: "contrato", clienteId: "c1,c2", tipoExcluir: "link" },
    contexto: { projetoId: "p1" },
  });
  assert.equal("ids" in corpo, false);
});

test("sem filtros nem contexto os campos opcionais não existem no corpo", () => {
  assert.deepEqual(corpoDaSelecao(selecionarTodosOsResultados(3), { filtros: {} }), { mode: "all_filtered", excludedIds: [] });
});

test("a busca por nome faz parte do universo de 'todos': vai em filtros.search", () => {
  const corpo = corpoDaSelecao(selecionarTodosOsResultados(7), { filtros: { search: "contrato" } });
  assert.equal(corpo.mode === "all_filtered" && corpo.filtros?.search, "contrato");
});

// ── confirmação de exclusão ───────────────────────────────────────────────────────────────────────────────────

test("confirmação: texto por quantidade, aviso de irreversível e ciência extra só em 'todos'", () => {
  const c7 = confirmacaoDeExclusao(selecionarPagina(selecaoVazia(), pagina));
  assert.equal(c7.titulo, "Excluir 5 arquivos?");
  assert.equal(c7.aviso, "Esta ação não pode ser desfeita.");
  assert.equal(c7.exigeCiencia, false);
  assert.equal(confirmacaoDeExclusao(alternarArquivo(selecaoVazia(), "x")).titulo, "Excluir 1 arquivo?");

  const todos = confirmacaoDeExclusao(selecionarTodosOsResultados(430));
  assert.equal(todos.titulo, "Excluir todos os 430 arquivos encontrados?");
  assert.equal(todos.exigeCiencia, true);
  assert.match(todos.textoCiencia ?? "", /Entendo que todos os 430 arquivos deste filtro serão excluídos/);
});

// ── remoção após exclusão ─────────────────────────────────────────────────────────────────────────────────────

test("remover da seleção (ids): tira os excluídos; em 'todos': encolhe total e ajusta exceções", () => {
  const ids = removerDaSelecao(selecionarPagina(selecaoVazia(), pagina), ["a1", "a2"]);
  assert.equal(quantidadeSelecionada(ids), 3);
  let todos = alternarArquivo(selecionarTodosOsResultados(10), "a9"); // 9 selecionados
  todos = removerDaSelecao(todos, ["a1"]); // um selecionado foi excluído
  assert.equal(quantidadeSelecionada(todos), 8);
  todos = removerDaSelecao(todos, ["a9"]); // excluído um que era exceção: total encolhe, exceção some, selecionados intactos
  assert.equal(quantidadeSelecionada(todos), 8);
});

// ── nome do download ──────────────────────────────────────────────────────────────────────────────────────────

test("nome do download vem do Content-Disposition, validado; fallback seguro", () => {
  assert.equal(nomeDoDownload('attachment; filename="taskfloww-arquivos-20261010-1530.zip"'), "taskfloww-arquivos-20261010-1530.zip");
  assert.equal(nomeDoDownload(null), "taskfloww-arquivos.zip");
  assert.equal(nomeDoDownload('attachment; filename="../../x.zip"'), "taskfloww-arquivos.zip");
  assert.equal(nomeDoDownload('attachment; filename="virus.exe"'), "taskfloww-arquivos.zip");
});

// ── tela: filtros, contexto, permissões, paginação, stale ────────────────────────────────────────────────────

const tela = semComentarios(ler("components/arquivos/ArquivosContextView.tsx"));
const barra = semComentarios(ler("components/arquivos/ArquivosSelecaoBar.tsx"));

test("mudança de filtro/busca/contexto limpa a seleção (mesma comparação de chave que reinicia a lista); paginar não", () => {
  const bloco = tela.slice(tela.indexOf("if (chaveAtual !== chaveConsultada)"), tela.indexOf("const filtrosAtualRef"));
  assert.match(bloco, /setSelecao\(selecaoVazia\(\)\)/);
  const carregarMais = tela.slice(tela.indexOf("function carregarMais"), tela.indexOf("function recarregar()"));
  assert.doesNotMatch(carregarMais, /setSelecao/); // "Carregar mais" preserva a seleção explícita
  assert.match(carregarMais, /setItens\(\(atual\) => \[\.\.\.atual, \.\.\.resultado\]\)/);
});

test("chave dos filtros inclui busca, filtros avançados e o recorte fixo (Cliente/Projeto)", () => {
  assert.match(tela, /function chaveFiltros\(/);
  assert.match(tela, /clienteId: clienteId \?\? parametrosAvancados\.clienteId/);
  assert.match(tela, /projetoId: projetoId \?\? parametrosAvancados\.projetoId/);
});

test("universo do lote = mesmos filtros da listagem + contexto à parte (nunca ampliado)", () => {
  assert.match(tela, /filtros: \{ \.\.\.parametrosAvancados, search: busca \|\| undefined \}/);
  assert.match(tela, /contexto: \{ clienteId, projetoId \}/);
  assert.match(tela, /corpoDaSelecao\(selecao, universoDoLote\)/);
  // a lista inteira de IDs nunca é buscada no navegador para "todos": só o resumo (total)
  assert.match(tela, /resumoLoteArquivos\(corpoDaSelecao\(selecionarTodosOsResultados\(0\)/);
});

test("sem permissão de exclusão: a barra não oferece Excluir (só Baixar ZIP) e o modal recebe o mesmo flag", () => {
  assert.match(barra, /\{podeExcluir && \(\s*<Button[^>]*onClick=\{\(\) => setConfirmando\(true\)\}/);
  assert.match(tela, /podeExcluir = true/);
  assert.match(tela, /podeExcluir=\{podeExcluir\}/);
});

test("download: loading, sem clique duplo, mantém a seleção e o filtro; aviso dos links", () => {
  const baixar = tela.slice(tela.indexOf("async function baixarSelecao"), tela.indexOf("async function excluirSelecao"));
  assert.match(baixar, /if \(baixando\) return;/);
  assert.match(baixar, /setBaixando\(true\)/);
  assert.match(baixar, /finally \{\s*setBaixando\(false\);/);
  assert.doesNotMatch(baixar, /setSelecao/); // seleção mantida após o download
  assert.match(baixar, /linksIgnorados > 0/);
  assert.match(barra, /disabled=\{ocupado\}/);
  assert.match(barra, /Gerando ZIP…/);
});

test("exclusão: sucesso mantém filtros (refetch só em 'todos'); erro preserva a seleção", () => {
  const excluir = tela.slice(tela.indexOf("async function excluirSelecao"), tela.indexOf("return (\n    <div className=\"flex flex-col gap-6\">"));
  assert.match(excluir, /if \(excluindoLote\) return;/);
  assert.match(excluir, /setItens\(\(atual\) => atual\.filter/); // ids: remove localmente, sem voltar à primeira página
  assert.match(excluir, /recarregar\(\)/); // todos: refaz a consulta nos mesmos filtros/contexto
  const catchBloco = excluir.slice(excluir.indexOf("} catch (error)"), excluir.indexOf("} finally"));
  assert.doesNotMatch(catchBloco, /setSelecao/); // erro não perde a seleção
  assert.match(catchBloco, /setErroLote/);
});

test("stale response: ações e total comparam a chave dos filtros antes de aplicar o resultado", () => {
  assert.equal((tela.match(/chaveFiltros\(filtrosAtualRef\.current\) === chaveDoClique/g) ?? []).length >= 2, true);
  assert.match(tela, /chaveFiltros\(filtrosAtualRef\.current\) === chave\)/);
  assert.match(tela, /cancelado = true/);
});

test("barra: contador, Baixar ZIP, Excluir, Limpar; confirmação inline com ciência extra e aviso de irreversível", () => {
  assert.match(barra, /textoDoContador\(quantidade\)/);
  assert.match(barra, /Baixar ZIP/);
  assert.match(barra, /Limpar seleção/);
  assert.match(barra, /confirmacao\.exigeCiencia && !ciente/);
  assert.match(barra, /sticky bottom-4/);
  assert.match(barra, /aria-label="Ações da seleção"/);
  assert.match(barra, /aria-live="polite"/);
  assert.doesNotMatch(barra, /window\.confirm/);
});

test("acessibilidade: checkbox por cartão com rótulo, cabeçalho com estado indeterminado; checkbox é irmão do botão do cartão", () => {
  const card = semComentarios(ler("components/arquivos/ArquivoCard.tsx"));
  assert.match(card, /aria-label=\{`Selecionar \$\{arquivo\.nome\}`\}/);
  assert.match(card, /type="checkbox"/);
  assert.match(card, /<div className="relative">/); // wrapper: input e button são irmãos
  assert.match(tela, /indeterminate = estadoCabecalho === "parcial"/);
  assert.match(tela, /aria-label="Selecionar todos os arquivos carregados"/);
  assert.match(tela, /Selecionar todos os \{total\} arquivos encontrados/);
});

test("API: POSTs com corpo (sem IDs na URL); download lê Blob e valida o nome", () => {
  const api = ler("lib/api-backend.ts");
  assert.match(api, /"\/arquivos\/resumo-lote", \{ method: "POST", body: JSON\.stringify\(corpo\) \}/);
  assert.match(api, /"\/arquivos\/excluir-lote", \{ method: "POST", body: JSON\.stringify\(corpo\) \}/);
  assert.match(api, /\/api\/backend\/arquivos\/download-lote/);
  assert.match(api, /nomeDoDownload\(response\.headers\.get\("content-disposition"\)\)/);
  assert.match(api, /x-lote-links-ignorados/);
});

test("proxy: ZIP segue como stream (sem arrayBuffer) e repassa os cabeçalhos necessários", () => {
  const proxy = ler("app/api/backend/[...path]/route.ts");
  const bloco = proxy.slice(proxy.indexOf('contentType.includes("application/zip")'), proxy.indexOf('if (!contentType.includes("application/json"))'));
  assert.match(bloco, /new NextResponse\(backendResponse\.body/);
  assert.doesNotMatch(bloco, /arrayBuffer|\.text\(\)/);
  assert.match(bloco, /content-disposition/);
  assert.match(bloco, /x-lote-/);
});
