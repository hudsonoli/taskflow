"use client";

import { useCallback, useRef, useState } from "react";
import { Eye, Pencil } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  CadastroAvatar,
  CadastroIndicators,
  CadastroTable,
  CadastroToolbar,
  cadastroTableHeaderClassName,
  getCadastroTableCellClassNames,
} from "@/components/cadastros";
import {
  EntityActions,
  EntityDrawer,
  EntityHeader,
  EntityPeek,
} from "@/components/entity";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import type { Usuario } from "@/types/usuario-domain";
import {
  UsuarioCreateForm,
  type UsuarioCreateFormValue,
} from "./UsuarioCreateForm";
import { UsuarioEditDrawer } from "./UsuarioEditDrawer";
import { useUsuarioCreate } from "./useUsuarioCreate";
import { useUsuarioDetail } from "./useUsuarioDetail";
import { useUsuariosList } from "./useUsuariosList";

const usuarioDateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
  timeZone: "America/Sao_Paulo",
});

function formatUsuarioDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : usuarioDateTimeFormatter.format(date);
}

function usuarioStatusTone(
  status: Usuario["status"],
): "neutral" | "green" | "amber" | "red" {
  if (status === "ativo") return "green";
  if (status === "bloqueado") return "amber";
  if (status === "inativo") return "red";
  return "neutral";
}

function createInitialUsuarioFormValue(): UsuarioCreateFormValue {
  return {
    codigoInterno: "",
    nome: "",
    email: "",
    perfilBase: "operador",
    acessoSistema: true,
  };
}

type UsuarioDrawerState =
  | { mode: "closed" }
  | { mode: "peek"; usuarioId: string }
  | { mode: "create" }
  | { mode: "edit"; usuarioId: string };

type UsuarioCreateDrawerProps = {
  onClose: () => void;
  onCreated: () => void;
};

function UsuarioCreateDrawer({
  onClose,
  onCreated,
}: UsuarioCreateDrawerProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const [value, setValue] = useState<UsuarioCreateFormValue>(
    createInitialUsuarioFormValue,
  );
  const [validationError, setValidationError] = useState<string | null>(
    null,
  );
  const { submit, status, error, reset } = useUsuarioCreate();
  const submitting = status === "submitting";
  const canSubmit =
    value.codigoInterno.trim().length > 0 &&
    value.nome.trim().length > 0 &&
    value.email.trim().length > 0;

  const handleCloseIntent = useCallback(() => {
    if (submitting) return;

    setValue(createInitialUsuarioFormValue());
    setValidationError(null);
    reset();
    onClose();
  }, [onClose, reset, submitting]);

  function handleValueChange(nextValue: UsuarioCreateFormValue) {
    setValue(nextValue);
    setValidationError(null);
    if (status === "error") reset();
  }

  async function handleSubmit() {
    if (!formRef.current?.reportValidity()) return;

    if (!canSubmit) {
      setValidationError(
        "Preencha o código interno, o nome e o e-mail.",
      );
      return;
    }

    setValidationError(null);
    const succeeded = await submit(value);
    if (!succeeded) return;

    setValue(createInitialUsuarioFormValue());
    reset();
    onCreated();
  }

  return (
    <EntityDrawer
      open
      mode="edit"
      loading={submitting}
      onClose={handleCloseIntent}
      header={
        <EntityHeader
          title="Novo Usuário"
          description="Preencha os dados básicos para criar o usuário."
          onClose={handleCloseIntent}
        />
      }
      footer={
        <EntityActions
          variant="edit"
          colorScheme="brand"
          primaryAction={{
            label: "Salvar Usuário",
            onClick: () => void handleSubmit(),
            disabled: !canSubmit,
            loading: submitting,
          }}
          secondaryActions={[
            {
              label: "Cancelar",
              onClick: handleCloseIntent,
              disabled: submitting,
            },
          ]}
        />
      }
    >
      <UsuarioCreateForm
        formRef={formRef}
        value={value}
        disabled={submitting}
        error={validationError ?? error}
        onChange={handleValueChange}
        onSubmit={() => void handleSubmit()}
      />
    </EntityDrawer>
  );
}

