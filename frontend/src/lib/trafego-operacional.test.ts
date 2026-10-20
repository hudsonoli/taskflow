// Tráfego V2 — UI de AGORA e GARGALOS. `npm run test:trafego-operacional` (node --test, sem DOM): lógica pura exercitada de verdade; telas (alias `@/`) lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  INTERVALO_POLLING_AGORA_MS,
  PERIODOS_GARGALOS,
  PERIODO_GARGALOS_PADRAO,
  PERIODO_MAXIMO_DIAS,
  ROTULO_TEMPO,
  TEXTO_TRUNCADA,
  TEXTO_VAZIO_AGORA,
  TrafegoOperacionalErro,
  VISAO_PADRAO,
  VISOES_TRAFEGO,
  avisoCobertura,
  avisoFilaSemEtapa,
  avisoSemEtapaAtual,
  clienteEProjeto,
  criarPoller,
  estadoRemotoInicial,
  formatarDuracao,
  formatarPrazo,
  gargalosVazio,
  idadeAtualSegundos,
  intervaloDoPeriodo,
  kpisDoAgora,
  linhaDoAgora,
  linhasDaFila,
  linhasDeGargalo,
  mediaComAmostra,
  mensagemDeErro,
  periodoGargalosDaUrl,
  reduzirRemoto,
  rotuloDepartamentos,
  textosDaLinha,
  visaoDaUrl,
} from "./trafego-operacional.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "");

const H = 3600;
const MIN = 60;
const DIA = 86_400;

// ── fixtures ─────────────────────────────────────────────────────────────────────────────────────────────────

const dep = (id: string, nome: string) => ({ id, nome });
const demanda = (extra: Record<string, unknown> = {}) => ({
  demandaId: "d1",
  codigoReferencia: "T26000001",
  numeroOperacional: 2063,
  identificador: "#2063",
  titulo: "Banner Halloween",
  projeto: { id: "p1", nome: "Halloween 2026" },
  cliente: { id: "c1", nome: "Goiânia Shopping" },
  etapaAtual: { id: "e1", nome: "Redação", tipo: "execucao", departamentos: [dep("a", "Criação")] },
  responsaveis: [{ usuarioId: "u1", nome: "João" }],
  origemResponsaveis: "etapa_atual" as const,
  status: "em_execucao",
  inicioEstadoAtual: "2026-10-14T07:00:00Z",
  idadeEstadoSegundos: 8 * H,
  prazo: "2026-10-14T20:00:00Z",
  atrasada: false,
  ...extra,
});

const definicao = (chave: string, nome: string, departamentos = [dep("a", "Criação")], tipo = "execucao") => ({ chave, nome, tipo, departamentos });
const etapaGargalo = (extra: Record<string, unknown> = {}) => ({
  definicaoEtapa: definicao("k1", "Redação"),
  n: 12,
  nExecucao: 12,
  tempoExecucaoTotalSegundos: 12 * (84 * MIN),
  tempoExecucaoMedioSegundos: 84 * MIN,
  tempoExecucaoMaiorSegundos: 3 * H,
  nPausado: 2,
  tempoPausadoTotalSegundos: 2 * H,
  tempoPausadoMedioSegundos: H,
  tempoPausadoMaiorSegundos: H + 30 * MIN,
  nBloqueado: 0,
  tempoBloqueadoTotalSegundos: 0,
  tempoBloqueadoMedioSegundos: null,
  tempoBloqueadoMaiorSegundos: null,
  nAguardandoCliente: 1,
  tempoAguardandoClienteTotalSegundos: 2 * DIA + 3 * H,
  tempoAguardandoClienteMedioSegundos: 2 * DIA + 3 * H,
  tempoAguardandoClienteMaiorSegundos: 2 * DIA + 3 * H,
  ...extra,
});
const filaEtapa = (extra: Record<string, unknown> = {}) => ({
  definicaoEtapa: definicao("k1", "Redação"),
  wip: 3,
  planejadas: 0,
  emExecucao: 1,
  pausadas: 0,
  bloqueadas: 1,
  aguardandoCliente: 1,
  maisAntigaDesde: "2026-10-12T00:00:00Z",
  maisAntigaSegundos: 2 * DIA + 15 * H,
  maisAntigaTruncadaPelaMedicao: false,
  idadeEstadoMaisAntigoSegundos: 2 * DIA + 5 * H,
  ...extra,
});

