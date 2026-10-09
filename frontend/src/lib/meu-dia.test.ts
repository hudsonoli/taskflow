// Fase 7B — Meu Dia: a fila operacional PESSOAL. `npm run test:meu-dia` (node --test, sem dependências).
// Lógica pura exercitada de verdade; a tela e a API (.tsx/.ts com alias `@/`) são lidas como texto.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { ROTULO_FAIXA, STATUS_DA_FILA, faixaDaFila, fronteirasDoDia } from "./meu-dia.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const AGORA = new Date(2026, 9, 15, 14, 0); // 15/10/2026 14:00 (relógio local)
const em = (dias: number, hora = 16, minuto = 30) => new Date(2026, 9, 15 + dias, hora, minuto).toISOString();

// ── faixas ───────────────────────────────────────────────────────────────────────────────────────────────────────

test("faixas: sessão ativa > atrasada > vence hoje > prazo futuro > sem prazo", () => {
  assert.equal(faixaDaFila(em(5), true, AGORA), "execucao"); // sessão ativa manda, mesmo com prazo longe
  assert.equal(faixaDaFila(em(-1), false, AGORA), "atrasada");
  assert.equal(faixaDaFila(new Date(2026, 9, 15, 9, 0).toISOString(), false, AGORA), "atrasada"); // hoje, mas a hora já passou
  assert.equal(faixaDaFila(em(0, 16, 30), false, AGORA), "hoje");
  assert.equal(faixaDaFila(em(1), false, AGORA), "futura");
  assert.equal(faixaDaFila(null, false, AGORA), "sem_prazo");
  assert.equal(faixaDaFila(undefined, false, AGORA), "sem_prazo");
  assert.equal(faixaDaFila("não é data", false, AGORA), "sem_prazo");
});

test("'em execução agora' vem da SESSÃO, nunca do status", () => {
  const tela = ler("components/dashboard/DashboardView.tsx");
  assert.match(tela, /faixaDaFila\(demanda\.prazoEtapaAtual, emExecucaoIds\.has\(demanda\.id\), agoraDaConsulta\)/);
  assert.match(tela, /listarMinhasSessoesAtivas\(\)/);
  assert.doesNotMatch(semComentarios(tela), /status === "em_execucao"/); // nenhuma inferência por status
  assert.equal(ROTULO_FAIXA.execucao, "Em execução agora");
});

test("fronteiras do dia: 00:00:00.000 a 23:59:59.999 no relógio local, a partir de UMA referência", () => {
  const f = fronteirasDoDia(AGORA);
  assert.equal(f.agora, AGORA.toISOString());
  assert.equal(new Date(f.hojeInicio).getTime(), new Date(2026, 9, 15, 0, 0, 0, 0).getTime());
  assert.equal(new Date(f.hojeFim).getTime(), new Date(2026, 9, 15, 23, 59, 59, 999).getTime());
  for (const iso of Object.values(f)) assert.match(iso, /Z$/); // a API exige fuso
});

test("status da fila: os reais do produto, sem concluída, cancelada nem arquivada", () => {
  assert.deepEqual([...STATUS_DA_FILA], ["rascunho", "planejada", "em_execucao", "pausada", "bloqueada", "aguardando_cliente"]);
  for (const final of ["concluida", "cancelada", "arquivada"]) assert.equal((STATUS_DA_FILA as readonly string[]).includes(final), false, final);
});

// ── universo e segurança ────────────────────────────────────────────────────────────────────────────────────────