type UsuarioPeekDrawerProps = {
  usuarioId: string;
  onClose: () => void;
  onEdit: () => void;
};

function UsuarioPeekDrawer({
  usuarioId,
  onClose,
  onEdit,
}: UsuarioPeekDrawerProps) {
  const { status, usuario, error, retry } = useUsuarioDetail(usuarioId);

  function renderContent() {
    switch (status) {
      case "loading":
        return (
          <div
            role="status"
            aria-live="polite"
            className="px-3 py-8 text-center text-sm text-zinc-500"
          >
            Carregando usuário...
          </div>
        );

      case "error":
        return (
          <div className="p-3">
            <EmptyStateIllustration
              size="compact"
              title="Não foi possível carregar o usuário"
              description={error}
              action={
                <Button size="sm" colorScheme="brand" onClick={retry}>
                  Tentar novamente
                </Button>
              }
            />
          </div>
        );

      case "success":
        return (
          <EntityPeek
            summary={[
              { label: "Código interno", value: usuario.codigoInterno },
              { label: "Nome", value: usuario.nome },
              { label: "E-mail", value: usuario.email },
              { label: "Perfil", value: usuario.perfilLabel },
              {
                label: "Status",
                value: usuario.statusLabel,
              },
              {
                label: "Data de criação",
                value: formatUsuarioDateTime(usuario.createdAt),
              },
              {
                label: "Data de atualização",
                value: formatUsuarioDateTime(usuario.updatedAt),
              },
            ]}
          />
        );
    }
  }

  return (
    <EntityDrawer
      open
      mode="peek"
      loading={status === "loading"}
      onClose={onClose}
      header={
        <EntityHeader
          title={status === "success" ? usuario.nome : "Usuário"}
          description={
            status === "success" ? usuario.codigoInterno : undefined
          }
          statusBadge={
            status === "success" ? (
              <StatusPill
                tone={usuarioStatusTone(usuario.status)}
                density="compact"
              >
                {usuario.statusLabel}
              </StatusPill>
            ) : undefined
          }
          onClose={onClose}
        />
      }
      footer={
        <EntityActions
          variant="peek"
          colorScheme="brand"
          primaryAction={{
            label: "Editar",
            onClick: onEdit,
          }}
          secondaryActions={[{ label: "Fechar", onClick: onClose }]}
        />
      }
    >
      {renderContent()}
    </EntityDrawer>
  );
}