// ── formatador único de durações ─────────────────────────────────────────────────────────────────────────────

test("formatarDuracao: <1 min, minutos, horas, dias — sem segundos e sem casas decimais, sempre por PISO", () => {
  const casos: Array<[number | null | undefined, string]> = [
    [0, "<1 min"],
    [59, "<1 min"],
    [60, "1 min"],
    [34 * MIN, "34 min"],
    [59 * MIN + 59, "59 min"], // piso: nunca arredonda para cima
    [H, "1h"],
    [2 * H + 15 * MIN, "2h 15min"],
    [8 * H, "8h"],
    [23 * H + 59 * MIN, "23h 59min"],
    [24 * H, "1d"],
    [2 * DIA + 3 * H, "2d 3h"],
    [2 * DIA + 3 * H + 59 * MIN, "2d 3h"], // dias+horas: minutos ficam de fora
    [-30, "<1 min"],
    [null, "—"],
    [undefined, "—"],
  ];
  for (const [entrada, esperado] of casos) assert.equal(formatarDuracao(entrada), esperado, String(entrada));
});

test("mediaComAmostra: a média NUNCA aparece sem o denominador (n)", () => {
  assert.deepEqual(mediaComAmostra(84 * MIN, 12), { valor: "1h 24min", amostra: "12 itens" });
  assert.deepEqual(mediaComAmostra(30 * MIN, 1), { valor: "30 min", amostra: "1 item" });
  assert.deepEqual(mediaComAmostra(null, 0), { valor: "—", amostra: "0 itens" });
});

test("idadeAtualSegundos: parte da idade medida pelo servidor e só soma o que passou desde que a resposta chegou (sem refetch por segundo)", () => {
  assert.equal(idadeAtualSegundos(8 * H, 1_000_000, 1_000_000), 8 * H);
  assert.equal(idadeAtualSegundos(8 * H, 1_000_000, 1_000_000 + 90_000), 8 * H + 90);
  assert.equal(idadeAtualSegundos(8 * H, 2_000_000, 1_000_000), 8 * H); // relógio local atrás: nunca diminui
  assert.equal(idadeAtualSegundos(null, 0, 99_999_999), null); // sem intervalo aberto: não inventa idade
});

// ── AGORA ────────────────────────────────────────────────────────────────────────────────────────────────────

test("AGORA: 5 KPIs na ordem do produto; semEtapaAtual NÃO é KPI principal e vira só um aviso discreto quando > 0", () => {
  const kpis = kpisDoAgora({ emExecucao: 2, atrasadas: 1, vencemHoje: 3, semResponsavel: 4, semPrazo: 5, semEtapaAtual: 7 });
  assert.deepEqual(kpis.map((k) => [k.label, k.valor]), [["Em execução", 2], ["Atrasadas", 1], ["Vencem hoje", 3], ["Sem responsável", 4], ["Sem prazo", 5]]);
  assert.equal(kpis.length, 5);
  assert.equal(avisoSemEtapaAtual(0), null);
  assert.equal(avisoSemEtapaAtual(1), "1 tarefa aberta com o workflow concluído e sem etapa atual.");
  assert.equal(avisoSemEtapaAtual(7), "7 tarefas abertas com o workflow concluído e sem etapa atual.");
});

test("AGORA: cor semântica só quando há o que olhar (zero é neutro); atrasadas é o único crítico", () => {
  const zero = kpisDoAgora({ emExecucao: 0, atrasadas: 0, vencemHoje: 0, semResponsavel: 0, semPrazo: 0, semEtapaAtual: 0 });
  assert.deepEqual(zero.map((k) => k.tom), ["blue", "neutral", "neutral", "neutral", "neutral"]);
  const cheio = kpisDoAgora({ emExecucao: 1, atrasadas: 1, vencemHoje: 1, semResponsavel: 1, semPrazo: 1, semEtapaAtual: 0 });
  assert.deepEqual(cheio.map((k) => k.tom), ["blue", "red", "amber", "amber", "neutral"]);
});

