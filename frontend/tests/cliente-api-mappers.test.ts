import assert from "node:assert/strict";
import test from "node:test";
import type { ClienteApiResponse } from "../src/types/cliente-api";
import type {
  ClientePayloadDraft,
} from "../src/lib/cliente-api-mappers";
import type * as MapperModule from "../src/lib/cliente-api-mappers";

const mapperUrl = new URL("../src/lib/cliente-api-mappers.ts", import.meta.url).href;
const {
  mapClienteApiResponseToDomain,
  mapClienteDraftToCreatePayload,
  mapClienteDraftToUpdatePayload,
  mapClienteStatusLabel,
  normalizeClienteDocumento,
} = (await import(mapperUrl)) as typeof MapperModule;

type DraftFixture = ClientePayloadDraft & {
  clienteId: string;
  status: "Ativo" | "Suspenso" | "Inativo";
  equipeResponsavelId: string;
  responsavelComercialId: string;
  responsavelAtendimentoId: string;
  endereco: { cep: string };
  contatos: { id: string }[];
  administrativo: { feeMensal: { valor: number } };
  historico: { id: string }[];
};

function makeDraft(overrides: Partial<DraftFixture> = {}): DraftFixture {
  return {
    clienteId: "cliente-local",
    empresaId: "11111111-1111-1111-1111-111111111111",
    agenciaId: "22222222-2222-2222-2222-222222222222",
    codigoInterno: " CLI-001 ",
    tipoDocumento: "cnpj",
    documento: "12.345.678/0001-90",
    nomeRazaoSocial: " Cliente Modelo Ltda ",
    nomeFantasia: " Cliente Modelo ",
    sigla: " CM ",
    email: " contato@cliente.com ",
    telefone: " (11) 3333-4444 ",
    celular: " (11) 99999-8888 ",
    site: " https://cliente.com ",
    codigoExterno: " EXT-10 ",
    observacoes: " Cliente prioritario ",
    status: "Suspenso",
    equipeResponsavelId: "equipe-1",
    responsavelComercialId: "usuario-1",
    responsavelAtendimentoId: "usuario-2",
    endereco: { cep: "01001-000" },
    contatos: [{ id: "contato-1" }],
    administrativo: { feeMensal: { valor: 3500 } },
    historico: [{ id: "evento-1" }],
    ...overrides,
  };
}

function makeApiResponse(
  overrides: Partial<ClienteApiResponse> = {}
): ClienteApiResponse {
  return {
    id: "33333333-3333-3333-3333-333333333333",
    empresaId: "11111111-1111-1111-1111-111111111111",
    agenciaId: "22222222-2222-2222-2222-222222222222",
    codigoInterno: "CLI-001",
    tipoPessoa: "juridica",
    documento: "12345678000190",
    razaoSocial: "Cliente Modelo Ltda",
    nomeFantasia: "Cliente Modelo",
    nome: null,
    sigla: "CM",
    email: "contato@cliente.com",
    telefone: "1133334444",
    celular: "11999998888",
    site: "https://cliente.com",
    codigoExterno: "EXT-10",
    observacoes: "Cliente prioritario",
    status: "ativo",
    statusAlteradoAt: null,
    statusAlteradoPorUsuarioId: null,
    motivoStatus: null,
    createdAt: "2026-07-17T10:00:00Z",
    updatedAt: "2026-07-17T10:00:00Z",
    ...overrides,
  };
}

test("mapeia response PJ para o modelo de dominio sem perder opcionais", () => {
  const cliente = mapClienteApiResponseToDomain(makeApiResponse());

  assert.equal(cliente.id, "33333333-3333-3333-3333-333333333333");
  assert.equal(cliente.tipoPessoa, "juridica");
  assert.equal(cliente.tipoDocumento, "cnpj");
  assert.equal(cliente.nomePrincipal, "Cliente Modelo");
  assert.equal(cliente.statusLabel, "Ativo");
  assert.equal(cliente.agenciaId, "22222222-2222-2222-2222-222222222222");
  assert.equal(cliente.codigoExterno, "EXT-10");
  assert.equal(cliente.observacoes, "Cliente prioritario");
});

test("mapeia aliases e nome de PF para o modelo de dominio", () => {
  const cliente = mapClienteApiResponseToDomain(
    makeApiResponse({
      tipoPessoa: "fisica",
      documento: "12345678901",
      razaoSocial: null,
      nomeFantasia: null,
      nome: "Maria Cliente",
    })
  );

  assert.equal(cliente.tipoDocumento, "cpf");
  assert.equal(cliente.nomePrincipal, "Maria Cliente");
  assert.equal(cliente.nome, "Maria Cliente");
});

test("normaliza CPF e CNPJ formatados para somente digitos", () => {
  assert.equal(normalizeClienteDocumento("123.456.789-01"), "12345678901");
  assert.equal(normalizeClienteDocumento("12.345.678/0001-90"), "12345678000190");
  assert.equal(normalizeClienteDocumento(""), null);
});

test("cria payload PJ sem ID e sem campos nao suportados", () => {
  const payload = mapClienteDraftToCreatePayload(makeDraft());

  assert.equal(payload.tipoPessoa, "juridica");
  assert.equal(payload.documento, "12345678000190");
  assert.equal(payload.razaoSocial, "Cliente Modelo Ltda");
  assert.equal(payload.nome, null);
  assert.equal(payload.status, "ativo");
  assert.equal(payload.email, "contato@cliente.com");
  assert.equal(Object.hasOwn(payload, "id"), false);
  assert.equal(Object.hasOwn(payload, "clienteId"), false);
  assert.equal(Object.hasOwn(payload, "equipeResponsavelId"), false);
  assert.equal(Object.hasOwn(payload, "endereco"), false);
  assert.equal(Object.hasOwn(payload, "contatos"), false);
  assert.equal(Object.hasOwn(payload, "administrativo"), false);
  assert.equal(Object.hasOwn(payload, "historico"), false);
});

test("cria payload PF usando nome e documento normalizado", () => {
  const payload = mapClienteDraftToCreatePayload(
    makeDraft({
      tipoDocumento: "cpf",
      documento: "123.456.789-01",
      nomeRazaoSocial: "Maria Cliente",
      nomeFantasia: "",
    })
  );

  assert.equal(payload.tipoPessoa, "fisica");
  assert.equal(payload.documento, "12345678901");
  assert.equal(payload.nome, "Maria Cliente");
  assert.equal(payload.razaoSocial, null);
  assert.equal(payload.nomeFantasia, null);
});

test("PATCH preserva opcionais validos e nunca envia status ou empresa", () => {
  const payload = mapClienteDraftToUpdatePayload(makeDraft());

  assert.equal(payload.agenciaId, "22222222-2222-2222-2222-222222222222");
  assert.equal(payload.codigoExterno, "EXT-10");
  assert.equal(payload.observacoes, "Cliente prioritario");
  assert.equal(payload.telefone, "(11) 3333-4444");
  assert.equal(payload.celular, "(11) 99999-8888");
  assert.equal(payload.site, "https://cliente.com");
  assert.equal(Object.hasOwn(payload, "status"), false);
  assert.equal(Object.hasOwn(payload, "empresaId"), false);
  assert.equal(Object.hasOwn(payload, "clienteId"), false);
});

test("converte todos os status da API para rotulos visuais", () => {
  assert.equal(mapClienteStatusLabel("ativo"), "Ativo");
  assert.equal(mapClienteStatusLabel("suspenso"), "Suspenso");
  assert.equal(mapClienteStatusLabel("inativo"), "Inativo");
});
