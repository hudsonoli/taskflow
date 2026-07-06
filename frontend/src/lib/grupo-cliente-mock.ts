import {
  EMPRESA_PADRAO_ID,
  generateCodigoInterno,
  generateId,
} from "@/lib/cliente-mock";
import type { ClienteDraft } from "@/types/cliente";
import type { GrupoClienteDraft } from "@/types/grupo-cliente";

export { EMPRESA_PADRAO_ID, generateCodigoInterno, generateId };

export type ClienteGrupoItem = Pick<
  ClienteDraft,
  | "clienteId"
  | "codigoInterno"
  | "nomeFantasia"
  | "nomeRazaoSocial"
  | "sigla"
  | "status"
>;

export const clientesGrupoDisponiveis: ClienteGrupoItem[] = [
  {
    clienteId: "cliente-1",
    codigoInterno: "#1001",
    nomeFantasia: "Cliente Exemplo",
    nomeRazaoSocial: "Cliente Exemplo Ltda",
    sigla: "CEX",
    status: "Ativo",
  },
  {
    clienteId: "cliente-2",
    codigoInterno: "#1002",
    nomeFantasia: "Clínica Clare",
    nomeRazaoSocial: "Clínica Clare Ltda",
    sigla: "CLC",
    status: "Ativo",
  },
  {
    clienteId: "cliente-3",
    codigoInterno: "#1003",
    nomeFantasia: "Loja Boxx",
    nomeRazaoSocial: "Loja Boxx Ltda",
    sigla: "LBX",
    status: "Ativo",
  },
  {
    clienteId: "cliente-4",
    codigoInterno: "#1004",
    nomeFantasia: "Cliente Inativo",
    nomeRazaoSocial: "Cliente Inativo Ltda",
    sigla: "CIN",
    status: "Inativo",
  },
];

const now = new Date().toISOString();

export const initialGruposClientes: GrupoClienteDraft[] = [
  {
    grupoClienteId: "grupo-cliente-1",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#GC-1001",
    nome: "Grupo Comercial Norte",
    sigla: "GCN",
    clientesIds: ["cliente-1", "cliente-2"],
    status: "Ativo",
    historico: [],
    createdAt: now,
    updatedAt: now,
  },
  {
    grupoClienteId: "grupo-cliente-2",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#GC-1002",
    nome: "Grupo Boxx Premium",
    sigla: "GBP",
    clientesIds: ["cliente-3"],
    status: "Ativo",
    historico: [],
    createdAt: now,
    updatedAt: now,
  },
];

export function createEmptyGrupoClienteDraft(): GrupoClienteDraft {
  const createdAt = new Date().toISOString();

  return {
    grupoClienteId: generateId("grupo-cliente"),
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: generateCodigoInterno(),
    nome: "",
    sigla: "",
    clientesIds: [],
    status: "Ativo",
    historico: [],
    createdAt,
    updatedAt: createdAt,
  };
}

export function cloneGrupoCliente(
  grupoCliente: GrupoClienteDraft
): GrupoClienteDraft {
  return {
    ...grupoCliente,
    clientesIds: [...grupoCliente.clientesIds],
    historico: grupoCliente.historico.map((evento) => ({ ...evento })),
  };
}
