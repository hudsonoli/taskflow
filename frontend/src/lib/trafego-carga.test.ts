// Tráfego V2 — 11B.2B-C: testes da UI da CARGA semanal. `npm run test:trafego-carga` (node --test, sem DOM).
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";
import {
  LIMITE_DETALHE,
  TEXTOS_PROIBIDOS_NA_CARGA,
  algumNaoPlanejado,
  algumaPendencia,
  avisosDoPlanejamento,
  baldesDeNaoPlanejado,
  cabecalhoDaSemana,
  consultaDaCarga,
  diaNoFuso,
  estadoVazioDaCarga,
  explicacaoCapacidadeIndisponivel,
  formatarMinutos,
  formatarPercentual,
  indicadoresDoResumo,
  itemPrecisaDePlanejamento,
  linhaDaPessoa,
  linhaDoDepartamento,
  linhaDoItem,
  mensagemDeErroCarga,
  parametrosDoDetalhe,
  parametrosPrincipais,
  preenchimentoDaBarra,
  qualidadeDoPlanejamento,
  resumoDaCarga,
  rotuloDaJanela,
  rotuloDaOcupacao,
  rotuloDaOrigem,
  rotuloSemana,
  semEstimativaDoRecorte,
  somarDias,
  tomDaOcupacao,
} from "./trafego-carga.ts";
import { TrafegoOperacionalErro, VISOES_TRAFEGO } from "./trafego-operacional.ts";
import type { BucketCarga, CargaSemanal, DepartamentoCarga, FiltrosCarga, ItemEtapaCarga, PessoaCarga } from "../types/trafego-carga.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "");

const SEM_FILTRO: FiltrosCarga = { departamentoId: null, usuarioId: null };

// ── fixtures ─────────────────────────────────────────────────────────────────────────────────────────────────

const bucket = (extra: Partial<BucketCarga> = {}): BucketCarga => ({ etapasCount: 0, minutosConhecidos: 0, semEstimativaCount: 0, ...extra });
const pendencia = (extra: Partial<BucketCarga> = {}) => ({ ...bucket(extra), itens: [] as ItemEtapaCarga[], truncado: false });

const pessoa = (extra: Partial<PessoaCarga> = {}): PessoaCarga => ({
  usuarioId: "u1",
  nome: "Ana",
  departamentoId: "d1",
  capacidadeNominalMin: 1920,
  capacidadeAlocavelMin: 1920,
  planejadoMin: 0,
  saldoMin: 1920,
  ocupacaoPercentual: 0,
  naoPlanejadoMin: 0,
  pendenciasPlanejamentoMin: 0,
  semEstimativaCount: 0,
  ...extra,
});

const departamento = (extra: Partial<DepartamentoCarga> = {}): DepartamentoCarga => ({
  departamentoId: "d1",
  nome: "Criação",
  pessoasCount: 1,
  capacidadeNominalMin: 1920,
  capacidadeAlocavelMin: 1920,
  planejadoMin: 0,
  planejadoPoolMin: 0,
  saldoMin: 1920,
  ocupacaoPercentual: 0,
  naoPlanejadoMin: 0,
  pendenciasPlanejamentoMin: 0,
  semEstimativaCount: 0,
  ...extra,
});

const item = (extra: Partial<ItemEtapaCarga> = {}): ItemEtapaCarga => ({
  demandaId: "7f0c2d3e-0000-4000-8000-000000000001",
  identificador: "#2063",
  titulo: "Banner Halloween",
  statusDemanda: "em_execucao",
  cliente: { id: "c1", nome: "Goiânia Shopping" },
  projeto: { id: "p1", nome: "Halloween" },
  etapaId: "7f0c2d3e-0000-4000-8000-000000000002",
  etapaNome: "Redação",
  etapaTipo: "execucao",
  estimativaMin: 240,
  restanteMin: 240,
  planejadoNaSemanaMin: 120,
  parteMin: 60,
  janela: { planejadoInicio: "2026-10-20", planejadoFim: "2026-10-23", estado: "planejado" },
  alocacaoEstado: "alocada",
  motivoNaoPlanejado: null,
  origem: "responsavel",
  divididoEntre: 2,
  ...extra,
});

/** Semana atual (terça 20/10/2026), 1 pessoa, tudo planejado e estimado. */
const carga = (extra: Partial<CargaSemanal> = {}): CargaSemanal => ({
  meta: { agoraServidor: "2026-10-20T15:00:00Z", fusoEmpresa: "America/Sao_Paulo" },
  semana: { inicio: "2026-10-19", fim: "2026-10-25", recorteHoje: true, dias: [] },
  capacidade: { capacidadeIndisponivel: null, fatorAlocavelPercentual: 100 },
  pessoas: [pessoa()],
  departamentos: [departamento()],
  poolSemDepartamento: { etapasCount: 0, planejadoMin: 0, naoPlanejadoMin: 0, pendenciasPlanejamentoMin: 0, semEstimativaCount: 0 },
  naoPlanejado: { semJanela: bucket(), janelaIncompleta: bucket() },
  pendenciasPlanejamento: { janelaVencida: pendencia(), semDiaUtil: pendencia() },
  detalhe: null,
  ...extra,
});

