"use client";

import { useCallback, useMemo, useState } from "react";
import { Pencil } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { Button } from "@/components/ui/Button";
import {
  CadastroIndicators,
  CadastroTable,
  CadastroToolbar,
  cadastroTableHeaderClassName,
  cadastroTableRowClassName,
  getCadastroTableCellClassNames,
} from "@/components/cadastros";
import {
  EntityActions,
  EntityDrawer,
  EntityHeader,
  EntityHistory,
  EntityPeek,
} from "@/components/entity";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  EMPRESA_PADRAO_ID,
  equipesDisponiveis,
  responsaveisDisponiveis,
} from "@/lib/cliente-mock";
import { normalizeSearchText, normalizeSearchToken } from "@/lib/search-normalize";
import type { ClienteDraft, ClienteStatus } from "@/types/cliente";
import { ClienteAvatar } from "./ClienteAvatar";
import { ClienteEditFormBody } from "./ClienteEditFormBody";
import { useClienteDraft } from "./useClienteDraft";

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

// Campos pesquisáveis hoje: código interno, nome fantasia, razão social,
// documento, e-mail, equipe responsável e responsável comercial. Quando o
// modelo de Cliente ganhar Tags, basta somar mais um item ao textHaystack —
// não há estrutura de Tags neste momento (types/cliente.ts não a possui).
function matchesCliente(cliente: ClienteDraft, query: string): boolean {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) return true;

  const textHaystack = normalizeSearchText(
    [
      cliente.codigoInterno,
      cliente.nomeFantasia,
      cliente.nomeRazaoSocial,
      cliente.documento,
      cliente.email,
      resolveEquipeNome(cliente.equipeResponsavelId),
      resolveResponsavelNome(cliente.responsavelComercialId),
    ].join(" ")
  );

  if (textHaystack.includes(normalizedQuery)) return true;

  // Comparação tolerante a pontuação (ex.: "12345678000190" ↔
  // "12.345.678/0001-90"), aplicada só aos campos de documento/código.
  const tokenQuery = normalizeSearchToken(query);
  if (!tokenQuery) return false;

  const tokenHaystack = normalizeSearchToken(
    `${cliente.codigoInterno} ${cliente.documento}`
  );

  return tokenHaystack.includes(tokenQuery);
}

