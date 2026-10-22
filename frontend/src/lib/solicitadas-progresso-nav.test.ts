// "Solicitadas por mim" (acompanhamento do criador), progresso da tarefa (battery segmentada) e ordem do menu. `npm run test:solicitadas` (node --test, sem dependências).
// A lógica de apresentação pura é exercitada de verdade; as telas (alias `@/`) são lidas como texto para provar o que os tipos não mostram: o servidor é a autoridade do percentual,
// a lista é filtrada no servidor, a visão não duplica páginas e Projetos fica logo depois de Tarefas.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { estadoDoProgresso, resumoDoProgresso, segmentosDoProgresso } from "./progresso-demanda.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

type Etapa = { id: string; nome: string; ordem: number; status: "pendente" | "em_execucao" | "pausada" | "concluida" };
const etapas = (...status: Etapa["status"][]): Etapa[] => status.map((s, i) => ({ id: `e${i + 1}`, nome: `Etapa ${i + 1}`, ordem: i + 1, status: s }));
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const demanda = (status: string, lista: Etapa[], atual: string | null, progresso: any) => ({ status, workflowEtapas: lista, etapaAtualId: atual, progresso }) as any;

test("segmentos: um por etapa na ordem do fluxo; concluída / atual / futura vêm do servidor, sem fração para a etapa em andamento", () => {
  const d = demanda("em_execucao", etapas("concluida", "concluida", "em_execucao", "pendente", "pendente"), "e3", { etapasTotal: 5, etapasConcluidas: 2, percentual: 40, semFluxo: false });
  assert.deepEqual(
    segmentosDoProgresso(d).map((s) => s.estado),
    ["concluida", "concluida", "atual", "futura", "futura"],
  );
  assert.equal(resumoDoProgresso(d.progresso), "2 de 5 etapas concluídas");
  assert.equal(resumoDoProgresso({ etapasTotal: 1, etapasConcluidas: 1, percentual: 100, semFluxo: false, etapaAtualId: null, etapaAtualNome: null }), "1 de 1 etapa concluída");
});

test("segmentos: etapa devolvida/rejeitada (status não concluído vindo do servidor) deixa de contar como concluída; fora de ordem é reordenado", () => {
  const embaralhada = [...etapas("concluida", "pendente", "pendente")].reverse();
  const d = demanda("em_execucao", embaralhada, "e2", { etapasTotal: 3, etapasConcluidas: 1, percentual: 33, semFluxo: false });
  assert.deepEqual(
    segmentosDoProgresso(d).map((s) => [s.nome, s.estado]),
    [
      ["Etapa 1", "concluida"],
      ["Etapa 2", "atual"],
      ["Etapa 3", "futura"],
    ],
  );
  const reaberta = demanda("em_execucao", etapas("pendente", "pendente"), "e1", { etapasTotal: 2, etapasConcluidas: 0, percentual: 0, semFluxo: false });
  assert.equal(segmentosDoProgresso(reaberta).filter((s) => s.estado === "concluida").length, 0);
});

test("tarefa concluída pinta todos os segmentos", () => {
  const d = demanda("concluida", etapas("concluida", "pendente"), null, { etapasTotal: 2, etapasConcluidas: 1, percentual: 100, semFluxo: false });
  assert.deepEqual(
    segmentosDoProgresso(d).map((s) => s.estado),
    ["concluida", "concluida"],
  );
});

test("estados: sem fluxo e cancelada não mostram barra (nunca 0% nem 100% inventados); bloqueada/aguardando/pausada preservam a barra com rótulo", () => {
  const base = { etapasTotal: 5, etapasConcluidas: 2, percentual: 40, semFluxo: false, etapaAtualId: "e3", etapaAtualNome: "Etapa 3" };
  assert.deepEqual(estadoDoProgresso(demanda("em_execucao", [], null, { ...base, etapasTotal: 0, etapasConcluidas: 0, percentual: null, semFluxo: true })), {
    rotulo: "Sem fluxo",
    mostrarBarra: false,
  });
  assert.deepEqual(estadoDoProgresso(demanda("em_execucao", [], null, undefined)), { rotulo: "Sem fluxo", mostrarBarra: false });
  assert.deepEqual(estadoDoProgresso(demanda("cancelada", [], null, base)), { rotulo: "Cancelada", mostrarBarra: false });
  assert.deepEqual(estadoDoProgresso(demanda("bloqueada", [], null, base)), { rotulo: "Bloqueada", mostrarBarra: true });
  assert.deepEqual(estadoDoProgresso(demanda("aguardando_cliente", [], null, base)), { rotulo: "Aguardando cliente", mostrarBarra: true });
  assert.deepEqual(estadoDoProgresso(demanda("pausada", [], null, base)), { rotulo: "Pausada", mostrarBarra: true });
  assert.deepEqual(estadoDoProgresso(demanda("em_execucao", [], null, base)), { rotulo: null, mostrarBarra: true });
});