test("universo pessoal decidido no servidor: escopo=meus, sem id de usuário na consulta, sem filtrar só o que foi carregado", () => {
  const tela = semComentarios(ler("components/dashboard/DashboardView.tsx"));
  assert.match(tela, /escopo: "meus",\s+naoFinalizada: true,\s+sort: "fila_pessoal",/);
  assert.match(tela, /\.\.\.fronteirasDoDia\(agora\)/);
  assert.doesNotMatch(tela, /responsavelId|usuarioId|usuarioAtual\.id/); // nenhum id de usuário vai na consulta
  assert.doesNotMatch(tela, /demandas(?:Pagina)?\.filter\(/); // nunca filtra só a página carregada
  assert.doesNotMatch(tela, /setDemandas\b|AppDataContext\.demandas|useAppData\(\)\.demandas/); // sem o array limitado a 200
});

test("a autoridade do usuário não aparece na tela: Atendimento, Head e Gestor não mudam a consulta", () => {
  const tela = semComentarios(ler("components/dashboard/DashboardView.tsx"));
  assert.doesNotMatch(tela, /perfil|eh_atendimento|ehAtendimento|resolverHead|PERFIS|podeAcessar/);
  assert.match(tela, /podeCriarDemanda\(usuarioAtual, departamentoAtualNome\)/); // só decide se a bandeira é clicável (já era assim)
});

test("fila e filtros: não há 'Responsável' (o dia é fixo no próprio usuário) e os filtros refinam, sem trocar o dono", () => {
  const defs = ler("components/dashboard/useDefinicoesFiltrosMeuDia.ts");
  for (const campo of ["status", "cliente", "projeto", "prioridade", "prazo"]) assert.ok(defs.includes(`CAMPO_MEU_DEPARTAMENTO.${campo}`), campo);
  for (const proibido of ["responsavel", "equipe", "origem", "departamento"]) assert.equal(defs.includes(`CAMPO_MEU_DEPARTAMENTO.${proibido}`), false, proibido);
  assert.doesNotMatch(defs, /label: "Responsável"/);
  assert.match(defs, /STATUS_DA_FILA/); // status oferecidos = os da fila
  const tela = ler("components/dashboard/DashboardView.tsx");
  assert.match(tela, /useFiltrosNaUrl\(definicoesFiltros, true\)/);
  assert.match(tela, /<FiltrosAvancados definicoes=\{definicoesFiltros\} filtros=\{filtros\} onChange=\{definirFiltros\} \/>/);
});

// ── conteúdo da tela ────────────────────────────────────────────────────────────────────────────────────────────

test("sem movimentações recentes: nenhum feed de eventos/auditoria no Meu Dia", () => {
  const tela = ler("components/dashboard/DashboardView.tsx");
  assert.doesNotMatch(tela, /ovimenta[cç][õo]|Atividade recente|Últimos eventos|listEventos|getEventos|\/eventos/i);
});

test("indicadores pessoais e operacionais; nada de carteira, SLA ou projetos globais", () => {
  const tela = ler("components/dashboard/DashboardView.tsx");
  for (const rotulo of ["Minha fila", "Em andamento", "Pausadas", "Aguardando", "Atrasadas", "Vencem hoje"]) assert.ok(tela.includes(`label: "${rotulo}"`), rotulo);
  assert.doesNotMatch(semComentarios(tela), /SLA|carteira|fee|clientes da empresa|Concluídas"|Previstas para a semana/i);
  assert.match(tela, /getResumoMinhaHome\(limitesTemporais\(new Date\(\)\)\)/); // agregados no servidor, universo pessoal integral
});

test("cada atividade mostra tarefa, cliente, projeto, status, prioridade, prazo (data + horário) e departamento", () => {
  const tela = ler("components/dashboard/DashboardView.tsx");
  assert.match(tela, /rotuloDemanda\(demanda\)/);
  assert.match(tela, /cliente\?\.nome \?\? "Sem cliente"/);
  assert.match(tela, /resolverProjetoNome\(demanda\.projetoId, projetos\)/);
  assert.match(tela, /statusDemandaLabels\[demanda\.status\]/);
  assert.match(tela, /prioridadeDemandaLabels\[demanda\.prioridade\]/);
  assert.match(tela, /formatPrazo\(demanda\.prazoEtapaAtual\)/);
  assert.match(tela, /demanda\.departamentoResponsavelIds/);
  // o prazo da Fase 7A (instante) mostra a hora
  assert.match(ler("lib/demandas.ts"), /\.\.\.\(hasTime \? \{ hour: "2-digit", minute: "2-digit" \} : \{\}\)/);
});

test("paginação: mesmo escopo e filtros em todas as páginas; filtro novo volta à 1ª página; resposta antiga é descartada", () => {
  const tela = ler("components/dashboard/DashboardView.tsx");
  assert.match(tela, /limit: TAMANHO_PAGINA,\s+offset,/);
  assert.match(tela, /if \(chaveFiltros !== chaveFiltrosVista\) \{[\s\S]*setOffset\(0\);/);
  assert.match(tela, /if \(cancelado\) return;/);
  assert.match(tela, /\}, \[usuarioAtual, parametrosFiltros, offset, refetchTick\]\);/);
});

test("API: a ordenação e as fronteiras viajam na consulta; a sessão ativa é consultada só do próprio usuário (sem parâmetro)", () => {
  const api = ler("lib/api-backend.ts");
  assert.match(api, /"fila_pessoal"/);
  for (const nome of ["agora", "hojeInicio", "hojeFim"]) assert.ok(api.includes(`query.set("${nome}"`), nome);
  const sessao = api.slice(api.indexOf("export async function listarMinhasSessoesAtivas"), api.indexOf("export type MembroEquipeAgora"));
  assert.match(sessao, /"\/sessoes-trabalho\/minhas-ativas"/);
  assert.doesNotMatch(sessao, /usuarioId|\?/); // sem parâmetro: ninguém consulta a sessão de outra pessoa
});
