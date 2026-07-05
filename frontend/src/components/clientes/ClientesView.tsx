"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  EMPRESA_PADRAO_ID,
  equipesDisponiveis,
  responsaveisDisponiveis,
} from "@/lib/cliente-mock";
import type { ClienteDraft } from "@/types/cliente";
import { NovoClienteButton } from "./NovoClienteButton";

function resolveEquipeNome(equipeId?: string): string {
  if (!equipeId) return "-";

  return (
    equipesDisponiveis.find((equipe) => equipe.id === equipeId)?.nome ??
    equipeId
  );
}

function resolveResponsavelNome(responsavelId?: string): string {
  if (!responsavelId) return "-";

  return (
    responsaveisDisponiveis.find((usuario) => usuario.id === responsavelId)
      ?.nome ?? responsavelId
  );
}

const initialClientes: ClienteDraft[] = [
  {
    clienteId: "cliente-1",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#1001",
    tipoDocumento: "cnpj",
    documento: "12.345.678/0001-90",
    nomeRazaoSocial: "Cliente Exemplo Ltda",
    nomeFantasia: "Cliente Exemplo",
    sigla: "CEX",
    email: "contato@clienteexemplo.com.br",
    telefone: "",
    celular: "",
    site: "",
    status: "Ativo",
    equipeResponsavelId: "equipe-1",
    responsavelComercialId: "user-4",
    responsavelAtendimentoId: "user-4",
    endereco: {
      cep: "",
      logradouro: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "",
      uf: "",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
  },
  {
    clienteId: "cliente-2",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#1002",
    tipoDocumento: "cnpj",
    documento: "98.765.432/0001-10",
    nomeRazaoSocial: "Clínica Clare Ltda",
    nomeFantasia: "Clínica Clare",
    sigla: "CLC",
    email: "contato@clinicaclare.com.br",
    telefone: "",
    celular: "",
    site: "",
    status: "Ativo",
    equipeResponsavelId: "equipe-2",
    responsavelComercialId: "user-5",
    responsavelAtendimentoId: "user-5",
    endereco: {
      cep: "",
      logradouro: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "",
      uf: "",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
  },
  {
    clienteId: "cliente-3",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#1003",
    tipoDocumento: "cnpj",
    documento: "11.222.333/0001-44",
    nomeRazaoSocial: "Loja Boxx Ltda",
    nomeFantasia: "Loja Boxx",
    sigla: "LBX",
    email: "contato@lojaboxx.com.br",
    telefone: "",
    celular: "",
    site: "",
    status: "Ativo",
    equipeResponsavelId: "equipe-4",
    responsavelComercialId: "user-2",
    responsavelAtendimentoId: "user-2",
    endereco: {
      cep: "",
      logradouro: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "",
      uf: "",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
  },
  {
    clienteId: "cliente-4",
    empresaId: EMPRESA_PADRAO_ID,
    codigoInterno: "#1004",
    tipoDocumento: "cnpj",
    documento: "55.666.777/0001-88",
    nomeRazaoSocial: "Cliente Inativo Ltda",
    nomeFantasia: "Cliente Inativo",
    sigla: "CIN",
    email: "",
    telefone: "",
    celular: "",
    site: "",
    status: "Inativo",
    endereco: {
      cep: "",
      logradouro: "",
      numero: "",
      complemento: "",
      bairro: "",
      cidade: "",
      uf: "",
      pais: "Brasil",
      tipo: "Comercial",
    },
    contatos: [],
    historico: [],
  },
];

export function ClientesView() {
  const [clientes, setClientes] = useState<ClienteDraft[]>(initialClientes);

  const clientesAtivos = clientes.filter(
    (cliente) => cliente.status === "Ativo"
  ).length;

  const totalContatos = clientes.reduce(
    (total, cliente) => total + cliente.contatos.length,
    0
  );

  function handleCreate(draft: ClienteDraft) {
    setClientes((current) => [draft, ...current]);
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Clientes"
          description="Cadastro e gestão de clientes."
        />

        <NovoClienteButton onCreate={handleCreate} />
      </div>

      <div className="grid gap-5 md:grid-cols-3">
        <Card>
          <p className="text-sm text-zinc-500">Total Clientes</p>
          <p className="mt-3 text-3xl font-bold">{clientes.length}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Ativos</p>
          <p className="mt-3 text-3xl font-bold">{clientesAtivos}</p>
        </Card>

        <Card>
          <p className="text-sm text-zinc-500">Total de Contatos</p>
          <p className="mt-3 text-3xl font-bold">{totalContatos}</p>
        </Card>
      </div>

      <div className="mt-8 overflow-hidden rounded-3xl bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Cliente</th>
              <th className="px-6 py-4 font-medium">Documento</th>
              <th className="px-6 py-4 font-medium">Equipe Responsável</th>
              <th className="px-6 py-4 font-medium">Responsável Comercial</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>

          <tbody>
            {clientes.map((cliente) => (
              <tr
                key={cliente.clienteId}
                className="border-b border-zinc-100 last:border-0"
              >
                <td className="px-6 py-4 font-medium text-zinc-900">
                  {cliente.nomeFantasia || cliente.nomeRazaoSocial}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {cliente.documento}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {resolveEquipeNome(cliente.equipeResponsavelId)}
                </td>

                <td className="px-6 py-4 text-zinc-500">
                  {resolveResponsavelNome(cliente.responsavelComercialId)}
                </td>

                <td className="px-6 py-4">
                  <Badge>{cliente.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
