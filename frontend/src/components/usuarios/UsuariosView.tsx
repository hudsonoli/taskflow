"use client";

import { useCallback, useState } from "react";
import { Pencil } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { Button } from "@/components/ui/Button";
import {
  CadastroAvatar,
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
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  EMPRESA_PADRAO_ID,
  createPermissoesCatalogo,
  departamentos,
} from "@/lib/usuario-mock";
import type { UsuarioDraft } from "@/types/usuario";
import { UsuarioEditFormBody } from "./UsuarioEditFormBody";
import { useUsuarioDraft } from "./useUsuarioDraft";

function resolveDepartamentoNome(departamentoId: string): string {
  return (
    departamentos.find((departamento) => departamento.id === departamentoId)
      ?.nome ?? departamentoId
  );
}

// 2 estados (não 3): o modelo de Usuário não tem um equivalente a
// "Suspenso" hoje (só emAtividade: boolean) — inventar um terceiro estado
// seria regra de negócio nova, fora do escopo desta migração visual.
function usuarioStatusTone(emAtividade: boolean): "green" | "red" {
  return emAtividade ? "green" : "red";
}

const initialUsuarios: UsuarioDraft[] = [
  {
    id: "user-1",
    codigoInterno: "#2001",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Hudson Cunha",
    email: "hudson@technetgo.com.br",
    departamentoId: "dep-ti",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Owner",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: {
        valor: 12000,
        moeda: "BRL",
        dataInicio: "2024-01-10",
        observacao: "",
      },
      dadosBancarios: {
        chavePix: "hudson@technetgo.com.br",
        banco: "Banco XP",
        agencia: "0001",
        conta: "654321-0",
        tipoConta: "Corrente",
      },
    },
    historico: [
      {
        id: "hist-user-1-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "10/07/2026 09:00",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.10",
        acao: "Cadastro criado.",
        origem: "Web",
      },
      {
        id: "hist-user-1-2",
        usuarioId: "user-1",
        usuario: "Hudson Cunha",
        dataHora: "12/07/2026 10:15",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.10",
        acao: "Perfil alterado para Owner.",
        origem: "Web",
      },
    ],
  },
  {
    id: "user-2",
    codigoInterno: "#2002",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Ana Costa",
    email: "ana@empresa.com.br",
    departamentoId: "dep-diretoria",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Diretoria",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: { valor: null, moeda: "BRL", dataInicio: "", observacao: "" },
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
        id: "hist-user-2-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "02/07/2026 08:30",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.10",
        acao: "Cadastro criado.",
        origem: "Importação",
      },
    ],
  },
  {
    id: "user-3",
    codigoInterno: "#2003",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Carlos Lima",
    email: "carlos@agenciaexemplo.com.br",
    departamentoId: "dep-administrativo",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Gestor",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: { valor: null, moeda: "BRL", dataInicio: "", observacao: "" },
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
        id: "hist-user-3-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "03/07/2026 11:00",
        dispositivo: "macOS / Safari",
        ipOrigem: "192.168.1.22",
        acao: "Cadastro criado.",
        origem: "Web",
      },
      {
        id: "hist-user-3-2",
        usuarioId: "user-1",
        usuario: "Hudson Cunha",
        dataHora: "05/07/2026 09:40",
        dispositivo: "Windows / Chrome",
        ipOrigem: "192.168.1.10",
        acao: "Perfil alterado de Admin para Gestor.",
        origem: "Web",
      },
    ],
  },
  {
    id: "user-4",
    codigoInterno: "#2004",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "João Silva",
    email: "joao@empresa.com.br",
    departamentoId: "dep-atendimento",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Gestor",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: {
        valor: 7500,
        moeda: "BRL",
        dataInicio: "2025-03-01",
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
        id: "hist-user-4-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "04/07/2026 09:12",
        dispositivo: "Desktop / Chrome",
        ipOrigem: "192.168.0.10",
        acao: "Cadastro criado.",
        origem: "Web",
      },
      {
        id: "hist-user-4-2",
        usuarioId: "user-1",
        usuario: "Hudson Cunha",
        dataHora: "04/07/2026 09:20",
        dispositivo: "Desktop / Chrome",
        ipOrigem: "192.168.0.10",
        acao: "Departamento atualizado.",
        origem: "Web",
      },
    ],
  },
  {
    id: "user-5",
    codigoInterno: "#2005",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Maria Souza",
    email: "maria@empresa.com.br",
    departamentoId: "dep-criacao",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Operador",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: { valor: null, moeda: "BRL", dataInicio: "", observacao: "" },
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
    id: "user-6",
    codigoInterno: "#2006",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Pedro Santos",
    email: "pedro@empresa.com.br",
    departamentoId: "dep-midia",
    squad: "",
    paginaPrincipal: "Dashboard",
    perfil: "Operador",
    acessoSistema: false,
    emAtividade: false,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: { valor: null, moeda: "BRL", dataInicio: "", observacao: "" },
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
        id: "hist-user-6-1",
        usuarioId: "sistema",
        usuario: "Sistema",
        dataHora: "01/07/2026 08:00",
        dispositivo: "Windows / Edge",
        ipOrigem: "192.168.1.31",
        acao: "Cadastro criado.",
        origem: "Web",
      },
      {
        id: "hist-user-6-2",
        usuarioId: "user-1",
        usuario: "Hudson Cunha",
        dataHora: "09/07/2026 15:10",
        dispositivo: "Windows / Edge",
        ipOrigem: "192.168.1.31",
        acao: "Usuário desativado.",
        origem: "Web",
      },
    ],
  },
  {
    id: "user-7",
    codigoInterno: "#2007",
    empresaId: EMPRESA_PADRAO_ID,
    nome: "Cliente Exemplo",
    email: "contato@clienteexemplo.com.br",
    departamentoId: "dep-externo",
    squad: "",
    paginaPrincipal: "Clientes",
    perfil: "Cliente",
    acessoSistema: true,
    emAtividade: true,
    permissoes: createPermissoesCatalogo(),
    enderecos: [],
    informacoes: {
      telefone: "",
      celular: "",
      dataNascimento: "",
      rg: "",
      cpf: "",
    },
    administrativo: {
      salario: { valor: null, moeda: "BRL", dataInicio: "", observacao: "" },
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
];

type DrawerMode = "closed" | "peek" | "edit";

export function UsuariosView() {
  const [usuarios, setUsuarios] = useState<UsuarioDraft[]>(initialUsuarios);
  const [searchQuery, setSearchQuery] = useState("");
  const [drawerMode, setDrawerMode] = useState<DrawerMode>("closed");
  const [selectedUsuarioId, setSelectedUsuarioId] = useState<string | null>(null);
  const [editSessionId, setEditSessionId] = useState(0);

  const selectedUsuario = usuarios.find(
    (usuario) => usuario.id === selectedUsuarioId
  );

  const usuariosAtivos = usuarios.filter((usuario) => usuario.emAtividade).length;

  // Mesmos 4 perfis autorizados na guia Administrativa (Owner/Diretoria/
  // Gestor/Financeiro) — coincidência de valores, não reuso de
  // hasAdministrativeAccess: este indicador é uma contagem de perfil dos
  // usuários listados, não o gate de quem está vendo a tela agora.
  const usuariosGestao = usuarios.filter(
    (usuario) =>
      usuario.perfil === "Owner" ||
      usuario.perfil === "Diretoria" ||
      usuario.perfil === "Gestor" ||
      usuario.perfil === "Financeiro"
  ).length;

  const usuariosFiltrados = usuarios.filter((usuario) =>
    [
      usuario.codigoInterno,
      usuario.nome,
      usuario.email,
      resolveDepartamentoNome(usuario.departamentoId),
      usuario.perfil,
    ]
      .join(" ")
      .toLowerCase()
      .includes(searchQuery.trim().toLowerCase())
  );

  const usuarioDraft = useUsuarioDraft(selectedUsuario, editSessionId);

  function handleUpsert(draft: UsuarioDraft) {
    setUsuarios((current) => {
      const exists = current.some((usuario) => usuario.id === draft.id);

      if (!exists) return [draft, ...current];

      return current.map((usuario) => (usuario.id === draft.id ? draft : usuario));
    });
  }

  function openPeek(usuarioId: string) {
    setSelectedUsuarioId(usuarioId);
    setDrawerMode("peek");
  }

  function openEdit(usuarioId: string) {
    setSelectedUsuarioId(usuarioId);
    setDrawerMode("edit");
    setEditSessionId((current) => current + 1);
  }

  function openEditFromPeek() {
    setDrawerMode("edit");
    setEditSessionId((current) => current + 1);
  }

  function openCreate() {
    setSelectedUsuarioId(null);
    setDrawerMode("edit");
    setEditSessionId((current) => current + 1);
  }

  // Mesma regra de Clientes: usuário existente → cancelar/fechar durante a
  // edição volta ao peek; usuário novo → fecha por completo.
  const handleCloseIntent = useCallback(() => {
    if (drawerMode === "edit" && selectedUsuarioId) {
      setDrawerMode("peek");
      return;
    }

    setDrawerMode("closed");
    setSelectedUsuarioId(null);
  }, [drawerMode, selectedUsuarioId]);

  function handleSaveEdit() {
    handleUpsert(usuarioDraft.draft);
    setSelectedUsuarioId(usuarioDraft.draft.id);
    setDrawerMode("peek");
  }

  const { headerCell, cell } = getCadastroTableCellClassNames("compact");

  return (
    <PageShell density="compact">
      <PageHeader
        title="Usuários"
        description="Gestão de usuários, cargos e permissões."
        size="section"
        actions={
          <Button size="sm" colorScheme="brand" onClick={openCreate}>
            Novo Usuário
          </Button>
        }
      />

      <CadastroIndicators
        density="compact"
        items={[
          { label: "Total", value: usuarios.length },
          { label: "Ativos", value: usuariosAtivos },
          { label: "Gestão", value: usuariosGestao },
        ]}
      />

      <CadastroToolbar
        density="compact"
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder="Pesquisar usuários..."
      />

      <CadastroTable minWidth="820px">
        <thead className={cadastroTableHeaderClassName}>
          <tr>
            <th className={headerCell}>Usuário</th>
            <th className={headerCell}>Departamento</th>
            <th className={headerCell}>Perfil</th>
            <th className={headerCell}>Status</th>
            <th className={`${headerCell} text-right`}>Ações</th>
          </tr>
        </thead>

        <tbody>
          {usuariosFiltrados.map((usuario) => (
            <tr
              key={usuario.id}
              tabIndex={0}
              onClick={() => openPeek(usuario.id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  openPeek(usuario.id);
                }
              }}
              aria-label={`Ver usuário ${usuario.nome}`}
              className={`cursor-pointer ${cadastroTableRowClassName}`}
            >
              <td className={cell}>
                <div className="flex min-w-0 items-center gap-2">
                  <CadastroAvatar label={usuario.nome} density="compact" />
                  <div className="flex min-w-0 items-baseline gap-1">
                    <span className="shrink-0 text-[11px] font-normal text-zinc-400">
                      {usuario.codigoInterno}
                    </span>
                    <span className="min-w-0 truncate text-[13px] font-normal text-zinc-900">
                      {usuario.nome}
                    </span>
                  </div>
                </div>
              </td>

              <td className={`${cell} text-[11px] font-normal text-zinc-500`}>
                {resolveDepartamentoNome(usuario.departamentoId)}
              </td>

              <td className={cell}>
                <StatusPill tone="neutral" density="compact">
                  {usuario.perfil}
                </StatusPill>
              </td>

              <td className={cell}>
                <StatusPill tone={usuarioStatusTone(usuario.emAtividade)} density="compact">
                  {usuario.emAtividade ? "Ativo" : "Inativo"}
                </StatusPill>
              </td>

              <td className={`${cell} text-right`}>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    openEdit(usuario.id);
                  }}
                  aria-label={`Editar usuário ${usuario.nome}`}
                  title="Editar usuário"
                  className="inline-flex h-7 w-7 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
                >
                  <Pencil className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </CadastroTable>

      <EntityDrawer
        open={drawerMode !== "closed"}
        mode={drawerMode === "edit" ? "edit" : "peek"}
        onClose={handleCloseIntent}
        header={
          drawerMode === "edit" ? (
            <EntityHeader
              title={usuarioDraft.editing ? "Editar Usuário" : "Novo Usuário"}
              description={
                usuarioDraft.editing
                  ? `Código interno: ${usuarioDraft.draft.codigoInterno}`
                  : "Preencha nome, e-mail e departamento para continuar."
              }
              onClose={handleCloseIntent}
            />
          ) : (
            <EntityHeader
              title={selectedUsuario ? selectedUsuario.nome : "Usuário"}
              description={selectedUsuario?.codigoInterno}
              statusBadge={
                selectedUsuario ? (
                  <StatusPill
                    tone={usuarioStatusTone(selectedUsuario.emAtividade)}
                    density="compact"
                  >
                    {selectedUsuario.emAtividade ? "Ativo" : "Inativo"}
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
              primaryAction={{
                label: usuarioDraft.editing ? "Salvar Alterações" : "Salvar Usuário",
                onClick: handleSaveEdit,
                disabled: !usuarioDraft.canSubmit,
              }}
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
          <UsuarioEditFormBody
            draft={usuarioDraft.draft}
            onDraftChange={usuarioDraft.setDraft}
            activeSection={usuarioDraft.activeSection}
            onActiveSectionChange={usuarioDraft.setActiveSection}
          />
        ) : (
          <EntityPeek
            summary={
              selectedUsuario
                ? [
                    { label: "Nome", value: selectedUsuario.nome },
                    { label: "Código interno", value: selectedUsuario.codigoInterno },
                    { label: "E-mail", value: selectedUsuario.email },
                    {
                      label: "Departamento",
                      value: resolveDepartamentoNome(selectedUsuario.departamentoId),
                    },
                    { label: "Perfil", value: selectedUsuario.perfil },
                  ]
                : []
            }
            history={
              selectedUsuario ? (
                <EntityHistory
                  variant="compact"
                  events={[...selectedUsuario.historico]
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
