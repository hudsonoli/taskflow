// Colunas vazias recolhidas do Kanban (preferência visual). `npm run test:kanban-colunas`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { colunaRecolhida, colunaSobOPonteiro, LARGURA_COLUNA_RECOLHIDA_PX, rotuloDaColunaRecolhida, type EntradaDeRecolhimento } from "./kanban-colunas.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const base: EntradaDeRecolhimento = { recolherVazias: true, quantidade: 0, expandidaManual: false, expandidaPorArraste: false, congelada: null };
const com = (parcial: Partial<EntradaDeRecolhimento>): EntradaDeRecolhimento => ({ ...base, ...parcial });

test("vazia recolhe por padrão; com cards não recolhe; preferência desligada mantém tudo aberto", () => {
  assert.equal(colunaRecolhida(base), true);
  assert.equal(colunaRecolhida(com({ quantidade: 1 })), false);
  assert.equal(colunaRecolhida(com({ quantidade: 12 })), false);
  assert.equal(colunaRecolhida(com({ recolherVazias: false })), false);
});

test("expandir à mão mantém a vazia aberta", () => {
  assert.equal(colunaRecolhida(com({ expandidaManual: true })), false);
});

test("durante o arraste a decisão está congelada: a coluna que perde o último card NÃO colapsa no meio do gesto", () => {
  // início do arraste: a coluna tinha 1 card (aberta) → congelada=false; no meio do gesto a lista pode zerar, mas continua aberta
  assert.equal(colunaRecolhida(com({ quantidade: 0, congelada: false })), false);
  // depois do fim do arraste (sem congelamento) e sem cards → recolhe
  assert.equal(colunaRecolhida(com({ quantidade: 0, congelada: null })), true);
});

test("drag-over expande a recolhida (e ela fica aberta até o fim do gesto); passar sem soltar volta a recolher no fim", () => {
  assert.equal(colunaRecolhida(com({ congelada: true })), true); // atravessada? ainda não: segue recolhida
  assert.equal(colunaRecolhida(com({ congelada: true, expandidaPorArraste: true })), false); // o ponteiro entrou: abre
  assert.equal(colunaRecolhida(com({ congelada: null, expandidaPorArraste: false })), true); // fim do gesto sem soltar nela: recolhe de novo
});

test("soltar numa recolhida: ela passa a ter card e fica aberta (expandida à mão ao soltar, sem piscar enquanto a API atualiza)", () => {
  assert.equal(colunaRecolhida(com({ quantidade: 0, expandidaManual: true })), false); // assim que o gesto termina, antes da lista atualizar
  assert.equal(colunaRecolhida(com({ quantidade: 1, expandidaManual: true })), false); // depois que o card chega
});

test("coluna aberta no início do arraste continua aberta mesmo vazia (congelada) e a recolhida só abre se atravessada", () => {
  assert.equal(colunaRecolhida(com({ congelada: false, expandidaPorArraste: true })), false);
  assert.equal(colunaRecolhida(com({ congelada: true, expandidaPorArraste: false })), true);
});

test("colunaSobOPonteiro: acha a coluna sob o ponteiro e devolve null fora de todas", () => {
  const caixas = [
    { id: "a", left: 0, right: 56, top: 0, bottom: 300 },
    { id: "b", left: 68, right: 354, top: 0, bottom: 300 },
  ];
  assert.equal(colunaSobOPonteiro(30, 100, caixas), "a");
  assert.equal(colunaSobOPonteiro(200, 100, caixas), "b");
  assert.equal(colunaSobOPonteiro(60, 100, caixas), null); // vão entre colunas
  assert.equal(colunaSobOPonteiro(30, 400, caixas), null);
});

test("nome acessível da coluna recolhida preserva o título completo e a contagem", () => {
  assert.equal(rotuloDaColunaRecolhida("Aguardando cliente", 0), "Aguardando cliente — 0 tarefas. Clique para expandir.");
  assert.equal(rotuloDaColunaRecolhida("Concluída", 1), "Concluída — 1 tarefa. Clique para expandir.");
  assert.ok(LARGURA_COLUNA_RECOLHIDA_PX >= 48 && LARGURA_COLUNA_RECOLHIDA_PX <= 64);
});