/** Estado REAL de produção conhecido: 3 pessoas elegíveis (1920 min cada), 6 etapas sem estimativa e sem janela, nenhuma com responsável nem departamento. */
const cargaDeProducao = (): CargaSemanal =>
  carga({
    pessoas: [pessoa({ usuarioId: "u1", nome: "Ana", departamentoId: null }), pessoa({ usuarioId: "u2", nome: "Bia", departamentoId: null }), pessoa({ usuarioId: "u3", nome: "Caio", departamentoId: null })],
    departamentos: [],
    poolSemDepartamento: { etapasCount: 6, planejadoMin: 0, naoPlanejadoMin: 0, pendenciasPlanejamentoMin: 0, semEstimativaCount: 6 },
    naoPlanejado: { semJanela: bucket({ etapasCount: 6, minutosConhecidos: 0, semEstimativaCount: 6 }), janelaIncompleta: bucket() },
  });

// ── formatação ───────────────────────────────────────────────────────────────────────────────────────────────

test("formatarMinutos: um formatador só, sem decimais; negativo preserva o sinal; null é indisponível", () => {
  assert.equal(formatarMinutos(0), "0h");
  assert.equal(formatarMinutos(30), "30 min");
  assert.equal(formatarMinutos(480), "8h");
  assert.equal(formatarMinutos(510), "8h 30min");
  assert.equal(formatarMinutos(1920), "32h");
  assert.equal(formatarMinutos(-180), "-3h");
  assert.equal(formatarMinutos(-210), "-3h 30min");
  assert.equal(formatarMinutos(-45), "-45 min");
  assert.equal(formatarMinutos(null), "—");
  assert.doesNotMatch(formatarMinutos(1920), /[.,]\d/); // nunca "32,0h"
});

test("formatarPercentual: sem teto em 100, 1 casa só quando precisa", () => {
  assert.equal(formatarPercentual(0), "0%");
  assert.equal(formatarPercentual(75), "75%");
  assert.equal(formatarPercentual(100), "100%");
  assert.equal(formatarPercentual(128), "128%");
  assert.equal(formatarPercentual(87.5), "87,5%");
  assert.equal(formatarPercentual(null), "—");
});

// ── resumo ───────────────────────────────────────────────────────────────────────────────────────────────────

test("resumo: capacidade = soma das pessoas; planejado = pessoas + pool de departamento COM pessoas; sem dupla contagem", () => {
  const dados = carga({
    pessoas: [
      pessoa({ usuarioId: "u1", nome: "Ana", planejadoMin: 600, saldoMin: 1320, ocupacaoPercentual: 31.3 }),
      pessoa({ usuarioId: "u2", nome: "Bia", planejadoMin: 300, saldoMin: 1620, ocupacaoPercentual: 15.6 }),
    ],
    // O departamento INCLUI as pessoas: planejadoMin (900) = 600 + 300 + pool (120)? Aqui o pool é 120, logo planejadoMin = 1020.
    departamentos: [departamento({ pessoasCount: 2, capacidadeAlocavelMin: 3840, planejadoMin: 1020, planejadoPoolMin: 120, saldoMin: 2820 })],
  });
  const r = resumoDaCarga(dados);
  assert.equal(r.capacidadeMin, 3840);
  assert.equal(r.planejadoMin, 1020); // 600 + 300 + 120 — NÃO 1020 + 900
  assert.equal(r.planejadoMin, dados.departamentos[0].planejadoMin); // coincide com o total do departamento (que já inclui pessoas)
  assert.equal(r.saldoMin, 2820);
  assert.equal(r.ocupacaoPercentual, 26.6);
  assert.equal(r.tom, "normal");
});

test("resumo: pessoa sem departamento entra na capacidade global; o pool dela não existe", () => {
  const dados = carga({ pessoas: [pessoa({ departamentoId: null, planejadoMin: 960, saldoMin: 960, ocupacaoPercentual: 50 })], departamentos: [] });
  const r = resumoDaCarga(dados);
  assert.deepEqual([r.capacidadeMin, r.planejadoMin, r.saldoMin, r.ocupacaoPercentual], [1920, 960, 960, 50]);
});

test("sobrecarga: 128% não é truncado no texto; a barra limita só o preenchimento; disponível negativo aparece como -3h", () => {
  const dados = carga({ pessoas: [pessoa({ capacidadeAlocavelMin: 480, planejadoMin: 660, saldoMin: -180, ocupacaoPercentual: 137.5 })], departamentos: [] });
  const r = resumoDaCarga(dados);
  assert.equal(r.saldoMin, -180);
  assert.equal(r.tom, "sobrecarga");
  const [capacidade, planejado, disponivel, ocupacao] = indicadoresDoResumo(r, qualidadeDoPlanejamento(dados, SEM_FILTRO));
  assert.equal(capacidade.valor, "8h");
  assert.equal(planejado.valor, "11h");
  assert.equal(disponivel.valor, "-3h"); // não vira zero
  assert.equal(disponivel.tom, "sobrecarga");
  assert.equal(ocupacao.valor, "137,5%");
  const linha = linhaDaPessoa(dados.pessoas[0], "Criação");
  assert.equal(linha.disponivel, "-3h");
  assert.equal(linha.disponivelNegativo, true);
  assert.equal(linha.ocupacao.texto, "137,5%");
  assert.equal(linha.ocupacao.preenchimento, 100); // geometria limitada…
  assert.equal(preenchimentoDaBarra(128), 100);
  assert.equal(formatarPercentual(128), "128%"); // …texto não
});

test("tom da ocupação: normal, atenção perto do limite, sobrecarga acima de 100; sem capacidade e com carga é sobrecarga", () => {
  assert.equal(tomDaOcupacao(0, 0, 1920), "normal");
  assert.equal(tomDaOcupacao(75, 1440, 1920), "normal");
  assert.equal(tomDaOcupacao(90, 1728, 1920), "atencao");
  assert.equal(tomDaOcupacao(100, 1920, 1920), "atencao");
  assert.equal(tomDaOcupacao(125, 2400, 1920), "sobrecarga");
  assert.equal(tomDaOcupacao(null, null, null), "neutro");
  assert.equal(tomDaOcupacao(null, 120, 0), "sobrecarga");
});