export function UsuariosView() {
  const [searchQuery, setSearchQuery] = useState("");
  const [drawerState, setDrawerState] = useState<UsuarioDrawerState>({
    mode: "closed",
  });
  const {
    usuarios,
    status,
    error,
    retry,
  } =
    useUsuariosList(searchQuery);
  const refreshUsuarios = retry;

  const closeDrawer = useCallback(() => {
    setDrawerState({ mode: "closed" });
  }, []);

  const handleUsuarioCreated = useCallback(() => {
    refreshUsuarios();
    setDrawerState({ mode: "closed" });
  }, [refreshUsuarios]);

  const openUsuarioPeek = useCallback((usuarioId: string) => {
    setDrawerState({ mode: "peek", usuarioId });
  }, []);

  const openUsuarioEdit = useCallback((usuarioId: string) => {
    setDrawerState({ mode: "edit", usuarioId });
  }, []);

  const handleUsuarioUpdated = useCallback(
    (usuarioId: string) => {
      refreshUsuarios();
      setDrawerState({ mode: "peek", usuarioId });
    },
    [refreshUsuarios],
  );

  const usuariosAtivos = usuarios.filter(
    (usuario) => usuario.status === "ativo",
  ).length;
  const usuariosGestao = usuarios.filter(
    (usuario) =>
      usuario.perfilBase === "admin" || usuario.perfilBase === "gestor",
  ).length;
  const { headerCell, cell } = getCadastroTableCellClassNames("compact");

  function renderUsuariosContent() {
    switch (status) {
      case "loading":
        return (
          <div
            role="status"
            aria-live="polite"
            className="rounded-2xl border border-zinc-100 bg-white px-4 py-10 text-center text-sm text-zinc-500 shadow-sm"
          >
            Carregando usuários...
          </div>
        );

      case "error":
        return (
          <EmptyStateIllustration
            size="compact"
            title="Não foi possível carregar os usuários"
            description={error}
            action={
              <Button size="sm" colorScheme="brand" onClick={retry}>
                Tentar novamente
              </Button>
            }
          />
        );

      case "empty":
        return (
          <EmptyStateIllustration
            size="compact"
            title="Nenhum usuário encontrado"
            description={
              searchQuery.trim()
                ? `A busca por "${searchQuery.trim()}" não retornou usuários.`
                : "Ainda não há usuários disponíveis."
            }
          />
        );

      case "success":
        return (
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
              {usuarios.map((usuario) => (
                <tr
                  key={usuario.id}
                  className="border-b border-zinc-100 last:border-0"
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

                  <td
                    className={`${cell} text-[11px] font-normal text-zinc-500`}
                  >
                    —
                  </td>

                  <td className={cell}>
                    <Badge>{usuario.perfilLabel}</Badge>
                  </td>

                  <td className={cell}>
                    <StatusPill
                      tone={usuarioStatusTone(usuario.status)}
                      density="compact"
                    >
                      {usuario.statusLabel}
                    </StatusPill>
                  </td>

                  <td className={`${cell} text-right`}>
                    <div className="inline-flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => openUsuarioPeek(usuario.id)}
                        aria-label={`Visualizar usuário ${usuario.nome}`}
                        className="inline-flex h-7 items-center gap-1 rounded-full px-2 text-[11px] font-normal text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
                      >
                        <Eye
                          className="h-3.5 w-3.5"
                          strokeWidth={2}
                          aria-hidden="true"
                        />
                        Visualizar
                      </button>

                      <button
                        type="button"
                        onClick={() => openUsuarioEdit(usuario.id)}
                        aria-label={`Editar usuário ${usuario.nome}`}
                        title="Editar usuário"
                        className="inline-flex h-7 w-7 items-center justify-center rounded-full text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 focus-visible:ring-offset-2"
                      >
                        <Pencil
                          className="h-3.5 w-3.5"
                          strokeWidth={2}
                          aria-hidden="true"
                        />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </CadastroTable>
        );
    }
  }

  return (
    <PageShell density="compact">
      <PageHeader
        title="Usuários"
        description="Gestão de usuários, cargos e permissões."
        size="section"
        actions={
          <Button
            size="sm"
            colorScheme="brand"
            onClick={() => setDrawerState({ mode: "create" })}
          >
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

      {renderUsuariosContent()}

      {drawerState.mode === "peek" ? (
        <UsuarioPeekDrawer
          key={drawerState.usuarioId}
          usuarioId={drawerState.usuarioId}
          onClose={closeDrawer}
          onEdit={() => openUsuarioEdit(drawerState.usuarioId)}
        />
      ) : null}

      {drawerState.mode === "create" ? (
        <UsuarioCreateDrawer
          onClose={closeDrawer}
          onCreated={handleUsuarioCreated}
        />
      ) : null}

      {drawerState.mode === "edit" ? (
        <UsuarioEditDrawer
          key={drawerState.usuarioId}
          usuarioId={drawerState.usuarioId}
          onCancel={() => openUsuarioPeek(drawerState.usuarioId)}
          onUpdated={() => handleUsuarioUpdated(drawerState.usuarioId)}
        />
      ) : null}
    </PageShell>
  );
}