test("AGORA: a linha mostra o tempo NO ESTADO e a atribuição — 8 h em execução com responsável João NUNCA vira 'João trabalhou 8h'", () => {
  const linha = linhaDoAgora(demanda() as never, { fuso: "America/Sao_Paulo", recebidoEmMs: 0, agoraMs: 0 });
  assert.equal(linha.tempoNoEstado, "8h");
  assert.deepEqual(linha.responsaveis, [{ id: "u1", nome: "João" }]);
  const texto = textosDaLinha(linha).join(" | ");
  assert.match(texto, /Tempo no estado atual: 8h/);
  assert.doesNotMatch(texto, /trabalh|executando|executou|horas de/i);
  assert.doesNotMatch(texto, /João[^|]*8h|8h[^|]*João/);
  assert.equal(ROTULO_TEMPO.execucao, "Tempo em execução");
});

test("AGORA: idade formatada avança com o relógio local (12 min → 1h 25min → 2d 3h)", () => {
  const contexto = (idade: number, passou = 0) => linhaDoAgora(demanda({ idadeEstadoSegundos: idade }) as never, { fuso: "America/Sao_Paulo", recebidoEmMs: 0, agoraMs: passou * 1000 });
  assert.equal(contexto(12 * MIN).tempoNoEstado, "12 min");
  assert.equal(contexto(85 * MIN).tempoNoEstado, "1h 25min");
  assert.equal(contexto(2 * DIA + 3 * H).tempoNoEstado, "2d 3h");
  assert.equal(contexto(10 * MIN, 5 * MIN).tempoNoEstado, "15 min"); // 5 min locais depois da resposta
  assert.equal(linhaDoAgora(demanda({ idadeEstadoSegundos: null }) as never, { fuso: "America/Sao_Paulo", recebidoEmMs: 0, agoraMs: 1 }).tempoNoEstado, "—");
});

test("AGORA: atrasada, sem prazo, sem responsável e sem etapa atual aparecem sem placeholder feio", () => {
  const atrasada = linhaDoAgora(demanda({ atrasada: true }) as never, { fuso: "America/Sao_Paulo", recebidoEmMs: 0, agoraMs: 0 });
  assert.equal(atrasada.atrasada, true);
  assert.equal(formatarPrazo(null, "America/Sao_Paulo"), "Sem prazo");
  assert.match(formatarPrazo("2026-10-14T20:00:00Z", "America/Sao_Paulo"), /^14\/10,? 17:00$/); // prazo na hora da EMPRESA (UTC-3), não do navegador
  const semDono = linhaDoAgora(demanda({ responsaveis: [], etapaAtual: null }) as never, { fuso: "America/Sao_Paulo", recebidoEmMs: 0, agoraMs: 0 });
  assert.deepEqual(semDono.responsaveis, []);
  assert.equal(semDono.etapa, null);
  assert.ok(textosDaLinha(semDono).includes("Sem etapa atual"));
});

test("AGORA: cliente em destaque, projeto como texto secundário; sem projeto não deixa buraco; sem cliente promove o projeto", () => {
  assert.deepEqual(clienteEProjeto({ cliente: { id: "c", nome: "Cliente A" }, projeto: { id: "p", nome: "Projeto X" } }), { principal: "Cliente A", secundario: "Projeto X" });
  assert.deepEqual(clienteEProjeto({ cliente: { id: "c", nome: "Cliente A" }, projeto: null }), { principal: "Cliente A", secundario: null });
  assert.deepEqual(clienteEProjeto({ cliente: null, projeto: { id: "p", nome: "Projeto X" } }), { principal: "Projeto X", secundario: null });
  assert.deepEqual(clienteEProjeto({ cliente: null, projeto: null }), { principal: null, secundario: null });
});

