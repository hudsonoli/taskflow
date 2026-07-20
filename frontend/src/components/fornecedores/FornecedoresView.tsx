"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Truck } from "lucide-react";
import {
  CadastroAvatar,
  CadastroIndicators,
  CadastroPage,
  CadastroStatusBadge,
  CadastroTable,
  CadastroToolbar,
  cadastroTableCellClassName,
  cadastroTableHeaderCellClassName,
  cadastroTableHeaderClassName,
  cadastroTableRowClassName,
} from "@/components/cadastros";
import { Button } from "@/components/ui/Button";
import { EntitySidePanel } from "@/components/ui/EntitySidePanel";
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
  const [searchQuery, setSearchQuery] = useState("");
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

  const fornecedoresFiltrados = fornecedores.filter((fornecedor) =>
    [
      fornecedor.codigoInterno,
      displayName(fornecedor),
      fornecedor.documento,
      fornecedor.categoria,
      fornecedor.email,
      fornecedor.telefone,
      fornecedor.celular,
    ]
      .join(" ")
      .toLowerCase()
      .includes(searchQuery.trim().toLowerCase())
  );

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
    <CadastroPage
      title="Fornecedores"
      description="Cadastro e gestão operacional de fornecedores."
      toolbar={
        <CadastroToolbar
          searchValue={searchQuery}
          onSearchChange={setSearchQuery}
          searchPlaceholder="Pesquisar fornecedores..."
          actions={
            <NovoFornecedorButton onClick={openCreate} disabled={!canCreate} />
          }
        />
      }
      indicators={
        <CadastroIndicators
          items={[
            { label: "Total", value: fornecedores.length },
            { label: "Ativos", value: ativos },
            { label: "Inativos", value: inativos },
            { label: "Categorias", value: categoriasCadastradas },
          ]}
        />
      }
    >
      <CadastroTable minWidth="820px">
        <thead className={cadastroTableHeaderClassName}>
          <tr>
            <th className={cadastroTableHeaderCellClassName}>Fornecedor</th>
            <th className={cadastroTableHeaderCellClassName}>Documento</th>
            <th className={cadastroTableHeaderCellClassName}>Categoria</th>
            <th className={cadastroTableHeaderCellClassName}>Contato</th>
            <th className={cadastroTableHeaderCellClassName}>Status</th>
          </tr>
        </thead>
        <tbody>
          {fornecedoresFiltrados.map((fornecedor) => (
            <tr
              key={fornecedor.fornecedorId}
              tabIndex={0}
              onClick={() => openPanel(fornecedor.fornecedorId)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  openPanel(fornecedor.fornecedorId);
                }
              }}
              aria-label={`Ver fornecedor ${displayName(fornecedor)}`}
              className={`cursor-pointer ${cadastroTableRowClassName}`}
            >
              <td className={`${cadastroTableCellClassName} font-medium text-zinc-900`}>
                <div className="flex items-center gap-2.5">
                  <CadastroAvatar label={displayName(fornecedor)} icon={Truck} />
                  <div className="min-w-0">
                    <p className="truncate font-medium text-zinc-900">
                      {displayName(fornecedor)}
                    </p>
                    <p className="text-xs text-zinc-400">
                      {fornecedor.codigoInterno}
                    </p>
                  </div>
                </div>
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                {fornecedor.documento}
              </td>
              <td className={cadastroTableCellClassName}>
                <Badge>{fornecedor.categoria}</Badge>
              </td>
              <td className={`${cadastroTableCellClassName} text-zinc-500`}>
                {fornecedor.email || fornecedor.telefone || fornecedor.celular || "-"}
              </td>
              <td className={cadastroTableCellClassName}>
                <CadastroStatusBadge>{fornecedor.status}</CadastroStatusBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </CadastroTable>

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
    </CadastroPage>
  );
}
