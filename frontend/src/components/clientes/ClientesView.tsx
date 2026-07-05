"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  EMPRESA_PADRAO_ID,
  equipesDisponiveis,
  responsaveisDisponiveis,
} from "@/lib/cliente-mock";
import type { ClienteDraft } from "@/types/cliente";
import { NovoClienteButton } from "./NovoClienteButton";
import { NovoClienteModal } from "./NovoClienteModal";

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
  const [selectedClienteId, setSelectedClienteId] = useState<string | null>(
    null
  );
  const [editingClienteId, setEditingClienteId] = useState<string | null>(null);

  const selectedCliente = clientes.find(
    (cliente) => cliente.clienteId === selectedClienteId
  );
  const editingCliente = clientes.find(
    (cliente) => cliente.clienteId === editingClienteId
  );

  const clientesAtivos = clientes.filter(
    (cliente) => cliente.status === "Ativo"
  ).length;

  const totalContatos = clientes.reduce(
    (total, cliente) => total + cliente.contatos.length,
    0
  );

  function handleUpsert(draft: ClienteDraft) {
    setClientes((current) => {
      const exists = current.some(
        (cliente) => cliente.clienteId === draft.clienteId
      );

      if (!exists) return [draft, ...current];

      return current.map((cliente) =>
        cliente.clienteId === draft.clienteId ? draft : cliente
      );
    });
  }

  function openEdit(clienteId: string) {
    setSelectedClienteId(null);
    setEditingClienteId(clienteId);
  }

  function closeEdit() {
    setEditingClienteId(null);
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Clientes"
          description="Cadastro e gestão de clientes."
        />

        <NovoClienteButton onCreate={handleUpsert} />
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
                tabIndex={0}
                onClick={() => setSelectedClienteId(cliente.clienteId)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    setSelectedClienteId(cliente.clienteId);
                  }
                }}
                aria-label={`Ver cliente ${
                  cliente.nomeFantasia || cliente.nomeRazaoSocial
                }`}
                className="cursor-pointer border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50 focus:bg-zinc-50 focus:outline-none"
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

      <EntitySidePanel
        open={selectedCliente !== undefined}
        onClose={() => setSelectedClienteId(null)}
        onEdit={
          selectedCliente
            ? () => openEdit(selectedCliente.clienteId)
            : undefined
        }
        editLabel="Editar cliente"
        title={
          selectedCliente
            ? selectedCliente.nomeFantasia || selectedCliente.nomeRazaoSocial
            : "Cliente"
        }
        description={selectedCliente?.codigoInterno}
        footer={
          <div className="flex justify-end">
            <Button
              variant="secondary"
              onClick={() => setSelectedClienteId(null)}
            >
              Fechar
            </Button>
          </div>
        }
      >
        {selectedCliente && (
          <div className="space-y-8">
            <section>
              <h3 className="text-sm font-semibold text-zinc-900">
                Informações
              </h3>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-zinc-400">Nome</dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {selectedCliente.nomeFantasia ||
                      selectedCliente.nomeRazaoSocial}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">Código interno</dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {selectedCliente.codigoInterno}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">Documento</dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {selectedCliente.documento}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">Contato</dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {selectedCliente.email ||
                      selectedCliente.telefone ||
                      selectedCliente.celular ||
                      "-"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">
                    Equipe responsável
                  </dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {resolveEquipeNome(selectedCliente.equipeResponsavelId)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">
                    Responsável comercial
                  </dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {resolveResponsavelNome(
                      selectedCliente.responsavelComercialId
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">Status</dt>
                  <dd className="mt-1">
                    <Badge>{selectedCliente.status}</Badge>
                  </dd>
                </div>
              </dl>
            </section>

            <section>
              <h3 className="text-sm font-semibold text-zinc-900">
                Último histórico
              </h3>
              {selectedCliente.historico.length > 0 ? (
                <div className="mt-4 rounded-2xl bg-[#faf8f4] p-4">
                  <p className="text-sm text-zinc-700">
                    {
                      selectedCliente.historico[
                        selectedCliente.historico.length - 1
                      ].acao
                    }
                  </p>
                  <p className="mt-1 text-xs text-zinc-400">
                    {
                      selectedCliente.historico[
                        selectedCliente.historico.length - 1
                      ].usuario
                    }{" "}
                    ·{" "}
                    {
                      selectedCliente.historico[
                        selectedCliente.historico.length - 1
                      ].dataHora
                    }
                  </p>
                </div>
              ) : (
                <p className="mt-3 text-sm text-zinc-500">
                  Nenhum histórico registrado.
                </p>
              )}
            </section>
          </div>
        )}
      </EntitySidePanel>

      {editingCliente && (
        <NovoClienteModal
          key={editingCliente.clienteId}
          open
          cliente={editingCliente}
          onClose={closeEdit}
          onCreate={handleUpsert}
        />
      )}
    </div>
  );
}