// Mapeamento de cor por estado — específico de Clientes, não vive no
// CadastroStatusBadge compartilhado (que é usado por outras 6 telas com uma
// heurística de texto diferente, sem "Suspenso" e com Inativo em cinza).
// StatusPill já tem os três tons semânticos prontos (green/amber/red),
// dirigidos aqui por um valor explícito, não por heurística.
function clienteStatusTone(status: ClienteStatus): "green" | "amber" | "red" {
  if (status === "Ativo") return "green";
  if (status === "Suspenso") return "amber";
  return "red";
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
    administrativo: {
      feeMensal: {
        valor: 3500,
        moeda: "BRL",
        dataInicio: "2026-01-15",
        observacao: "",
      },
      dadosBancarios: {
        chavePix: "12.345.678/0001-90",
        banco: "Banco XP",
        agencia: "0001",
        conta: "123456-7",
        tipoConta: "Corrente",
      },
    },
    historico: [
      {
        id: "hist-cliente-1-1",
        usuarioId: "sistema",
        usuario: "João Silva",
        dataHora: "10/07/2026 09:15",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.10",
        acao: "Cliente criado.",
        origem: "Web",
      },
      {
        id: "hist-cliente-1-2",
        usuarioId: "user-4",
        usuario: "Maria Souza",
        dataHora: "12/07/2026 14:30",
        dispositivo: "macOS / Safari",
        ipOrigem: "192.168.1.22",
        acao: "Dados cadastrais alterados.",
        origem: "Web",
      },
      {
        id: "hist-cliente-1-3",
        usuarioId: "user-4",
        usuario: "João Silva",
        dataHora: "13/07/2026 17:42",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.20",
        acao: "Endereço alterado.",
        origem: "API",
      },
    ],
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
    status: "Suspenso",
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
    administrativo: {
      feeMensal: {
        valor: 1800,
        moeda: "BRL",
        dataInicio: "2026-02-01",
        observacao: "Fee reduzido durante suspensão.",
      },
      dadosBancarios: {
        chavePix: "",
        banco: "",
        agencia: "",
        conta: "",
        tipoConta: "Corrente",
      },
    },
    historico: [
      {
        id: "hist-cliente-2-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "02/07/2026 10:00",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.10",
        acao: "Cliente criado.",
        origem: "Importação",
      },
      {
        id: "hist-cliente-2-2",
        usuarioId: "user-5",
        usuario: "Maria Souza",
        dataHora: "11/07/2026 08:50",
        dispositivo: "macOS / Safari",
        ipOrigem: "192.168.1.22",
        acao: "Status alterado de Ativo para Suspenso.",
        origem: "Web",
      },
    ],
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
    administrativo: {
      feeMensal: {
        valor: null,
        moeda: "BRL",
        dataInicio: "",
        observacao: "",
      },
      dadosBancarios: {
        chavePix: "",
        banco: "",
        agencia: "",
        conta: "",
        tipoConta: "Corrente",
      },
    },
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
    administrativo: {
      feeMensal: {
        valor: null,
        moeda: "BRL",
        dataInicio: "",
        observacao: "",
      },
      dadosBancarios: {
        chavePix: "",
        banco: "",
        agencia: "",
        conta: "",
        tipoConta: "Corrente",
      },
    },
    historico: [
      {
        id: "hist-cliente-4-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "01/07/2026 08:00",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.10",
        acao: "Cliente criado.",
        origem: "Integração",
      },
      {
        id: "hist-cliente-4-2",
        usuarioId: "user-2",
        usuario: "Usuário Autorizado",
        dataHora: "05/07/2026 11:20",
        dispositivo: "Windows / Edge",
        ipOrigem: "192.168.1.31",
        acao: "Dados financeiros alterados.",
        origem: "Web",
      },
      {
        id: "hist-cliente-4-3",
        usuarioId: "user-2",
        usuario: "Maria Souza",
        dataHora: "08/07/2026 16:05",
        dispositivo: "macOS / Safari",
        ipOrigem: "192.168.1.22",
        acao: "Status alterado de Suspenso para Inativo.",
        origem: "Web",
      },
    ],
  },
];

type DrawerMode = "closed" | "peek" | "edit";

