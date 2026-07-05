"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { initialFornecedores } from "@/lib/fornecedor-mock";
import type { FornecedorDraft } from "@/types/fornecedor";
import { NovoFornecedorButton } from "./NovoFornecedorButton";
import { NovoFornecedorModal } from "./NovoFornecedorModal";

type FornecedoresViewProps = {
  canCreate?: boolean;
  canEdit?: boolean;
};

function displayName(fornecedor: FornecedorDraft): string {
  return (
    fornecedor.nomeFantasia ||
    fornecedor.nomeRazaoSocial ||
    "Fornecedor sem nome"
  );
}

export function FornecedoresView({
  canCreate = true,
  canEdit = true,
}: FornecedoresViewProps = {}) {
  const [fornecedores, setFornecedores] =
    useState<FornecedorDraft[]>(initialFornecedores);
  const [selectedFornecedorId, setSelectedFornecedorId] =
    useState<string | null>(null);
  const [editingFornecedorId, setEditingFornecedorId] =
    useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const selectedFornecedor = fornecedores.find(
    (fornecedor) =>
      fornecedor.fornecedorId === selectedFornecedorId
  );
  const editingFornecedor = fornecedores.find(
    (fornecedor) =>
      fornecedor.fornecedorId === editingFornecedorId
  );

  const ativos = fornecedores.filter(
    (fornecedor) => fornecedor.status === "Ativo"
  ).length;
  const inativos = fornecedores.length - ativos;
  const categoriasCadastradas = new Set(
    fornecedores.map((fornecedor) => fornecedor.categoria)
  ).size;

  function openCreate() {
    setEditingFornecedorId(null);
    setModalOpen(true);
  }

  function openEdit(fornecedorId: string) {
    setSelectedFornecedorId(null);
    setEditingFornecedorId(fornecedorId);
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingFornecedorId(null);
  }

  function handleSave(draft: FornecedorDraft) {
    setFornecedores((current) => {
      const exists = current.some(
        (fornecedor) =>
          fornecedor.fornecedorId === draft.fornecedorId
      );

      if (!exists) return [draft, ...current];

      return current.map((fornecedor) =>
        fornecedor.fornecedorId === draft.fornecedorId
          ? draft
          : fornecedor
      );
    });
  }

  function openPanel(fornecedorId: string) {
    setSelectedFornecedorId(fornecedorId);
  }

  return (
    <div className="p-8">
      <div className="flex items-start justify-between gap-4">
        <PageHeader
          title="Fornecedores"
          description="Cadastro e gestão operacional de fornecedores."
        />
        <NovoFornecedorButton
          onClick={openCreate}
          disabled={!canCreate}
        />
      </div>

      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <p className="text-sm text-zinc-500">
            Total de Fornecedores
          </p>
          <p className="mt-3 text-3xl font-bold">
            {fornecedores.length}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-zinc-500">Ativos</p>
          <p className="mt-3 text-3xl font-bold">{ativos}</p>
        </Card>
        <Card>
          <p className="text-sm text-zinc-500">Inativos</p>
          <p className="mt-3 text-3xl font-bold">{inativos}</p>
        </Card>
        <Card>
          <p className="text-sm text-zinc-500">
            Categorias Cadastradas
          </p>
          <p className="mt-3 text-3xl font-bold">
            {categoriasCadastradas}
          </p>
        </Card>
      </div>

      <div className="mt-8 overflow-x-auto rounded-3xl bg-white shadow-sm">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-zinc-100 bg-[#faf8f4] text-zinc-500">
            <tr>
              <th className="px-6 py-4 font-medium">Fornecedor</th>
              <th className="px-6 py-4 font-medium">Documento</th>
              <th className="px-6 py-4 font-medium">Categoria</th>
              <th className="px-6 py-4 font-medium">Contato</th>
              <th className="px-6 py-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {fornecedores.map((fornecedor) => (
              <tr
                key={fornecedor.fornecedorId}
                tabIndex={0}
                onClick={() =>
                  openPanel(fornecedor.fornecedorId)
                }
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" ||
                    event.key === " "
                  ) {
                    event.preventDefault();
                    openPanel(fornecedor.fornecedorId);
                  }
                }}
                aria-label={`Ver fornecedor ${displayName(
                  fornecedor
                )}`}
                className="cursor-pointer border-b border-zinc-100 transition last:border-0 hover:bg-zinc-50 focus:bg-zinc-50 focus:outline-none"
              >
                <td className="px-6 py-4">
                  <p className="font-medium text-zinc-900">
                    {displayName(fornecedor)}
                  </p>
                  <p className="mt-1 text-xs text-zinc-400">
                    {fornecedor.codigoInterno}
                  </p>
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {fornecedor.documento}
                </td>
                <td className="px-6 py-4">
                  <Badge>{fornecedor.categoria}</Badge>
                </td>
                <td className="px-6 py-4 text-zinc-500">
                  {fornecedor.email ||
                    fornecedor.telefone ||
                    fornecedor.celular ||
                    "-"}
                </td>
                <td className="px-6 py-4">
                  <Badge>{fornecedor.status}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <EntitySidePanel
        open={selectedFornecedor !== undefined}
        onClose={() => setSelectedFornecedorId(null)}
        onEdit={
          canEdit && selectedFornecedor
            ? () =>
                openEdit(selectedFornecedor.fornecedorId)
            : undefined
        }
        editLabel="Editar fornecedor"
        title={
          selectedFornecedor
            ? displayName(selectedFornecedor)
            : "Fornecedor"
        }
        description={selectedFornecedor?.codigoInterno}
        footer={
          <div className="flex justify-end">
            <Button
              variant="secondary"
              onClick={() => setSelectedFornecedorId(null)}
            >
              Fechar
            </Button>
          </div>
        }
      >
        {selectedFornecedor && (
          <div className="space-y-8">
            <section>
              <h3 className="text-sm font-semibold text-zinc-900">
                Informações
              </h3>
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-zinc-400">
                    Código interno
                  </dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {selectedFornecedor.codigoInterno}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">Nome</dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {displayName(selectedFornecedor)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">
                    Documento
                  </dt>
                  <dd className="mt-1 text-sm font-medium text-zinc-800">
                    {selectedFornecedor.documento}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">
                    Categoria
                  </dt>
                  <dd className="mt-1">
                    <Badge>
                      {selectedFornecedor.categoria}
                    </Badge>
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-zinc-400">Status</dt>
                  <dd className="mt-1">
                    <Badge>{selectedFornecedor.status}</Badge>
                  </dd>
                </div>
              </dl>
            </section>

            <section>
              <h3 className="text-sm font-semibold text-zinc-900">
                Contatos
              </h3>
              {selectedFornecedor.contatos.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {selectedFornecedor.contatos.map((contato) => (
                    <div
                      key={contato.contatoId}
                      className="rounded-2xl border border-zinc-200 p-4"
                    >
                      <p className="font-medium text-zinc-900">
                        {contato.nome}
                      </p>
                      <p className="mt-1 text-xs text-zinc-400">
                        {contato.cargo || "Contato"}
                      </p>
                      <p className="mt-2 text-sm text-zinc-600">
                        {contato.email ||
                          contato.telefone ||
                          contato.celular ||
                          "-"}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-zinc-500">
                  Nenhum contato cadastrado.
                </p>
              )}
            </section>

            <section>
              <h3 className="text-sm font-semibold text-zinc-900">
                Histórico resumido
              </h3>
              {selectedFornecedor.historico.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {selectedFornecedor.historico
                    .slice(-3)
                    .reverse()
                    .map((evento) => (
                      <div
                        key={evento.id}
                        className="rounded-2xl bg-[#faf8f4] p-4"
                      >
                        <p className="text-sm text-zinc-700">
                          {evento.acao}
                        </p>
                        <p className="mt-1 text-xs text-zinc-400">
                          {evento.usuario} · {evento.dataHora}
                        </p>
                      </div>
                    ))}
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

      <NovoFornecedorModal
        open={modalOpen}
        onClose={closeModal}
        onSave={handleSave}
        fornecedor={editingFornecedor}
      />
    </div>
  );
}