// ── apresentação e motor de arraste (source-scan) ──────────────────────────────────────────────────────────────────

test("o motor dnd-kit e as regras operacionais NÃO foram tocados: handleDragEnd, sensores, expediente e iniciar trabalho", () => {
  const board = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(board, /const sensors = useSensors\(useSensor\(PointerSensor, \{ activationConstraint: \{ distance: 8 \} \}\)\);/);
  assert.match(board, /function handleDragEnd\(event: DragEndEvent\) \{\s*setActiveId\(null\);\s*const \{ active, over \} = event;/);
  // a decisão do que chamar ao soltar agora é a função pura `decidirSoltura` (lib/kanban-soltura.ts, com testes próprios); o handleDragEnd só a executa
  assert.match(board, /const decisao = decidirSoltura\(\{[\s\S]*?podeIniciarNoExpediente: expediente\.podeIniciar,\s*\}\);/);
  assert.match(board, /if \(decisao\.acao === "nada"\) return;/);
  assert.match(board, /if \(decisao\.acao === "bloqueado-expediente"\) \{\s*setAvisoBloqueio\(MOTIVO_INICIAR_FORA_EXPEDIENTE\);/);
  assert.match(board, /if \(decisao\.acao === "iniciar-trabalho"\) onIniciarTrabalho\(demanda\.id\);\s*else onMoveDemanda\(demanda\.id, decisao\.novoStatus\);/);
  assert.doesNotMatch(board, /collisionDetection|useSortable|SortableContext/); // nenhum motor novo
  const coluna = semComentarios(ler("components/demandas/DemandaKanbanColumn.tsx"));
  assert.match(coluna, /const \{ setNodeRef, isOver \} = useDroppable\(\{ id \}\);/); // a coluna recolhida continua registrada no dnd-kit
});

test("a coluna recolhida continua no DOM (só muda a largura), com nome acessível, tooltip e expansão por clique", () => {
  const coluna = semComentarios(ler("components/demandas/DemandaKanbanColumn.tsx"));
  assert.match(coluna, /ref=\{setNodeRef\}/);
  assert.match(coluna, /data-kanban-coluna=\{id\}/);
  assert.match(coluna, /rotuloDaColunaRecolhida\(title, demandas\.length\)/);
  assert.match(coluna, /aria-label=\{rotulo\}/);
  assert.match(coluna, /onClick=\{onExpandir\}/);
  assert.match(coluna, /motion-reduce:transition-none/);
  assert.doesNotMatch(coluna, /(?<![-\w])hidden(?![-\w])|display:\s*none/); // nunca some do DOM (overflow-hidden do rótulo é outra coisa)
});

test("a preferência 'Recolher colunas vazias automaticamente' é visual: ligada por padrão, em localStorage, sem backend", () => {
  const board = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(board, /usePreferenciaBooleana\("taskflow.kanban\.recolherColunasVazias", true\)/);
  assert.match(board, /Recolher colunas vazias automaticamente/);
  const pref = semComentarios(ler("lib/preferencia-visual.ts"));
  assert.match(pref, /window\.localStorage/);
  assert.match(pref, /catch/); // armazenamento indisponível não derruba a tela
  assert.doesNotMatch(pref + board, /fetch\(|api-backend/); // nenhuma chamada ao servidor
});

test("o arraste só ABRE colunas recolhidas (onDragMove) e a soltura numa vazia a deixa aberta; o fim do gesto limpa o estado temporário", () => {
  const board = semComentarios(ler("components/demandas/DemandasKanban.tsx"));
  assert.match(board, /onDragMove=\{aoArrastar\}/);
  assert.match(board, /colunaSobOPonteiro\(/);
  assert.match(board, /onDragEnd=\{aoSoltar\}/);
  assert.match(board, /onDragCancel=\{aoCancelar\}/);
  assert.match(board, /handleDragEnd\(event\);/); // o handler original continua sendo chamado, intacto
  assert.match(board, /setCongeladas\(null\)/);
});