test("capacidade indisponível (expediente desligado): nada de capacidade 0, nem ocupação inventada", () => {
  const dados = carga({
    capacidade: { capacidadeIndisponivel: "expediente_desligado", fatorAlocavelPercentual: 100 },
    pessoas: [pessoa({ capacidadeNominalMin: null, capacidadeAlocavelMin: null, planejadoMin: null, saldoMin: null, ocupacaoPercentual: null, semEstimativaCount: 2 })],
    departamentos: [departamento({ capacidadeNominalMin: null, capacidadeAlocavelMin: null, planejadoMin: null, planejadoPoolMin: null, saldoMin: null, ocupacaoPercentual: null })],
    naoPlanejado: { semJanela: bucket({ etapasCount: 2, semEstimativaCount: 2 }), janelaIncompleta: bucket() },
  });
  const q = qualidadeDoPlanejamento(dados, SEM_FILTRO);
  const r = resumoDaCarga(dados);
  assert.deepEqual([r.capacidadeMin, r.planejadoMin, r.saldoMin, r.ocupacaoPercentual], [null, null, null, null]);
  const textos = indicadoresDoResumo(r, q);
  assert.equal(textos[0].valor, "Indisponível"); // não "0h"
  assert.deepEqual(textos.slice(1).map((i) => i.valor), ["—", "—", "—"]);
  assert.match(explicacaoCapacidadeIndisponivel("expediente_desligado") ?? "", /controle de expediente está desativado/);
  const linha = linhaDaPessoa(dados.pessoas[0], "Criação");
  assert.deepEqual([linha.capacidade, linha.planejado, linha.disponivel, linha.ocupacao.texto], ["—", "—", "—", "—"]);
  assert.equal(linha.ocupacao.preenchimento, 0);
  // o planejamento que independe da capacidade continua visível
  assert.equal(q.incompleto, true);
  assert.equal(algumNaoPlanejado(dados), true);
  assert.match(avisosDoPlanejamento(q).join(" "), /2 etapas sem estimativa/);
});

// ── planejamento incompleto ──────────────────────────────────────────────────────────────────────────────────

test("produção atual (capacidade 1920 ×3, planejado 0, 6 sem estimativa, 6 sem janela): lê-se '0% conhecido' + alerta, nunca 'equipe livre'", () => {
  const dados = cargaDeProducao();
  const q = qualidadeDoPlanejamento(dados, SEM_FILTRO);
  const r = resumoDaCarga(dados);
  assert.equal(r.capacidadeMin, 5760);
  assert.equal(r.planejadoMin, 0);
  assert.equal(r.ocupacaoPercentual, 0);
  assert.equal(q.incompleto, true);
  assert.deepEqual(q.semEstimativa, { valor: 6, exato: true }); // pool sem departamento (6) — limite inferior = superior
  assert.equal(rotuloDaOcupacao(q), "Ocupação conhecida");
  const indicadores = indicadoresDoResumo(r, q);
  assert.equal(indicadores[3].rotulo, "Ocupação conhecida");
  assert.equal(indicadores[3].valor, "0%");
  const avisos = avisosDoPlanejamento(q);
  assert.ok(avisos.includes("6 etapas sem estimativa. A ocupação pode estar subestimada."), avisos.join("|"));
  assert.ok(avisos.some((a) => /6 etapas sem janela de planejamento completa/.test(a)));
  // nenhum texto produzido pela lib sugere equipe livre / sem sobrecarga
  const tudo = [...avisos, ...indicadores.flatMap((i) => [i.rotulo, i.valor, i.ajuda])].join("\n");
  for (const proibido of TEXTOS_PROIBIDOS_NA_CARGA) assert.doesNotMatch(tudo, proibido);
  assert.match(indicadores[2].ajuda, /pode ser menor com o planejamento completo/);
  // a UI mostra as linhas das pessoas com capacidade (não parece vazia)
  const linha = linhaDaPessoa(dados.pessoas[0], null);
  assert.deepEqual([linha.capacidade, linha.planejado, linha.disponivel, linha.ocupacao.texto], ["32h", "0h", "32h", "0%"]);
  assert.equal(estadoVazioDaCarga(dados, SEM_FILTRO), null);
});

test("planejamento completo: o rótulo volta a ser 'Ocupação' e não há aviso", () => {
  const dados = carga({ pessoas: [pessoa({ planejadoMin: 960, saldoMin: 960, ocupacaoPercentual: 50 })] });
  const q = qualidadeDoPlanejamento(dados, SEM_FILTRO);
  assert.equal(q.incompleto, false);
  assert.equal(rotuloDaOcupacao(q), "Ocupação");
  assert.deepEqual(avisosDoPlanejamento(q), []);
});