export function ClientesView() {
  const [clientes, setClientes] = useState<ClienteDraft[]>(initialClientes);
  const [searchQuery, setSearchQuery] = useState("");
  const [drawerMode, setDrawerMode] = useState<DrawerMode>("closed");
  const [selectedClienteId, setSelectedClienteId] = useState<string | null>(null);
  const [editSessionId, setEditSessionId] = useState(0);

  const selectedCliente = clientes.find(
    (cliente) => cliente.clienteId === selectedClienteId
  );

  const clientesAtivos = clientes.filter(
    (cliente) => cliente.status === "Ativo"
  ).length;

  const clientesSuspensos = clientes.filter(
    (cliente) => cliente.status === "Suspenso"
  ).length;

  const clientesInativos = clientes.filter(
    (cliente) => cliente.status === "Inativo"
  ).length;

  const clientesFiltrados = useMemo(
    () => clientes.filter((cliente) => matchesCliente(cliente, searchQuery)),
    [clientes, searchQuery]
  );

  const resultadosLabel = searchQuery.trim()
    ? `${clientesFiltrados.length} resultado${clientesFiltrados.length === 1 ? "" : "s"} encontrado${clientesFiltrados.length === 1 ? "" : "s"}`
    : `${clientesFiltrados.length} cliente${clientesFiltrados.length === 1 ? "" : "s"}`;

  const clienteDraft = useClienteDraft(selectedCliente, editSessionId);

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

  function openPeek(clienteId: string) {
    setSelectedClienteId(clienteId);
    setDrawerMode("peek");
  }

  function openEdit(clienteId: string) {
    setSelectedClienteId(clienteId);
    setDrawerMode("edit");
    setEditSessionId((current) => current + 1);
  }

  function openEditFromPeek() {
    setDrawerMode("edit");
    setEditSessionId((current) => current + 1);
  }

  function openCreate() {
    setSelectedClienteId(null);
    setDrawerMode("edit");
    setEditSessionId((current) => current + 1);
  }

  // Fluxo oficial: cliente existente → cancelar/fechar durante a edição
  // volta ao peek da mesma entidade, nunca fecha o Drawer. Cliente novo
  // (sem selectedClienteId) → fecha por completo. Mesma função atende
  // Escape, clique no backdrop, botão "X" do cabeçalho e o botão
  // "Cancelar"/"Fechar" do rodapé — um único ponto de decisão.
  //
  // useCallback (não uma function declaration comum) porque é passada como
  // onClose para o EntityDrawer, cujo efeito de foco/trap depende dessa
  // referência (entity/EntityDrawer.tsx). Sem memoização, cada tecla
  // digitada em qualquer campo do formulário re-renderiza a View com uma
  // nova closure, o efeito reexecuta, e o cleanup+setup do Drawer move o
  // foco para o primeiro elemento focável do header (o botão fechar) — daí
  // o bug de precisar reclicar no campo a cada letra.
  const handleCloseIntent = useCallback(() => {
    if (drawerMode === "edit" && selectedClienteId) {
      setDrawerMode("peek");
      return;
    }

    setDrawerMode("closed");
    setSelectedClienteId(null);
  }, [drawerMode, selectedClienteId]);

  function handleSaveEdit() {
    handleUpsert(clienteDraft.draft);
    setSelectedClienteId(clienteDraft.draft.clienteId);
    setDrawerMode("peek");
  }

  const { headerCell, cell } = getCadastroTableCellClassNames("compact");

  return (
    <PageShell density="compact">
      <CadastroIndicators
        density="compact"
        items={[
          { label: "Total", value: clientes.length },
          { label: "Ativos", value: clientesAtivos },
          { label: "Suspensos", value: clientesSuspensos },
          { label: "Inativos", value: clientesInativos },
        ]}
      />

      <CadastroToolbar
        density="compact"
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Pesquisar clientes..."
        actions={
          <Button size="sm" colorScheme="brand" onClick={openCreate}>
            Novo Cliente
          </Button>
        }
      />

      <p className="px-1 text-[11px] text-zinc-400">{resultadosLabel}</p>

      <CadastroTable minWidth="900px">
        <thead className={cadastroTableHeaderClassName}>
          <tr>
            <th className={headerCell}>Cliente</th>
            <th className={headerCell}>Documento</th>
            <th className={headerCell}>Equipe</th>
            <th className={headerCell}>Responsável</th>
            <th className={headerCell}>Status</th>
            <th className={`${headerCell} text-right`}>Ações</th>
          </tr>
        </thead>

        <tbody>
          {clientesFiltrados.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-[12px] text-zinc-400">
                {searchQuery.trim()
                  ? `Nenhum cliente encontrado para "${searchQuery.trim()}".`
                  : "Nenhum cliente encontrado."}
              </td>
            </tr>
          ) : null}

          {clientesFiltrados.map((cliente) => {
            const nome = cliente.nomeFantasia || cliente.nomeRazaoSocial;

            return (
              <tr
                key={cliente.clienteId}
                tabIndex={0}
                onClick={() => openPeek(cliente.clienteId)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openPeek(cliente.clienteId);
                  }
                }}
                aria-label={`Ver cliente ${nome}`}
                className={`cursor-pointer ${cadastroTableRowClassName}`}
              >
                <td className={cell}>
                  <div className="flex min-w-0 items-center gap-2">
                    <ClienteAvatar clienteId={cliente.clienteId} sigla={cliente.sigla} />
                    <div className="flex min-w-0 items-baseline gap-1">
                      <span className="shrink-0 text-[10px] font-normal text-zinc-400">
                        {cliente.codigoInterno}
                      </span>
                      <span className="min-w-0 truncate text-[13px] font-normal leading-tight text-zinc-800">
                        {nome}
                      </span>
                    </div>
                  </div>
                </td>

                <td className={`${cell} text-[11px] font-normal text-zinc-500`}>
                  {cliente.documento || "-"}
                </td>

                <td className={`${cell} text-[11px] font-normal text-zinc-500`}>
                  {resolveEquipeNome(cliente.equipeResponsavelId)}
                </td>

                <td className={`${cell} text-[11px] font-normal text-zinc-500`}>
                  {resolveResponsavelNome(cliente.responsavelComercialId)}
                </td>

                <td className={cell}>
                  <StatusPill tone={clienteStatusTone(cliente.status)} density="compact">
                    {cliente.status}
                  </StatusPill>
                </td>

                <td className={`${cell} text-right`}>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      openEdit(cliente.clienteId);
                    }}
                    aria-label={`Editar cliente ${nome}`}
                    title="Editar cliente"
                    className="inline-flex h-7 w-7 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
                  >
                    <Pencil className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </CadastroTable>

      <EntityDrawer
        open={drawerMode !== "closed"}
        mode={drawerMode === "edit" ? "edit" : "peek"}
        onClose={handleCloseIntent}
        header={
          drawerMode === "edit" ? (
            <EntityHeader
              title={clienteDraft.editing ? "Editar Cliente" : "Novo Cliente"}
              description={
                clienteDraft.step === "documento"
                  ? "Informe o CNPJ ou CPF para iniciar o cadastro."
                  : `Código interno: ${clienteDraft.draft.codigoInterno}`
              }
              onClose={handleCloseIntent}
            />
          ) : (
            <EntityHeader
              title={
                selectedCliente
                  ? selectedCliente.nomeFantasia || selectedCliente.nomeRazaoSocial
                  : "Cliente"
              }
              description={selectedCliente?.codigoInterno}
              statusBadge={
                selectedCliente ? (
                  <StatusPill
                    tone={clienteStatusTone(selectedCliente.status)}
                    density="compact"
                  >
                    {selectedCliente.status}
                  </StatusPill>
                ) : undefined
              }
              onClose={handleCloseIntent}
            />
          )
        }
        footer={
          drawerMode === "edit" ? (
            <EntityActions
              variant="edit"
              colorScheme="brand"
              primaryAction={
                clienteDraft.step === "documento"
                  ? {
                      label: clienteDraft.loadingLookup ? "Buscando dados..." : "Continuar",
                      onClick: clienteDraft.handleDocumentContinue,
                      disabled: !clienteDraft.canContinue || clienteDraft.loadingLookup,
                      loading: clienteDraft.loadingLookup,
                    }
                  : {
                      label: clienteDraft.editing ? "Salvar Alterações" : "Salvar Cliente",
                      onClick: handleSaveEdit,
                    }
              }
              secondaryActions={[{ label: "Cancelar", onClick: handleCloseIntent }]}
            />
          ) : (
            <EntityActions
              variant="peek"
              colorScheme="brand"
              primaryAction={{ label: "Editar", onClick: openEditFromPeek }}
              secondaryActions={[{ label: "Fechar", onClick: handleCloseIntent }]}
            />
          )
        }
      >
        {drawerMode === "edit" ? (
          <ClienteEditFormBody
            step={clienteDraft.step}
            editing={clienteDraft.editing}
            documentoInput={clienteDraft.documentoInput}
            onDocumentoInputChange={clienteDraft.setDocumentoInput}
            documentType={clienteDraft.documentType}
            draft={clienteDraft.draft}
            onDraftChange={clienteDraft.setDraft}
            onNomeFantasiaChange={clienteDraft.handleNomeFantasiaChange}
            onSiglaChange={clienteDraft.handleSiglaChange}
            activeSection={clienteDraft.activeSection}
            onActiveSectionChange={clienteDraft.setActiveSection}
          />
        ) : (
          <EntityPeek
            summary={
              selectedCliente
                ? [
                    {
                      label: "Nome",
                      value: selectedCliente.nomeFantasia || selectedCliente.nomeRazaoSocial,
                    },
                    { label: "Código interno", value: selectedCliente.codigoInterno },
                    { label: "Documento", value: selectedCliente.documento },
                    {
                      label: "Contato",
                      value:
                        selectedCliente.email ||
                        selectedCliente.telefone ||
                        selectedCliente.celular ||
                        "-",
                    },
                    {
                      label: "Equipe responsável",
                      value: resolveEquipeNome(selectedCliente.equipeResponsavelId),
                    },
                    {
                      label: "Responsável comercial",
                      value: resolveResponsavelNome(selectedCliente.responsavelComercialId),
                    },
                  ]
                : []
            }
            history={
              selectedCliente ? (
                <EntityHistory
                  variant="compact"
                  events={[...selectedCliente.historico]
                    .reverse()
                    .map((evento) => ({
                      id: evento.id,
                      usuario: evento.usuario,
                      dataHora: evento.dataHora,
                      acao: evento.acao,
                    }))}
                />
              ) : undefined
            }
          />
        )}
      </EntityDrawer>
    </PageShell>
  );
}
