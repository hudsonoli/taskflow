// Fase 6 — filtros avançados de ARQUIVOS: tradução para os parâmetros do servidor e ligação com a tela. `npm run test:filtros-arquivos`.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { CAMPO_ARQUIVOS, filtrosArquivosParaApi } from "./filtros-arquivos.ts";
import type { FiltroAtivo } from "../types/filtros.ts";

const ler = (caminho: string) => readFileSync(new URL(`../${caminho}`, import.meta.url), "utf8").replace(/\r\n/g, "\n");
const A = "0b8f7e0e-4c2d-4f0a-9d37-1f2e3a4b5c6d";
const B = "7a1c2d3e-4f50-4617-8899-aabbccddeeff";
const AGORA = new Date(2026, 9, 8, 15, 30);

test("um filtro: 'é' vai em clienteId; 'não é' vai em clienteIdExcluir", () => {
  assert.deepEqual(filtrosArquivosParaApi([{ campo: CAMPO_ARQUIVOS.cliente, operador: "is", valores: [A] }]), { clienteId: A });
  assert.deepEqual(filtrosArquivosParaApi([{ campo: CAMPO_ARQUIVOS.cliente, operador: "is_not", valores: [A] }]), { clienteIdExcluir: A });
});

test("'é um de' / 'não é um de' viram CSV (OR no servidor)", () => {
  assert.deepEqual(filtrosArquivosParaApi([{ campo: "projeto", operador: "in", valores: [A, B] }]), { projetoId: `${A},${B}` });
  assert.deepEqual(filtrosArquivosParaApi([{ campo: "tipo", operador: "not_in", valores: ["link", "anexo"] }]), { tipoExcluir: "link,anexo" });
});

test("vários filtros combinados: cada campo em seu parâmetro (AND no servidor), incluindo remetente e status", () => {
  const filtros: FiltroAtivo[] = [
    { campo: "cliente", operador: "is", valores: [A] },
    { campo: "demanda", operador: "in", valores: [A, B] },
    { campo: "tipo", operador: "is", valores: ["layout"] },
    { campo: "status", operador: "in", valores: ["aprovado", "reprovado"] },
    { campo: "enviadoPor", operador: "is_not", valores: [B] },
  ];
  assert.deepEqual(filtrosArquivosParaApi(filtros), {
    clienteId: A,
    demandaId: `${A},${B}`,
    tipo: "layout",
    status: "aprovado,reprovado",
    usuarioIdExcluir: B,
  });
});

test("data de envio: 'é' = dia inteiro; 'antes de'/'depois de' = uma ponta aberta; atalhos viram intervalo", () => {
  const dia = filtrosArquivosParaApi([{ campo: "dataEnvio", operador: "is", valores: ["2026-10-15"] }], AGORA);
  assert.equal(new Date(dia.dataInicio!).getTime(), new Date(2026, 9, 15, 0, 0, 0, 0).getTime());
  assert.equal(new Date(dia.dataFim!).getTime(), new Date(2026, 9, 15, 23, 59, 59, 999).getTime());
  const antes = filtrosArquivosParaApi([{ campo: "dataEnvio", operador: "before", valores: ["2026-10-15"] }], AGORA);
  assert.equal(antes.dataInicio, undefined);
  assert.equal(new Date(antes.dataFim!).getTime(), new Date(2026, 9, 15).getTime() - 1);
  const depois = filtrosArquivosParaApi([{ campo: "dataEnvio", operador: "after", valores: ["2026-10-15"] }], AGORA);
  assert.equal(depois.dataFim, undefined);
  assert.equal(new Date(depois.dataInicio!).getTime(), new Date(2026, 9, 16).getTime());
  const hoje = filtrosArquivosParaApi([{ campo: "dataEnvio", operador: "is", valores: ["hoje"] }], AGORA);
  assert.equal(new Date(hoje.dataInicio!).getDate(), 8);
  assert.match(hoje.dataInicio!, /Z$/); // a API exige timezone
});

test("filtro sem valores, campo desconhecido ou data inválida não geram parâmetro; sem filtros = nada", () => {
  assert.deepEqual(filtrosArquivosParaApi([]), {});
  assert.deepEqual(filtrosArquivosParaApi([{ campo: "cliente", operador: "is", valores: [] }]), {});
  assert.deepEqual(filtrosArquivosParaApi([{ campo: "inventado", operador: "is", valores: [A] }]), {});
  assert.deepEqual(filtrosArquivosParaApi([{ campo: "dataEnvio", operador: "is", valores: ["2026-99-99"] }], AGORA), {});
});

test("limpar volta à visão original: lista vazia → nenhum parâmetro de filtro", () => {
  const com = filtrosArquivosParaApi([{ campo: "tipo", operador: "is", valores: ["link"] }]);
  assert.ok(Object.keys(com).length > 0);
  assert.deepEqual(filtrosArquivosParaApi([]), {});
});

test("tela de Arquivos: busca separada dos filtros, recorte fixo prevalece, filtros no servidor antes da paginação", () => {
  const view = ler("components/arquivos/ArquivosContextView.tsx");
  assert.match(view, /search: busca \|\| undefined/); // busca textual SEPARADA dos filtros estruturados
  assert.match(view, /clienteId: clienteId \?\? parametrosAvancados\.clienteId/);
  assert.match(view, /projetoId: projetoId \?\? parametrosAvancados\.projetoId/);
  assert.match(view, /listArquivosCentral\(\{ \.\.\.filtrosAtualRef\.current, limit: TAMANHO_PAGINA, offset: 0 \}\)/);
  assert.match(view, /offset: itens\.length/); // "carregar mais" mantém os mesmos filtros
  assert.doesNotMatch(view, /itens\.filter\(/); // nunca filtra só a página carregada
  assert.match(view, /useFiltrosNaUrl\(definicoes, persistirNaUrl\)/);
  // URL só no Gerenciador central; as abas de Cliente/Projeto não mexem na URL
  assert.match(ler("components/arquivos/ArquivosView.tsx"), /<ArquivosContextView persistirNaUrl \/>/);
  assert.doesNotMatch(ler("components/clientes/ClienteFormModal.tsx"), /persistirNaUrl/);
  assert.doesNotMatch(ler("components/projetos/ProjetoDetailsDrawer.tsx"), /persistirNaUrl/);
});

test("campos oferecidos só existem no domínio; cliente/projeto somem quando o recorte já é fixo", () => {
  const defs = ler("components/arquivos/useDefinicoesFiltrosArquivos.ts");
  for (const campo of ["cliente", "projeto", "demanda", "tipo", "status", "enviadoPor", "dataEnvio"]) assert.ok(defs.includes(`CAMPO_ARQUIVOS.${campo}`), campo);
  assert.match(defs, /if \(!ocultarCliente\)/);
  assert.match(defs, /if \(!ocultarProjeto\)/);
  assert.match(defs, /STATUS_LAYOUT_OPTIONS/); // status REAIS do produto, não os da referência
  assert.match(defs, /buscarOpcoes: async/); // usuários: busca no servidor (sem pré-carregar todos)
});

test("API: o cliente HTTP envia as exclusões; o backend recebe os mesmos nomes", () => {
  const api = ler("lib/api-backend.ts");
  for (const nome of ["clienteIdExcluir", "projetoIdExcluir", "demandaIdExcluir", "tipoExcluir", "statusExcluir", "usuarioIdExcluir"]) {
    assert.ok(api.includes(`search.set("${nome}"`), nome);
  }
});