test("pendências: sem_janela, janela_incompleta, janela_vencida, sem_dia_util e sem estimativa NÃO entram na ocupação e geram aviso", () => {
  const dados = carga({
    pessoas: [pessoa({ planejadoMin: 480, saldoMin: 1440, ocupacaoPercentual: 25, naoPlanejadoMin: 900, pendenciasPlanejamentoMin: 300, semEstimativaCount: 1 })],
    naoPlanejado: { semJanela: bucket({ etapasCount: 2, minutosConhecidos: 600, semEstimativaCount: 1 }), janelaIncompleta: bucket({ etapasCount: 1, minutosConhecidos: 300 }) },
    pendenciasPlanejamento: { janelaVencida: pendencia({ etapasCount: 1, minutosConhecidos: 180 }), semDiaUtil: pendencia({ etapasCount: 1, minutosConhecidos: 120 }) },
  });
  const r = resumoDaCarga(dados);
  assert.equal(r.planejadoMin, 480); // os 900 + 300 de fora NÃO entram
  assert.equal(r.ocupacaoPercentual, 25);
  const q = qualidadeDoPlanejamento(dados, SEM_FILTRO);
  assert.deepEqual([q.semJanela, q.janelaIncompleta, q.janelaVencida, q.semDiaUtil, q.semEstimativa.valor], [2, 1, 1, 1, 1]);
  const avisos = avisosDoPlanejamento(q).join("\n");
  assert.match(avisos, /1 etapa sem estimativa\. A ocupação pode estar subestimada\./);
  assert.match(avisos, /3 etapas sem janela de planejamento completa/);
  assert.match(avisos, /1 etapa com janela vencida: precisa replanejar\./);
  assert.match(avisos, /1 etapa com janela sem capacidade disponível\./);
  assert.equal(algumNaoPlanejado(dados), true);
  assert.equal(algumaPendencia(dados), true);
  const baldes = baldesDeNaoPlanejado(dados);
  assert.deepEqual(baldes.map((b) => [b.id, b.etapas, b.minutos, b.semEstimativa]), [["sem_janela", 2, "10h", 1], ["janela_incompleta", 1, "5h", 0]]);
  const linha = linhaDaPessoa(dados.pessoas[0], "Criação");
  assert.equal(linha.aPlanejar, "20h"); // 900 + 300 mostrados SEPARADOS do planejado
  assert.equal(linha.planejado, "8h");
  assert.equal(linha.semEstimativa, 1);
});

test("sem estimativa global: com filtro é exato; sem filtro é limite inferior provado (e exato quando inferior = superior)", () => {
  // pool sem departamento (4) + uma pessoa com 1 sem estimativa que também aparece no seu departamento (1)
  const sem = carga({
    pessoas: [pessoa({ semEstimativaCount: 1 })],
    departamentos: [departamento({ semEstimativaCount: 1 })],
    poolSemDepartamento: { etapasCount: 4, planejadoMin: 0, naoPlanejadoMin: 0, pendenciasPlanejamentoMin: 0, semEstimativaCount: 4 },
  });
  assert.deepEqual(semEstimativaDoRecorte(sem, SEM_FILTRO), { valor: 5, exato: true }); // 4 + 1 (a pessoa já está no departamento: não soma duas vezes)
  assert.deepEqual(semEstimativaDoRecorte(sem, { departamentoId: "d1", usuarioId: null }), { valor: 1, exato: true });
  assert.deepEqual(semEstimativaDoRecorte(sem, { departamentoId: null, usuarioId: "u1" }), { valor: 1, exato: true });
  // a MESMA etapa sem estimativa atribuída a dois departamentos: somar daria 2 (errado); o limite inferior é 1 e a UI diz "pelo menos"
  const dois = carga({
    pessoas: [pessoa({ usuarioId: "u1", departamentoId: "d1", semEstimativaCount: 1 }), pessoa({ usuarioId: "u2", nome: "Bia", departamentoId: "d2", semEstimativaCount: 1 })],
    departamentos: [departamento({ departamentoId: "d1", semEstimativaCount: 1 }), departamento({ departamentoId: "d2", nome: "Mídia", semEstimativaCount: 1 })],
  });
  assert.deepEqual(semEstimativaDoRecorte(dois, SEM_FILTRO), { valor: 1, exato: false });
  const aviso = avisosDoPlanejamento(qualidadeDoPlanejamento(dois, SEM_FILTRO))[0];
  assert.match(aviso, /^Pelo menos 1 etapa sem estimativa\. A ocupação pode estar subestimada\.$/);
  assert.deepEqual(semEstimativaDoRecorte(carga(), SEM_FILTRO), { valor: 0, exato: true });
});

// ── pessoas ──────────────────────────────────────────────────────────────────────────────────────────────────

test("pessoas: 0%, 75%, 100%, 125%; planejado zero; planejado > capacidade; departamento null", () => {
  const casos: Array<[number, number, string, string]> = [
    [0, 0, "0%", "normal"],
    [1440, 75, "75%", "normal"],
    [1920, 100, "100%", "atencao"],
    [2400, 125, "125%", "sobrecarga"],
  ];
  for (const [planejado, pct, texto, tom] of casos) {
    const linha = linhaDaPessoa(pessoa({ planejadoMin: planejado, saldoMin: 1920 - planejado, ocupacaoPercentual: pct }), null);
    assert.equal(linha.ocupacao.texto, texto);
    assert.equal(linha.ocupacao.tom, tom);
    assert.equal(linha.departamento, null); // a tela mostra "Sem departamento"
    assert.equal(linha.disponivelNegativo, planejado > 1920);
  }
  assert.equal(linhaDaPessoa(pessoa({ planejadoMin: 2400, saldoMin: -480, ocupacaoPercentual: 125 }), null).disponivel, "-8h");
});

test("pessoas: capacidade null (indisponível) e capacidade 0 com carga ('Sem capacidade')", () => {
  const nula = linhaDaPessoa(pessoa({ capacidadeAlocavelMin: null, planejadoMin: null, saldoMin: null, ocupacaoPercentual: null }), "Criação");
  assert.equal(nula.capacidade, "—");
  assert.equal(nula.ocupacao.tom, "neutro");
  const zero = linhaDaPessoa(pessoa({ capacidadeAlocavelMin: 0, planejadoMin: 120, saldoMin: -120, ocupacaoPercentual: null }), "Criação");
  assert.equal(zero.ocupacao.texto, "Sem capacidade");
  assert.equal(zero.ocupacao.tom, "sobrecarga");
  assert.equal(zero.disponivel, "-2h");
});

