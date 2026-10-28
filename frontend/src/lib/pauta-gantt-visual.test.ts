// P1_PAUTA_GANTT_VISUAL_REFINEMENT — apresentação da Pauta (source-scan + lógica pura do rótulo). `npm run test:pauta-gantt`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { rotuloDeResponsaveis, semIdentificadorTecnico, type PautaContexto } from "../components/pauta/pautaContexto.ts";
import type { PautaItem } from "../types/pauta-operacional.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const UUID = "493bb6d7-1d76-4d89-96e0-0f1c2d3e4f50";
const contexto = (visao: "colaborador" | "projeto"): PautaContexto => ({
  visao,
  nomeCliente: () => null,
  nomeProjeto: () => null,
  nomeDepartamento: (id) => `Depto ${id}`,
  nomePessoa: (id) => ({ u1: "Hudson de Oliveira", u2: "Raquel Cardozo" })[id] ?? "Usuário indisponível",
  emExecucaoIds: new Set(),
  onOpenDetails: () => undefined,
});
const item = (usuarioIds: string[], departamentoIds: string[] = []) =>
  ({ responsabilidadeEfetiva: { usuarioIds, departamentoIds, origem: "etapa" } }) as unknown as PautaItem;

test("o cabeçalho secundário foi removido: a página começa pela toolbar (h1 só para leitor de tela) e a navegação segue com o item Pauta", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.doesNotMatch(view, /Agenda operacional por etapa/);
  assert.doesNotMatch(view, /<motion\./);
  assert.match(view, /<h1 className="sr-only">Pauta<\/h1>/);
  assert.ok(view.indexOf("<h1") < view.indexOf("<PautaToolbar"));
  const nav = semComentarios(ler("components/layout/TopNav.tsx"));
  assert.equal((nav.match(/label: "Pauta"/g) ?? []).length, 1);
});

test("nenhum identificador técnico vira rótulo: cliente não resolvido não devolve a referência crua e o contexto descarta UUID", () => {
  const view = semComentarios(ler("components/pauta/PautaView.tsx"));
  assert.match(view, /nomeCliente: \(clienteId\) => \(clienteId && resolverClientePorReferencia\(clienteId, clientes\) \? resolverClienteNome\(clienteId, clientes\) : null\)/);
  assert.equal(semIdentificadorTecnico(UUID), null);
  assert.equal(semIdentificadorTecnico(`Cliente ${UUID}`), null);
  assert.equal(semIdentificadorTecnico("Projeto Piloto"), "Projeto Piloto");
  for (const arquivo of ["PautaGantt", "PautaLista"]) {
    const codigo = semComentarios(ler(`components/pauta/${arquivo}.tsx`));
    assert.doesNotMatch(codigo, /(?<!=)\{item\.(etapaId|demandaId|projetoId|clienteId)\}/, arquivo); // ids são chave/ação, nunca texto
  }
});

test("responsável sem a palavra 'Com': colaborador → só os colegas; projeto → todos; departamento continua explícito", () => {
  assert.equal(rotuloDeResponsaveis(item(["u1", "u2"]), contexto("colaborador"), "u1"), "Raquel Cardozo");
  assert.equal(rotuloDeResponsaveis(item(["u1"]), contexto("colaborador"), "u1"), null);
  assert.equal(rotuloDeResponsaveis(item(["u1", "u2"]), contexto("projeto")), "Hudson de Oliveira, Raquel Cardozo");
  assert.equal(rotuloDeResponsaveis(item([], ["d1"]), contexto("colaborador")), "Departamento: Depto d1");
});

test("linha do Gantt: duas linhas (etapa + prioridade / tarefa · responsável), altura compacta, painel de 20rem e abrir o detalhe como antes", () => {
  const gantt = semComentarios(ler("components/pauta/PautaGantt.tsx"));
  assert.match(gantt, /min-h-\[46px\]/);
  assert.match(gantt, /sm:\[--pauta-nome:20rem\]/);
  assert.match(gantt, /\{item\.etapaNome\}<\/span>\s*<PrioridadeTag prioridade=\{item\.prioridade\} \/>/);
  assert.match(gantt, /\{item\.demandaIdentificador\}<\/span>\s*\{item\.demandaNome\}\s*\{responsaveis && /);
  assert.equal((gantt.match(/<span className="block truncate/g) ?? []).length, 1); // só UMA linha secundária
  assert.doesNotMatch(gantt, /Com \$\{|"Com /);
  assert.match(gantt, /onClick=\{\(\) => contexto\.onOpenDetails\(item\.demandaId\)\}/);
});

test("cópia: 'Não planejada' discreta por linha, seção 'Não planejadas · N' sem caixa alta e grupo em uma linha", () => {
  const gantt = semComentarios(ler("components/pauta/PautaGantt.tsx"));
  assert.match(gantt, /Não planejada\s*<\/span>/);
  assert.doesNotMatch(gantt, /Sem janela planejada/);
  assert.match(gantt, /Não planejadas · \$\{naoPlanejadas\.length\}/);
  assert.match(gantt, /Planejamento incompleto · \$\{incompletas\.length\}/);
  assert.match(gantt, /· \{grupo\.itens\.length\} \{grupo\.itens\.length === 1 \? "etapa" : "etapas"\}/);
  const secao = gantt.slice(gantt.indexOf("function SubtituloSecao"), gantt.indexOf("function LinhaGantt"));
  assert.doesNotMatch(secao, /uppercase/);
});

test("Glass reaproveita os tokens existentes: sem blur por linha/botão, sem token paralelo, e os controles seguem acessíveis", () => {
  const gantt = semComentarios(ler("components/pauta/PautaGantt.tsx"));
  const toolbar = semComentarios(ler("components/pauta/PautaToolbar.tsx"));
  assert.doesNotMatch(gantt + toolbar, /backdrop-blur|backdrop-filter/);
  const css = ler("app/globals.css");
  assert.match(css, /\[data-visual-style="glass"\] \[data-pauta="alternador"\] \[aria-pressed="true"\] \{\s*background: var\(--glass-selected\);/);
  assert.equal((css.match(/--glass-pauta/g) ?? []).length, 0);
  assert.match(toolbar, /aria-label="Período anterior"/);
  assert.match(toolbar, /aria-label="Próximo período"/);
  assert.match(toolbar, /aria-pressed=\{ativo\}/);
  assert.match(toolbar, /<span className="sr-only">Busca<\/span>/);
});