test("AGORA: estado vazio curto e sem celebração; os KPIs seguem visíveis (a lista vazia não derruba a tela)", () => {
  assert.equal(TEXTO_VAZIO_AGORA, "Nenhuma tarefa em execução agora.");
  const lista = ler("components/trafego/TrafegoAgoraLista.tsx");
  assert.match(lista, /linhas\.length === 0 \? \(\s*<EmptyState title=\{TEXTO_VAZIO_AGORA\}/);
  const visao = ler("components/trafego/TrafegoAgoraVisao.tsx");
  assert.match(visao, /<TrafegoAgoraKpis kpis=\{dados\.kpis\} \/>[\s\S]*<TrafegoAgoraLista/); // KPIs e lista no mesmo ramo: o vazio só afeta a lista
});

// ── estado remoto: loading, erro e polling sem flicker ───────────────────────────────────────────────────────

test("loading: a PRIMEIRA carga é skeleton; depois dela, atualizar mantém o conteúdo (polling sem flicker)", () => {
  let estado = estadoRemotoInicial<{ v: number }>();
  assert.deepEqual([estado.carregando, estado.dados, estado.erro], [true, null, null]);
  estado = reduzirRemoto(estado, { tipo: "buscar" });
  assert.equal(estado.carregando, true);
  estado = reduzirRemoto(estado, { tipo: "sucesso", dados: { v: 1 }, emMs: 10 });
  assert.deepEqual([estado.carregando, estado.atualizando, estado.dados?.v, estado.recebidoEmMs], [false, false, 1, 10]);
  // poll seguinte: NADA de skeleton e o dado antigo continua na tela até o novo chegar
  estado = reduzirRemoto(estado, { tipo: "buscar" });
  assert.deepEqual([estado.carregando, estado.atualizando, estado.dados?.v], [false, true, 1]);
  estado = reduzirRemoto(estado, { tipo: "sucesso", dados: { v: 2 }, emMs: 40_000 });
  assert.deepEqual([estado.dados?.v, estado.atualizando, estado.recebidoEmMs], [2, false, 40_000]);
});

test("erro: na primeira carga vira erro local; depois de haver dados, a falha mantém os dados e só expõe a mensagem", () => {
  let estado = reduzirRemoto(estadoRemotoInicial<{ v: number }>(), { tipo: "buscar" });
  estado = reduzirRemoto(estado, { tipo: "falha", mensagem: "x" });
  assert.deepEqual([estado.carregando, estado.dados, estado.erro], [false, null, "x"]);
  estado = reduzirRemoto(estado, { tipo: "sucesso", dados: { v: 1 }, emMs: 1 });
  assert.equal(estado.erro, null); // sucesso limpa o erro
  estado = reduzirRemoto(reduzirRemoto(estado, { tipo: "buscar" }), { tipo: "falha", mensagem: "queda" });
  assert.deepEqual([estado.dados?.v, estado.erro, estado.atualizando], [1, "queda", false]);
});

test("erros: 403 vira mensagem de acesso; 422 de filtros; o resto, mensagem genérica de carga (nunca o detalhe técnico)", () => {
  assert.match(mensagemDeErro(new TrafegoOperacionalErro("Acesso negado", 403)), /não tem acesso/);
  assert.match(mensagemDeErro(new TrafegoOperacionalErro("período", 422)), /filtros/);
  assert.match(mensagemDeErro(new TrafegoOperacionalErro("boom", 500)), /Não foi possível carregar/);
  assert.match(mensagemDeErro(new Error("rede")), /Não foi possível carregar/);
  assert.doesNotMatch(mensagemDeErro(new TrafegoOperacionalErro("Traceback...", 500)), /Traceback/);
});

test("polling: busca imediata, repete a cada 30 s, só com a aba visível e nunca sobrepõe requisições", async () => {
  assert.equal(INTERVALO_POLLING_AGORA_MS, 30_000);
  let chamadas = 0;
  let liberar = null as (() => void) | null;
  let visivel = true;
  let tick = null as (() => void) | null;
  let intervaloPedido = 0;
  let limpo = false;
  const poller = criarPoller({
    buscar: () => {
      chamadas += 1;
      return new Promise<void>((resolve) => {
        liberar = resolve;
      });
    },
    visivel: () => visivel,
    setIntervalo: (acao, ms) => {
      tick = acao;
      intervaloPedido = ms;
      return 1;
    },
    limparIntervalo: () => {
      limpo = true;
    },
  });
  poller.iniciar();
  assert.equal(chamadas, 1);
  assert.equal(intervaloPedido, 30_000);
  tick?.(); // ainda em voo: descartado
  assert.equal(chamadas, 1);
  liberar?.();
  await Promise.resolve();
  await Promise.resolve();
  visivel = false;
  tick?.(); // aba oculta: nada
  assert.equal(chamadas, 1);
  visivel = true;
  tick?.();
  assert.equal(chamadas, 2);
  liberar?.();
  await Promise.resolve();
  await Promise.resolve();
  poller.aoMudarVisibilidade(); // voltou à aba: atualiza
  assert.equal(chamadas, 3);
  poller.parar();
  assert.equal(limpo, true);
  poller.iniciar(); // reiniciável após parar
  assert.equal(chamadas === 3 || chamadas === 4, true);
});

test("polling: não usa websocket nem refetch por segundo — o hook liga UM poller de 30 s e o relógio local roda a cada 30 s", () => {
  const hook = semComentarios(ler("components/trafego/useTrafegoOperacional.ts"));
  assert.equal((hook.match(/getTrafegoOperacionalAgora\(/g) ?? []).length, 1);
  assert.equal((hook.match(/criarPoller\(/g) ?? []).length, 1);
  assert.doesNotMatch(hook, /WebSocket|EventSource/);
  const visao = semComentarios(ler("components/trafego/TrafegoAgoraVisao.tsx"));
  assert.match(visao, /useNow\(ATUALIZACAO_RELOGIO_MS\)/);
  assert.match(visao, /ATUALIZACAO_RELOGIO_MS = 30_000/);
  assert.doesNotMatch(visao, /useNow\(1000\)/);
});

// ── GARGALOS ─────────────────────────────────────────────────────────────────────────────────────────────────

test("GARGALOS: período padrão 30 dias, máximo 90 (coerente com o backend); valor desconhecido na URL volta ao padrão", () => {
  assert.equal(PERIODO_GARGALOS_PADRAO, "30d");
  assert.equal(PERIODO_MAXIMO_DIAS, 90);
  assert.ok(PERIODOS_GARGALOS.every((p) => p.dias <= 90));
  assert.equal(Math.max(...PERIODOS_GARGALOS.map((p) => p.dias)), 90);
  assert.equal(periodoGargalosDaUrl(null), "30d");
  assert.equal(periodoGargalosDaUrl("365d"), "30d");
  assert.equal(periodoGargalosDaUrl("7d"), "7d");
  const agora = new Date("2026-10-16T12:00:00Z");
  const { inicio, fim } = intervaloDoPeriodo("90d", agora);
  assert.equal(new Date(fim).getTime() - new Date(inicio).getTime(), 90 * 86_400_000);
  assert.equal(fim, "2026-10-16T12:00:00.000Z"); // com timezone (Z), como o backend exige
  assert.equal(new Date(fim).getTime() - new Date(intervaloDoPeriodo("30d", agora).inicio).getTime(), 30 * 86_400_000);
});

test("GARGALOS: cobertura parcial é um aviso discreto com a data de início da medição (não é erro); cobertura total não mostra nada", () => {
  const data = (iso: string) => `[${iso.slice(0, 10)}]`;
  assert.equal(avisoCobertura({ coberturaParcial: false, medicaoDesde: "2026-10-14T15:45:56Z" }, data), null);
  assert.equal(avisoCobertura({ coberturaParcial: true, medicaoDesde: "2026-10-14T15:45:56Z" }, data), "Dados operacionais disponíveis a partir de [2026-10-14].");
  assert.equal(avisoCobertura({ coberturaParcial: true, medicaoDesde: null }, data), "Ainda não há medição operacional registrada.");
  const visao = semComentarios(ler("components/trafego/TrafegoGargalosVisao.tsx"));
  assert.match(visao, /\{cobertura && \(\s*<p role="note"/); // aviso, não troca o conteúdo
});

test("GARGALOS: definição de etapa — departamentos múltiplos, único e nenhum; a chave opaca não vira texto visível", () => {
  assert.equal(rotuloDepartamentos([dep("a", "Criação"), dep("b", "Atendimento")]), "Criação + Atendimento");
  assert.equal(rotuloDepartamentos([dep("a", "Criação")]), "Criação");
  assert.equal(rotuloDepartamentos([]), "Sem departamento");
  const [linha] = linhasDeGargalo([etapaGargalo({ definicaoEtapa: definicao("hash-opaco", "Aprovação", [dep("a", "Criação"), dep("b", "Atendimento")], "aprovacao") }) as never], []);
  assert.equal(linha.departamentos, "Criação + Atendimento");
  const visivel = JSON.stringify({ ...linha, chave: undefined });
  assert.doesNotMatch(visivel, /hash-opaco/);
  for (const arquivo of ["TrafegoGargalosTabela.tsx", "TrafegoFilaTabela.tsx", "TrafegoGargalosVisao.tsx"]) {
    const fonte = semComentarios(ler(`components/trafego/${arquivo}`));
    assert.doesNotMatch(fonte, />\s*\{[^}]*chave[^}]*\}\s*</, arquivo); // a chave só serve de `key`
    // sem id materializado como identidade da linha; na visão, `workflowEtapaId` aparece UMA vez, só como PARÂMETRO do filtro de etapa (vindo do AGORA)
    assert.equal((fonte.match(/workflowEtapaId|etapaId/g) ?? []).length, arquivo === "TrafegoGargalosVisao.tsx" ? 1 : 0, arquivo);
  }
  assert.match(semComentarios(ler("components/trafego/TrafegoGargalosVisao.tsx")), /workflowEtapaId: etapa\?\.id \?\? null/);
});

test("GARGALOS: a média sempre vem com n; sem amostra vira '—'; WIP vem da fila pela mesma definição (0 se não há fila)", () => {
  const [com, sem] = linhasDeGargalo(
    [etapaGargalo() as never, etapaGargalo({ definicaoEtapa: definicao("k2", "Arte", []), n: 1, nExecucao: 0, tempoExecucaoMedioSegundos: null, tempoExecucaoMaiorSegundos: null }) as never],
    [filaEtapa({ wip: 3 }) as never],
  );
  assert.deepEqual([com.execucao.valor, com.execucao.amostra, com.execucao.maior, com.wip], ["1h 24min", "12 itens", "3h", 3]);
  assert.deepEqual([com.pausado.valor, com.pausado.amostra], ["1h", "2 itens"]);
  assert.deepEqual([com.aguardandoCliente.valor, com.aguardandoCliente.total], ["2d 3h", "2d 3h"]);
  assert.deepEqual([com.bloqueado.valor, com.bloqueado.amostra], ["—", "0 itens"]);
  assert.deepEqual([sem.execucao.valor, sem.execucao.maior, sem.wip, sem.departamentos], ["—", "—", 0, "Sem departamento"]);
});

test("GARGALOS: fila/WIP — estados atuais (bloqueada e aguardando cliente inclusos), só os não zerados; mais antiga ≥ quando truncada pela medição", () => {
  const [normal, truncada] = linhasDaFila([filaEtapa() as never, filaEtapa({ definicaoEtapa: definicao("k2", "Revisão", [dep("b", "Atendimento")], "aprovacao"), wip: 1, emExecucao: 0, bloqueadas: 0, aguardandoCliente: 0, planejadas: 1, maisAntigaTruncadaPelaMedicao: true }) as never]);
  assert.equal(normal.maisAntigaHa, "2d 15h");
  assert.equal(normal.truncada, false);
  assert.equal(normal.idadeEstadoMaisAntigo, "2d 5h");
  assert.deepEqual(normal.estados.map((e) => `${e.n} ${e.rotulo}`), ["1 em execução", "1 bloqueada", "1 aguardando cliente"]);
  assert.equal(truncada.truncada, true);
  assert.deepEqual(truncada.estados.map((e) => `${e.n} ${e.rotulo}`), ["1 planejada"]);
  assert.equal(TEXTO_TRUNCADA, "Esta atividade já estava nesta etapa quando a medição começou; a idade real pode ser maior.");
  const tabela = ler("components/trafego/TrafegoFilaTabela.tsx");
  assert.match(tabela, /title=\{TEXTO_TRUNCADA\}/);
  assert.match(tabela, /≥/); // idade truncada marcada como piso, nunca como erro
});

test("GARGALOS: avisos da fila sem etapa (workflow concluído × sem workflow) e estado vazio sem 'Sem gargalos!'", () => {
  assert.equal(avisoFilaSemEtapa({ workflowConcluido: 0, semWorkflow: 0 }), null);
  assert.equal(avisoFilaSemEtapa({ workflowConcluido: 2, semWorkflow: 1 }), "Também abertas, fora das etapas: 2 com o workflow concluído e sem etapa atual · 1 sem workflow.");
  const semEtapa = { n: 0, nExecucao: 0, tempoExecucaoTotalSegundos: 0, tempoExecucaoMedioSegundos: null, tempoExecucaoMaiorSegundos: null, nPausado: 0, tempoPausadoTotalSegundos: 0, nBloqueado: 0, tempoBloqueadoTotalSegundos: 0, nAguardandoCliente: 0, tempoAguardandoClienteTotalSegundos: 0 };
  assert.equal(gargalosVazio({ etapas: [], semEtapa }), true);
  assert.equal(gargalosVazio({ etapas: [etapaGargalo() as never], semEtapa }), false);
  assert.equal(gargalosVazio({ etapas: [], semEtapa: { ...semEtapa, n: 1 } }), false); // só tempo sem etapa: não é "vazio"
  const visao = semComentarios(ler("components/trafego/TrafegoGargalosVisao.tsx"));
  assert.doesNotMatch(visao, /Sem gargalos/i);
  assert.match(visao, /TEXTO_SEM_DADOS_SUFICIENTES : TEXTO_VAZIO_GARGALOS/);
});

test("GARGALOS: filtros — período, departamento, cliente, projeto e a etapa vinda do AGORA; uma requisição principal", () => {
  const filtros = semComentarios(ler("components/trafego/TrafegoGargalosFiltros.tsx"));
  for (const rotulo of ['label="Período"', 'label="Departamento"', 'label="Cliente"', 'label="Projeto"', "Remover filtro de etapa"]) assert.ok(filtros.includes(rotulo), rotulo);
  const visao = semComentarios(ler("components/trafego/TrafegoGargalosVisao.tsx"));
  assert.equal((visao.match(/useTrafegoGargalos\(/g) ?? []).length, 1); // UMA requisição principal por consulta
  assert.match(visao, /gperiodo/); // parâmetro próprio: não colide com o `periodo` da visão Tempo pessoal
  const hook = semComentarios(ler("components/trafego/useTrafegoOperacional.ts"));
  assert.equal((hook.match(/getTrafegoOperacionalGargalos\(/g) ?? []).length, 1);
  assert.match(hook, /controlador\.abort\(\)/); // consulta nova cancela a anterior
  const api = semComentarios(ler("lib/api.ts"));
  assert.match(api, /\/trafego\/operacional\/\$\{caminho\}/);
  for (const parametro of ["departamentoId", "clienteId", "projetoId", "workflowEtapaId"]) assert.ok(api.includes(`set("${parametro}"`), parametro);
});

// ── visões, legado e semântica do tempo ──────────────────────────────────────────────────────────────────────

test("visões: Agora é o padrão; valor desconhecido na URL abre Agora; Tempo pessoal é a aba secundária (última)", () => {
  assert.equal(VISAO_PADRAO, "agora");
  assert.equal(visaoDaUrl(null), "agora");
  assert.equal(visaoDaUrl("qualquer"), "agora");
  assert.equal(visaoDaUrl("gargalos"), "gargalos");
  assert.equal(visaoDaUrl("carga"), "carga");
  assert.equal(visaoDaUrl("pessoal"), "pessoal");
  assert.deepEqual(VISOES_TRAFEGO.map((v) => v.label), ["Agora", "Gargalos", "Carga", "Tempo pessoal"]);
  const shell = semComentarios(ler("components/trafego/TrafegoView.tsx"));
  assert.match(shell, /visao === "agora" && /);
  assert.match(shell, /visao === "carga" && <TrafegoCargaView \/>/); // a Carga só monta (e só pede dados) na aba dela
  assert.match(shell, /visao === "pessoal" && <TrafegoTempoPessoalView \/>/); // o legado só monta (e só pede dados) na aba dele
  assert.match(shell, /podeAcessarCentralTrafego\(usuarioAtual\)/); // mesmo gate de antes; o backend segue sendo a autoridade
});

test("legado preservado: a visão Tempo pessoal mantém TODOS os componentes e chamadas de sessão de antes (nada removido)", () => {
  const legado = ler("components/trafego/TrafegoTempoPessoalView.tsx");
  for (const peca of [
    "TempoOperacionalCard",
    "TrafegoAgoraTable",
    "TrafegoCargaDepartamentos",
    "TrafegoCargaEquipes",
    "TrafegoCargaUsuarios",
    "TrafegoFilters",
    "TrafegoIndicadoresDemandas",
    "TrafegoIniciarSessao",
    "TrafegoResumoCards",
    "getAgoraTrafegoSessoes",
    "getCargaTrafegoSessoes",
    "getIndicadoresTrafegoSessoes",
    "getResumoTrafegoSessoes",
  ]) {
    assert.ok(legado.includes(peca), peca);
  }
  assert.match(legado, /Não alimenta as métricas operacionais de Agora e Gargalos/);
});

test("tempo pessoal NÃO é usado como operacional: as visões novas não importam nada de sessões nem do legado", () => {
  for (const arquivo of ["TrafegoAgoraVisao.tsx", "TrafegoAgoraKpis.tsx", "TrafegoAgoraLista.tsx", "TrafegoGargalosVisao.tsx", "TrafegoGargalosFiltros.tsx", "TrafegoGargalosTabela.tsx", "TrafegoFilaTabela.tsx", "TrafegoEstados.tsx", "useTrafegoOperacional.ts"]) {
    const fonte = semComentarios(ler(`components/trafego/${arquivo}`));
    assert.doesNotMatch(fonte, /sessoes-trabalho|SessaoTrabalho|sessao-trabalho|getAgoraTrafegoSessoes|getCargaTrafegoSessoes|getIndicadoresTrafegoSessoes|getResumoTrafegoSessoes|TrafegoAgoraLinha|fecharSessao/, arquivo);
    assert.doesNotMatch(fonte, /:\s*any\b|\bas any\b/, arquivo); // sem `any`
  }
  const lib = semComentarios(ler("lib/trafego-operacional.ts"));
  assert.doesNotMatch(lib, /sessoes-trabalho|SessaoTrabalho/);
});

test("semântica: nenhum texto das visões novas fala em horas trabalhadas, 'trabalhou', 'executando' ou ranking/produtividade de pessoas", () => {
  const proibidos = /trabalhou|trabalhad[oa]s?\b|horas de trabalho|executando|executou|ranking|mais produtiv|produtividade|eficiência/i;
  const arquivos = ["TrafegoAgoraVisao.tsx", "TrafegoAgoraKpis.tsx", "TrafegoAgoraLista.tsx", "TrafegoGargalosVisao.tsx", "TrafegoGargalosFiltros.tsx", "TrafegoGargalosTabela.tsx", "TrafegoFilaTabela.tsx", "TrafegoEstados.tsx", "TrafegoView.tsx", "TrafegoHeader.tsx"];
  for (const arquivo of arquivos) {
    const fonte = semComentarios(ler(`components/trafego/${arquivo}`));
    // texto visível (literais JSX e strings): ignora o aviso explícito "não são horas trabalhadas", que NEGA a leitura errada
    const visivel = fonte.replace(/Não são horas trabalhadas por pessoas\.?/g, "").replace(/não horas trabalhadas por pessoas/g, "");
    assert.doesNotMatch(visivel, proibidos, arquivo);
  }
  const textos = [ROTULO_TEMPO.execucao, ROTULO_TEMPO.pausado, ROTULO_TEMPO.bloqueado, ROTULO_TEMPO.aguardandoCliente];
  assert.deepEqual(textos, ["Tempo em execução", "Tempo pausado", "Tempo bloqueado", "Aguardando cliente"]);
});

test("responsáveis são ATRIBUIÇÃO: a coluna avisa (tooltip) e nenhum rótulo diz que alguém está executando", () => {
  const lista = ler("components/trafego/TrafegoAgoraLista.tsx");
  assert.match(lista, /title=\{TEXTO_RESPONSAVEIS\}/);
  assert.match(lista, /title=\{TEXTO_TEMPO_NO_ESTADO\}/);
  assert.match(lista, /emptyLabel="Sem responsável"/);
});