test("pessoas: a ordem do servidor é preservada (sem ranking) e as linhas não carregam produtividade", () => {
  const nomes = ["Zeca", "Ana", "Bia"];
  const linhas = nomes.map((nome, i) => linhaDaPessoa(pessoa({ usuarioId: `u${i}`, nome, planejadoMin: i * 600, ocupacaoPercentual: i * 31 }), null));
  assert.deepEqual(linhas.map((l) => l.nome), nomes);
  assert.deepEqual(Object.keys(linhas[0]).sort(), ["aPlanejar", "capacidade", "departamento", "disponivel", "disponivelNegativo", "nome", "ocupacao", "planejado", "semEstimativa", "usuarioId"]);
});

// ── departamentos e pools ────────────────────────────────────────────────────────────────────────────────────

test("departamentos: planejadoPoolMin aparece à parte e NÃO é somado de novo ao planejado do departamento", () => {
  const d = departamento({ pessoasCount: 2, capacidadeAlocavelMin: 3840, planejadoMin: 1020, planejadoPoolMin: 120, saldoMin: 2820, ocupacaoPercentual: 26.6 });
  const linha = linhaDoDepartamento(d);
  assert.equal(linha.planejado, "17h"); // 1020 — o valor do servidor, que já inclui o pool
  assert.equal(linha.pool, "2h");
  assert.equal(linha.disponivel, "47h");
  assert.equal(linha.pessoas, 2);
  // pool zero → "—"
  assert.equal(linhaDoDepartamento(departamento({ planejadoPoolMin: 0 })).pool, null);
  // sobrecarga e disponível negativo no departamento
  const sobre = linhaDoDepartamento(departamento({ capacidadeAlocavelMin: 1920, planejadoMin: 2400, planejadoPoolMin: 480, saldoMin: -480, ocupacaoPercentual: 125 }));
  assert.equal(sobre.ocupacao.texto, "125%");
  assert.equal(sobre.disponivel, "-8h");
  assert.equal(sobre.disponivelNegativo, true);
});

test("pool de departamento SEM pessoas e pool sem departamento ficam FORA do resumo (sem denominador confiável)", () => {
  const dados = carga({
    pessoas: [pessoa({ planejadoMin: 480, saldoMin: 1440, ocupacaoPercentual: 25 })],
    departamentos: [
      departamento({ planejadoMin: 480, planejadoPoolMin: 0 }),
      departamento({ departamentoId: "d9", nome: "Vídeo", pessoasCount: 0, capacidadeAlocavelMin: 0, planejadoMin: 360, planejadoPoolMin: 360, saldoMin: -360, ocupacaoPercentual: null }),
    ],
    poolSemDepartamento: { etapasCount: 3, planejadoMin: 240, naoPlanejadoMin: 0, pendenciasPlanejamentoMin: 0, semEstimativaCount: 1 },
  });
  const r = resumoDaCarga(dados);
  assert.equal(r.capacidadeMin, 1920); // só pessoas elegíveis
  assert.equal(r.planejadoMin, 480); // pool de "Vídeo" (360) e pool sem departamento (240) NÃO diluem a capacidade
  assert.equal(r.ocupacaoPercentual, 25);
  assert.deepEqual(r.poolsSemCapacidade, [{ chave: "d9", nome: "Vídeo", planejadoMin: 360 }]);
  assert.equal(r.poolSemDepartamento?.etapasCount, 3);
  assert.equal(r.poolSemDepartamento?.semEstimativaCount, 1);
});

test("pool de departamento COM pessoas consome a capacidade das pessoas do departamento (entra no planejado global uma única vez)", () => {
  const dados = carga({
    pessoas: [pessoa({ planejadoMin: 480, saldoMin: 1440, ocupacaoPercentual: 25 })],
    departamentos: [departamento({ planejadoMin: 960, planejadoPoolMin: 480, saldoMin: 960, ocupacaoPercentual: 50 })],
  });
  const r = resumoDaCarga(dados);
  assert.equal(r.planejadoMin, 960);
  assert.equal(r.ocupacaoPercentual, 50);
  assert.deepEqual(r.poolsSemCapacidade, []);
});

test("pool sem departamento vazio não gera bloco", () => {
  assert.equal(resumoDaCarga(carga()).poolSemDepartamento, null);
  assert.equal(resumoDaCarga(carga({ poolSemDepartamento: null })).poolSemDepartamento, null);
});

// ── semana ───────────────────────────────────────────────────────────────────────────────────────────────────

test("semana atual: recorteHoje com aviso, 'anterior' desabilitado; semana futura: sem aviso, navegação livre", () => {
  const atual = cabecalhoDaSemana(carga());
  assert.equal(atual.rotulo, "19–25 out");
  assert.equal(atual.podeVoltar, false);
  assert.match(atual.aviso ?? "", /Capacidade restante da semana: considerando de hoje \(20\/10\) até domingo \(25\/10\)\./);
  assert.equal(atual.proxima, "2026-10-26");

  const futura = cabecalhoDaSemana(carga({ semana: { inicio: "2026-10-26", fim: "2026-11-01", recorteHoje: false, dias: [] } }));
  assert.equal(futura.rotulo, "26 out – 1 nov");
  assert.equal(futura.aviso, null);
  assert.equal(futura.podeVoltar, true);
  assert.equal(futura.anterior, "2026-10-19");
  assert.equal(futura.proxima, "2026-11-02");
});

