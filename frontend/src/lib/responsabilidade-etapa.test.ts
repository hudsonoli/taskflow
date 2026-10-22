// Responsáveis por etapa do workflow: exibição da origem (etapa / herdado da tarefa / sem responsável), edição e ajustes na criação. `npm run test:etapa-responsaveis` (node --test).
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import {
  aplicarAjusteDaEtapa,
  podeEditarResponsaveisDaEtapa,
  previsaoNaCriacao,
  removerAjusteDaEtapa,
  responsabilidadeDaEtapa,
  ROTULO_ORIGEM,
} from "./responsabilidade-etapa.ts";

const SRC = new URL("../", import.meta.url);
const ler = (caminho: string) => readFileSync(new URL(caminho, SRC), "utf8").replace(/\r\n/g, "\n");
const semComentarios = (texto: string) => texto.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

test("tarefa existente: a UI exibe a resolução do SERVIDOR (explícita, herdada, nenhuma) — sem comparar listas", () => {
  const explicita = { usuarioResponsavelIds: ["raquel"], departamentoResponsavelIds: [], responsabilidadeEfetiva: { origem: "etapa" as const, usuarioIds: ["raquel"], departamentoIds: [] } };
  const herdada = { usuarioResponsavelIds: [], departamentoResponsavelIds: [], responsabilidadeEfetiva: { origem: "tarefa" as const, usuarioIds: ["milenna"], departamentoIds: [] } };
  const nenhuma = { usuarioResponsavelIds: [], departamentoResponsavelIds: [], responsabilidadeEfetiva: { origem: "nenhuma" as const, usuarioIds: [], departamentoIds: [] } };
  assert.equal(responsabilidadeDaEtapa(explicita).origem, "etapa");
  assert.deepEqual(responsabilidadeDaEtapa(herdada), { origem: "tarefa", usuarioIds: ["milenna"], departamentoIds: [] }); // herdado NÃO vira vínculo da etapa
  assert.equal(responsabilidadeDaEtapa(nenhuma).origem, "nenhuma");
  assert.equal(ROTULO_ORIGEM.tarefa, "Herdado da tarefa");
  assert.equal(ROTULO_ORIGEM.nenhuma, "Sem responsável");
  // resposta antiga sem o campo: cai nos vínculos explícitos da própria etapa
  assert.equal(responsabilidadeDaEtapa({ usuarioResponsavelIds: ["a"], departamentoResponsavelIds: [] }).origem, "etapa");
  assert.equal(responsabilidadeDaEtapa({ usuarioResponsavelIds: [], departamentoResponsavelIds: [] }).origem, "nenhuma");
});

test("criação: pré-visualização com a regra de 3 degraus; só departamento já é responsabilidade explícita; múltiplos responsáveis", () => {
  const gerais = { usuarioIds: ["milenna"], departamentoIds: [] };
  assert.deepEqual(previsaoNaCriacao({ usuarioIds: ["raquel", "joao"], departamentoIds: [] }, gerais), { origem: "etapa", usuarioIds: ["raquel", "joao"], departamentoIds: [] });
  assert.deepEqual(previsaoNaCriacao({ usuarioIds: [], departamentoIds: ["criacao"] }, gerais), { origem: "etapa", usuarioIds: [], departamentoIds: ["criacao"] }); // sem fallback para Milenna
  assert.deepEqual(previsaoNaCriacao({ usuarioIds: [], departamentoIds: [] }, gerais), { origem: "tarefa", usuarioIds: ["milenna"], departamentoIds: [] });
  assert.deepEqual(previsaoNaCriacao({ usuarioIds: [], departamentoIds: [] }, { usuarioIds: [], departamentoIds: [] }), { origem: "nenhuma", usuarioIds: [], departamentoIds: [] });
});

test("ajustes da criação: trocar, restaurar o padrão do modelo e nunca mutar a lista anterior", () => {
  const base = [{ modeloEtapaId: "e1", usuarioResponsavelIds: ["a"], departamentoResponsavelIds: [] }];
  const trocada = aplicarAjusteDaEtapa(base, { modeloEtapaId: "e1", usuarioResponsavelIds: ["b"], departamentoResponsavelIds: [] });
  const somada = aplicarAjusteDaEtapa(trocada, { modeloEtapaId: "e2", usuarioResponsavelIds: [], departamentoResponsavelIds: [] }); // [] explícito (herdar) é um ajuste válido
  assert.deepEqual(base[0].usuarioResponsavelIds, ["a"]);
  assert.deepEqual(trocada.map((x) => x.usuarioResponsavelIds), [["b"]]);
  assert.deepEqual(somada.map((x) => x.modeloEtapaId).sort(), ["e1", "e2"]);
  assert.deepEqual(removerAjusteDaEtapa(somada, "e1").map((x) => x.modeloEtapaId), ["e2"]);
});