test("o percentual é do SERVIDOR: a interface não calcula progresso (nada de divisão/arredondamento, tempo, estimativa ou sessão)", () => {
  for (const arquivo of ["lib/progresso-demanda.ts", "components/demandas/ProgressoDemanda.tsx", "components/demandas/DemandasSolicitadasTable.tsx"]) {
    const texto = semComentarios(ler(arquivo));
    assert.doesNotMatch(texto, /Math\.(round|floor|ceil)|\*\s*100|esforco|estimad|sessao|intervalo/i, arquivo);
  }
  const barra = semComentarios(ler("components/demandas/ProgressoDemanda.tsx"));
  assert.match(barra, /role="progressbar"/);
  assert.match(barra, /\{progresso\.percentual\}%/); // texto: não depende só da cor
  assert.match(barra, /role="tooltip"/);
});

test("contrato: progresso e acompanhamento vêm do servidor e o escopo 'solicitadas' é um filtro server-side derivado do usuário autenticado", () => {
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /DemandaEscopo = "meus" \| "meu-departamento" \| "atendimento" \| "pauta" \| "solicitadas"/);
  assert.match(api, /EscopoLeituraDemanda = "pauta" \| "acompanhamento"/);
  assert.match(api, /progresso: data\.progresso \?\? undefined/);
  assert.match(api, /acessoSomenteAcompanhamento: data\.acessoSomenteAcompanhamento === true/);
  const view = semComentarios(ler("components/demandas/DemandasView.tsx"));
  assert.match(view, /escopo: "solicitadas" as const/);
  assert.doesNotMatch(view, /criadoPorUsuarioId|criadorUsuarioId/); // nada de filtrar por autoria no navegador
});

test("a visão vive em Tarefas como contexto (sem página nova nem item de menu) e não mistura Meu Dia / Meu Departamento", () => {
  const view = semComentarios(ler("components/demandas/DemandasView.tsx"));
  assert.match(view, /Solicitadas por mim/);
  assert.match(view, /<Tabs tabs=\{ABAS_CONTEXTO\}/);
  assert.match(view, /<DemandasSolicitadasTable /);
  assert.match(view, /modoLeitura=\{contexto === "solicitadas" \? "acompanhamento" : undefined\}/);
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.doesNotMatch(nav, /Solicitadas/);
  const tabela = semComentarios(ler("components/demandas/DemandasSolicitadasTable.tsx"));
  for (const coluna of ["Solicitação", "Cliente / Projeto", "Status", "Etapa atual", "Responsável atual", "Prazo", "Progresso"]) assert.match(tabela, new RegExp(coluna), coluna);
  assert.doesNotMatch(tabela, /Editar|onEdit|Excluir/); // acompanhamento, não gestão
  for (const rota of ["meu-dia", "meu-departamento"]) assert.doesNotMatch(semComentarios(ler(`app/e/[slug]/${rota}/page.tsx`)), /solicitadas/i, rota);
});

test("o drawer entra em modo acompanhamento (leitura, escopo=acompanhamento) pelo pedido da visão OU pelo sinal do servidor", () => {
  const drawer = semComentarios(ler("components/demandas/DemandaDetailsDrawer.tsx"));
  assert.match(drawer, /modoLeitura \?\? \(demanda\?\.acessoSomenteAcompanhamento === true \? "acompanhamento" : undefined\)/);
  assert.match(drawer, /<LeituraDemandaProvider value=\{modoEfetivo\}>/);
});

test("Projetos fica imediatamente depois de Tarefas, sem mudar rota, ícone ou gate; uma única lista alimenta desktop e mobile", () => {
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.match(nav, /items\.splice\(indiceTarefas \+ 1, 0, \{ label: "Projetos", href: "\/projetos", icon: Kanban \}\)/);
  assert.match(nav, /if \(podeAcessarAreaAdministrativa\(usuarioAtual\)\) \{/);
  assert.equal((nav.match(/label: "Projetos"/g) ?? []).length, 1);
  assert.equal((nav.match(/buildNavItems\(/g) ?? []).length, 2); // definição + uma chamada: a mesma lista nas duas variantes
  assert.equal((nav.match(/navItems\.map/g) ?? []).length, 2); // desktop e mobile
  // ordem efetiva: Projetos é inserido DEPOIS da Pauta ter sido inserida após Tarefas → Tarefas, Projetos, Pauta
  assert.ok(nav.indexOf('label: "Pauta"') < nav.indexOf('label: "Projetos"'));
});