test("semana: datas do calendário da EMPRESA, nunca o fuso do navegador (o 'hoje' vem do instante do servidor no fuso da empresa)", () => {
  // 21/10 02:30Z ainda é 20/10 em São Paulo (UTC-3)
  assert.equal(diaNoFuso("2026-10-21T02:30:00Z", "America/Sao_Paulo"), "2026-10-20");
  assert.equal(diaNoFuso("2026-10-21T02:30:00Z", "UTC"), "2026-10-21");
  assert.match(cabecalhoDaSemana(carga({ meta: { agoraServidor: "2026-10-21T02:30:00Z", fusoEmpresa: "America/Sao_Paulo" } })).aviso ?? "", /hoje \(20\/10\)/);
  assert.equal(somarDias("2026-10-26", -7), "2026-10-19");
  assert.equal(somarDias("2026-12-28", 7), "2027-01-04");
  assert.equal(rotuloSemana("2026-12-28", "2027-01-03"), "28 dez – 3 jan");
});

// ── consultas / contagem de requisições ──────────────────────────────────────────────────────────────────────

test("consulta principal: semana + filtros, NUNCA 'detalhe'; filtros são enviados ao servidor (o cliente não recalcula)", () => {
  assert.equal(consultaDaCarga(parametrosPrincipais(null, SEM_FILTRO)), "");
  assert.equal(consultaDaCarga(parametrosPrincipais("2026-10-26", SEM_FILTRO)), "semana=2026-10-26");
  assert.equal(consultaDaCarga(parametrosPrincipais(null, { departamentoId: "dep-1", usuarioId: null })), "departamentoId=dep-1");
  assert.equal(consultaDaCarga(parametrosPrincipais(null, { departamentoId: null, usuarioId: "usr-1" })), "usuarioId=usr-1");
  // pessoa e departamento são recortes excludentes: nunca vão juntos
  assert.equal(consultaDaCarga(parametrosPrincipais(null, { departamentoId: "dep-1", usuarioId: "usr-1" })), "usuarioId=usr-1");
  for (const consulta of [parametrosPrincipais("2026-10-26", { departamentoId: "d", usuarioId: null }), parametrosPrincipais(null, SEM_FILTRO)]) {
    assert.equal(consulta.detalhe, null);
    assert.doesNotMatch(consultaDaCarga(consulta), /detalhe/);
  }
});

test("cada troca de semana ou de filtro muda a chave da consulta (1 nova chamada); mesma entrada, mesma chave (nenhuma chamada extra)", () => {
  const chave = (semana: string | null, filtros = SEM_FILTRO) => JSON.stringify(parametrosPrincipais(semana, filtros));
  const base = chave(null);
  assert.equal(chave(null), base);
  assert.notEqual(chave("2026-10-26"), base);
  assert.notEqual(chave(null, { departamentoId: "d1", usuarioId: null }), base);
  assert.notEqual(chave(null, { departamentoId: null, usuarioId: "u1" }), base);
});

test("detalhe: UMA consulta por alvo, com semana, id e detalhe correspondentes; limite explícito", () => {
  const pessoaAlvo = parametrosDoDetalhe({ tipo: "usuario", id: "usr-1", nome: "Ana" }, "2026-10-19");
  assert.equal(consultaDaCarga(pessoaAlvo), `semana=2026-10-19&usuarioId=usr-1&detalhe=usuario&limite=${LIMITE_DETALHE}`);
  const depAlvo = parametrosDoDetalhe({ tipo: "departamento", id: "dep-1", nome: "Criação" }, "2026-10-26");
  assert.equal(consultaDaCarga(depAlvo), `semana=2026-10-26&departamentoId=dep-1&detalhe=departamento&limite=${LIMITE_DETALHE}`);
});

// ── itens ────────────────────────────────────────────────────────────────────────────────────────────────────

test("origem em linguagem de gestão (nunca o enum cru)", () => {
  assert.equal(rotuloDaOrigem("responsavel"), "Responsável");
  assert.equal(rotuloDaOrigem("pool_departamento"), "Pool do departamento");
  assert.equal(rotuloDaOrigem("pool_sem_departamento"), "Pool sem departamento");
  assert.equal(rotuloDaOrigem("algo_novo"), "Outra origem");
});

test("janela: '20/10 – 23/10', 'A partir de 20/10' (não é prazo), 'Sem janela'", () => {
  assert.equal(rotuloDaJanela({ planejadoInicio: "2026-10-20", planejadoFim: "2026-10-23" }), "20/10 – 23/10");
  assert.equal(rotuloDaJanela({ planejadoInicio: "2026-10-20", planejadoFim: null }), "A partir de 20/10");
  assert.equal(rotuloDaJanela({ planejadoInicio: null, planejadoFim: null }), "Sem janela");
});

test("item do detalhe: parte do alvo, total da etapa quando dividida, selos e ação 'Planejar'", () => {
  const dividido = linhaDoItem(item());
  assert.equal(dividido.naSemana, "1h");
  assert.equal(dividido.totalDaEtapaNaSemana, "2h");
  assert.equal(dividido.dividido, "Dividido entre 2");
  assert.equal(dividido.origem, "Responsável");
  assert.equal(dividido.janela, "20/10 – 23/10");
  assert.equal(dividido.estimativa, "4h");
  assert.deepEqual(dividido.selos.map((s) => s.texto), ["Planejada"]);
  assert.equal(dividido.precisaPlanejar, false);
  assert.equal(dividido.demanda, "#2063 — Banner Halloween");

  const inteiro = linhaDoItem(item({ divididoEntre: 1, planejadoNaSemanaMin: 240, parteMin: 240 }));
  assert.equal(inteiro.totalDaEtapaNaSemana, null);
  assert.equal(inteiro.dividido, null);
});