test("quem pode abrir o editor: etapa não concluída, sem leitura/acompanhamento/acesso só-workflow e tarefa não arquivada", () => {
  const ativa = { status: "ativa", acessoApenasWorkflow: false, acessoSomenteAcompanhamento: false };
  assert.equal(podeEditarResponsaveisDaEtapa(ativa, { status: "pendente" }, false), true);
  assert.equal(podeEditarResponsaveisDaEtapa(ativa, { status: "em_execucao" }, false), true);
  assert.equal(podeEditarResponsaveisDaEtapa(ativa, { status: "concluida" }, false), false); // concluída: somente leitura
  assert.equal(podeEditarResponsaveisDaEtapa(ativa, { status: "pendente" }, true), false); // Pauta/leitura
  assert.equal(podeEditarResponsaveisDaEtapa({ ...ativa, acessoApenasWorkflow: true }, { status: "pendente" }, false), false);
  assert.equal(podeEditarResponsaveisDaEtapa({ ...ativa, acessoSomenteAcompanhamento: true }, { status: "pendente" }, false), false);
  assert.equal(podeEditarResponsaveisDaEtapa({ ...ativa, status: "arquivada" }, { status: "pendente" }, false), false);
});

test("aba Workflow: mostra departamento/responsáveis/origem de CADA etapa e edita uma etapa por vez (sem requisição por etapa na leitura)", () => {
  const secao = semComentarios(ler("components/demandas/DemandaFormSections.tsx"));
  assert.match(secao, /<ResponsabilidadeEtapa\s+responsabilidade=\{responsabilidadeDaEtapa\(etapa\)\}/);
  assert.match(secao, /podeEditarResponsaveisDaEtapa\(demanda, etapa, somenteLeitura\)/);
  assert.match(secao, /Editar responsáveis/);
  assert.match(secao, /alterarResponsaveisEtapaReal\(demanda\.id, editandoResponsaveis\.id,/);
  assert.doesNotMatch(secao, /Sem responsável definido/); // o texto antigo (ambíguo) saiu: agora há 3 estados explícitos
  // a leitura vem da própria tarefa (já agregada): nenhuma chamada de API por etapa para descobrir responsáveis
  const exibicao = semComentarios(ler("components/demandas/ResponsabilidadeEtapa.tsx"));
  assert.doesNotMatch(exibicao, /fetch|request\(|api-backend/);
  assert.match(exibicao, /Responsável ainda não definido/);
  assert.match(exibicao, /ROTULO_ORIGEM\[origem\]/);
});

test("editor: pessoas e departamentos (vários), ajuda de herança e 'Usar responsáveis da tarefa' = duas listas vazias (nada é copiado)", () => {
  const modal = semComentarios(ler("components/demandas/EditarResponsaveisEtapaModal.tsx"));
  assert.match(modal, /<MemberSelector/);
  assert.match(modal, /<MultiSelect/);
  assert.match(modal, /AJUDA_HERANCA/);
  assert.match(modal, /onClick=\{\(\) => void enviar\(\[\], \[\]\)\}/);
  assert.match(modal, /rotuloLimpar = "Usar responsáveis da tarefa"/);
  assert.match(ler("lib/responsabilidade-etapa.ts"), /Se nenhum responsável específico for definido, esta etapa usa os responsáveis gerais da tarefa\./);
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /export async function alterarResponsaveisEtapaReal\(/);
  assert.match(api, /\/workflow\/etapas\/\$\{etapaId\}\/responsaveis`, \{\s*method: "PUT"/);
});

test("criação: etapas do modelo com departamento/responsáveis, ajuste por etapa, envio opcional por id da etapa do MODELO e reset ao trocar de modelo", () => {
  const criacao = semComentarios(ler("components/demandas/EtapasDoWorkflowNaCriacao.tsx"));
  assert.match(criacao, /Definir responsáveis/);
  assert.match(criacao, /Restaurar padrão do modelo/);
  assert.match(criacao, /modeloEtapaId: editando\.id/);
  const modal = semComentarios(ler("components/demandas/NovaDemandaModal.tsx"));
  assert.match(modal, /<EtapasDoWorkflowNaCriacao/);
  assert.match(modal, /workflowModeloId: workflowModeloId \|\| null, workflowEtapasResponsaveis: \[\]/);
  const api = semComentarios(ler("lib/api-backend.ts"));
  assert.match(api, /draft\.workflowModeloId && draft\.workflowEtapasResponsaveis && draft\.workflowEtapasResponsaveis\.length > 0/);
  const tipos = semComentarios(ler("types/demanda.ts"));
  assert.match(tipos, /workflowEtapasResponsaveis\?: \{ modeloEtapaId: string; usuarioResponsavelIds: string\[\]; departamentoResponsavelIds: string\[\] \}\[\]/);
});

test("o modelo de workflow nunca é alterado por estas telas", () => {
  for (const arquivo of ["components/demandas/EtapasDoWorkflowNaCriacao.tsx", "components/demandas/EditarResponsaveisEtapaModal.tsx"]) {
    assert.doesNotMatch(semComentarios(ler(arquivo)), /atualizarWorkflowModelo|criarWorkflowModelo|workflow-modelos/, arquivo);
  }
});