test("itens que precisam de planejamento ganham selo âmbar/vermelho e a ação 'Planejar'", () => {
  const semJanela = item({ estimativaMin: null, restanteMin: null, planejadoNaSemanaMin: null, parteMin: null, janela: { planejadoInicio: null, planejadoFim: null, estado: "nao_planejado" }, alocacaoEstado: null, motivoNaoPlanejado: "sem_janela" });
  assert.deepEqual(linhaDoItem(semJanela).selos.map((s) => s.texto), ["Sem janela", "Sem estimativa"]);
  assert.equal(linhaDoItem(semJanela).naSemana, null);
  assert.equal(linhaDoItem(semJanela).estimativa, "—"); // nunca "0h": o selo "Sem estimativa" explica

  const incompleta = item({ janela: { planejadoInicio: "2026-10-20", planejadoFim: null, estado: "incompleto" }, alocacaoEstado: null, motivoNaoPlanejado: "janela_incompleta", planejadoNaSemanaMin: null, parteMin: null });
  assert.deepEqual(linhaDoItem(incompleta).selos.map((s) => s.texto), ["Planejamento incompleto"]);
  assert.equal(linhaDoItem(incompleta).janela, "A partir de 20/10");

  const vencida = item({ alocacaoEstado: "janela_vencida", planejadoNaSemanaMin: null, parteMin: null });
  assert.deepEqual(linhaDoItem(vencida).selos.map((s) => [s.texto, s.tom]), [["Precisa replanejar", "vermelho"]]);

  const semDia = item({ alocacaoEstado: "sem_dia_util", planejadoNaSemanaMin: null, parteMin: null });
  assert.deepEqual(linhaDoItem(semDia).selos.map((s) => s.texto), ["Janela sem capacidade disponível"]);

  for (const precisa of [semJanela, incompleta, vencida, semDia]) assert.equal(itemPrecisaDePlanejamento(precisa), true);
  assert.equal(itemPrecisaDePlanejamento(item()), false);
  assert.equal(itemPrecisaDePlanejamento(item({ estimativaMin: null })), true);
});

test("item planejado em outras semanas não finge carga nesta", () => {
  const outra = linhaDoItem(item({ planejadoNaSemanaMin: 0, parteMin: 0 }));
  assert.deepEqual(outra.selos.map((s) => s.texto), ["Planejada em outras semanas"]);
  assert.equal(outra.naSemana, "0h");
});

// ── estados vazios e erros ───────────────────────────────────────────────────────────────────────────────────

test("estado vazio factual: sem pessoas elegíveis; com pessoas e nenhum planejamento NÃO é 'sem dados'", () => {
  const vazio = carga({ pessoas: [], departamentos: [] });
  assert.equal(estadoVazioDaCarga(vazio, SEM_FILTRO)?.titulo, "Não há pessoas elegíveis para capacidade.");
  assert.equal(estadoVazioDaCarga(vazio, { departamentoId: "d1", usuarioId: null })?.titulo, "Não há pessoas elegíveis para capacidade neste filtro.");
  assert.equal(estadoVazioDaCarga(carga(), SEM_FILTRO), null);
  assert.equal(estadoVazioDaCarga(cargaDeProducao(), SEM_FILTRO), null);
});

test("erros locais: 403, 404, 422 (semana) e genérico; 401 fica com o handler global", () => {
  assert.match(mensagemDeErroCarga(new TrafegoOperacionalErro("x", 403)), /restrita à gestão autorizada/);
  assert.match(mensagemDeErroCarga(new TrafegoOperacionalErro("x", 404)), /filtro escolhido não existe mais/);
  assert.match(mensagemDeErroCarga(new TrafegoOperacionalErro("x", 422)), /semana atual e as futuras/);
  assert.equal(mensagemDeErroCarga(new TrafegoOperacionalErro("x", 500)), "Não foi possível carregar a Carga semanal.");
  assert.equal(mensagemDeErroCarga(new Error("rede")), "Não foi possível carregar a Carga semanal.");
});

// ── rota / abas ──────────────────────────────────────────────────────────────────────────────────────────────

test("abas: Agora | Gargalos | Carga | Tempo pessoal, com ?visao=carga", () => {
  assert.deepEqual(VISOES_TRAFEGO.map((v) => [v.id, v.label]), [["agora", "Agora"], ["gargalos", "Gargalos"], ["carga", "Carga"], ["pessoal", "Tempo pessoal"]]);
});

// ── isolamento: tempo pessoal / operacional, polling, any, contrato ──────────────────────────────────────────

const ARQUIVOS_DA_CARGA = readdirSync(new URL("components/trafego/carga/", SRC)).map((nome) => `components/trafego/carga/${nome}`);

test("a Carga não importa nem consome sessões de trabalho nem intervalos operacionais; usa só getTrafegoCarga", () => {
  assert.ok(ARQUIVOS_DA_CARGA.length >= 8);
  for (const arquivo of [...ARQUIVOS_DA_CARGA, "lib/trafego-carga.ts", "types/trafego-carga.ts"]) {
    const fonte = semComentarios(ler(arquivo));
    assert.doesNotMatch(fonte, /sessoes-trabalho|SessaoTrabalho|sessao-trabalho|getAgoraTrafegoSessoes|getCargaTrafegoSessoes|getIndicadoresTrafegoSessoes|getResumoTrafegoSessoes|fecharSessao/, arquivo);
    assert.doesNotMatch(fonte, /demanda_status_intervalos|getTrafegoOperacionalAgora|getTrafegoOperacionalGargalos|TrafegoAgoraLinha|AgoraDemanda|GargaloEtapa|FilaEtapa|TrafegoOperacionalAgora|TrafegoOperacionalGargalos/, arquivo); // só os helpers genéricos de estado remoto/erro vêm de trafego-operacional
    assert.doesNotMatch(fonte, /:\s*any\b|\bas any\b/, arquivo); // sem `any`
    assert.doesNotMatch(fonte, /\bfetch\(/, arquivo); // nenhum componente fala com a API direto
    assert.doesNotMatch(fonte, /setInterval|criarPoller|WebSocket/, arquivo); // sem polling nem websocket
  }
  const hook = ler("components/trafego/carga/useTrafegoCarga.ts");
  assert.equal((hook.match(/getTrafegoCarga\(/g) ?? []).length, 1);
  const api = ler("lib/api.ts");
  assert.match(api, /getOperacional\("carga"/);
});

test("requisições: a visão principal chama o hook UMA vez; o detalhe só existe com um alvo (montado ao abrir); nada por linha", () => {
  const view = semComentarios(ler("components/trafego/carga/TrafegoCargaView.tsx"));
  assert.equal((view.match(/useTrafegoCarga\(/g) ?? []).length, 1);
  assert.match(view, /parametrosPrincipais\(semana, filtros\)/);
  assert.match(view, /\{alvo && dados && <CargaDetailDrawer/); // o drawer (e a chamada do detalhe) só monta com um alvo
  const drawer = semComentarios(ler("components/trafego/carga/CargaDetailDrawer.tsx"));
  assert.equal((drawer.match(/useTrafegoCarga\(/g) ?? []).length, 1);
  assert.match(drawer, /parametrosDoDetalhe\(alvo, semana\)/);
  for (const arquivo of ["CargaTabelas.tsx", "CargaItensTabela.tsx", "CargaPlanejamento.tsx", "CargaSummary.tsx"]) {
    assert.doesNotMatch(semComentarios(ler(`components/trafego/carga/${arquivo}`)), /useTrafegoCarga|getTrafegoCarga/, arquivo);
  }
  // atualização: ao entrar (efeito do hook), ao mudar semana/filtro (chave da consulta) e no botão — sem intervalo
  assert.match(view, /<CargaWeekNavigator[^>]*onAtualizar=\{atualizar\}/);
});

test("filtros: o cliente não filtra nem recalcula — os selects só trocam o estado que vira parâmetro da consulta", () => {
  const view = semComentarios(ler("components/trafego/carga/TrafegoCargaView.tsx"));
  assert.match(view, /setFiltros\(\{ departamentoId: evento\.target\.value \|\| null, usuarioId: null \}\)/);
  assert.match(view, /setFiltros\(\{ departamentoId: null, usuarioId: id \|\| null \}\)/);
  assert.doesNotMatch(view, /\.filter\(\(p\) =>|dados\.pessoas\.filter|dados\.departamentos\.filter/);
});

test("semana: o botão anterior usa podeVoltar (desabilitado na atual); a UI não calcula limites de semana com o fuso do navegador", () => {
  const nav = semComentarios(ler("components/trafego/carga/CargaWeekNavigator.tsx"));
  assert.match(nav, /disabled=\{cabecalho === null \|\| !cabecalho\.podeVoltar\}/);
  const lib = semComentarios(ler("lib/trafego-carga.ts"));
  assert.doesNotMatch(lib, /getTimezoneOffset|toLocaleDateString|new Date\(\)\.get(Day|Date)/);
  const view = semComentarios(ler("components/trafego/carga/TrafegoCargaView.tsx"));
  assert.doesNotMatch(view, /new Date\(/);
});

test("itens: a tabela não exibe UUID nem chave técnica (demandaId só serve à ação)", () => {
  const fonte = semComentarios(ler("components/trafego/carga/CargaItensTabela.tsx"));
  assert.doesNotMatch(fonte, /\{linha\.demandaId\}|[^=]\{linha\.chave\}|etapaId|statusDemanda/); // `chave` só como key de lista
  const itens = semComentarios(ler("lib/trafego-carga.ts"));
  assert.doesNotMatch(itens, /valor financeiro|custo|preco|preço/i);
});

test("semântica: os textos visíveis da Carga nunca falam em 'equipe livre', ranking, produtividade ou horas trabalhadas", () => {
  const proibidos = [...TEXTOS_PROIBIDOS_NA_CARGA, /ranking|mais produtiv|produtividade|medalha|melhor|pior/i];
  for (const arquivo of [...ARQUIVOS_DA_CARGA.filter((a) => a.endsWith(".tsx")), "lib/trafego-carga.ts"]) {
    // o aviso que NEGA a leitura errada ("não é tempo trabalhado") é permitido
    const visivel = semComentarios(ler(arquivo)).replace(/não é tempo trabalhado/g, "").replace(/Planejamento — não é tempo trabalhado/g, "");
    for (const proibido of proibidos) {
      // `TEXTOS_PROIBIDOS_NA_CARGA` é a própria lista de proibidos em lib/trafego-carga.ts: não a audita contra si mesma
      if (arquivo === "lib/trafego-carga.ts") continue;
      assert.doesNotMatch(visivel, proibido, `${arquivo}: ${proibido}`);
    }
  }
});
