"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  EntityActions,
  EntityDrawer,
  EntityHeader,
} from "@/components/entity";
import { EmptyStateIllustration } from "@/components/ui/EmptyStateIllustration";
import type { Usuario } from "@/types/usuario-domain";
import {
  UsuarioCreateForm,
  type UsuarioCreateFormValue,
} from "./UsuarioCreateForm";
import { buildUsuarioUpdatePayload } from "./usuario-update";
import { useUsuarioDetail } from "./useUsuarioDetail";
import { useUsuarioUpdate } from "./useUsuarioUpdate";

type UsuarioEditDrawerProps = {
  usuarioId: string;
  onCancel: () => void;
  onUpdated: () => void;
};

function usuarioToFormValue(usuario: Usuario): UsuarioCreateFormValue {
  return {
    codigoInterno: usuario.codigoInterno,
    nome: usuario.nome,
    email: usuario.email,
    perfilBase: usuario.perfilBase,
    acessoSistema: usuario.acessoSistema,
  };
}

type UsuarioEditFormSessionProps = {
  usuario: Usuario;
  onCancel: () => void;
  onUpdated: () => void;
};

function UsuarioEditFormSession({
  usuario,
  onCancel,
  onUpdated,
}: UsuarioEditFormSessionProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const original = useMemo(() => usuarioToFormValue(usuario), [usuario]);
  const [value, setValue] = useState<UsuarioCreateFormValue>(original);
  const [validationError, setValidationError] = useState<string | null>(
    null,
  );
  const { submit, status, error, reset } = useUsuarioUpdate();
  const submitting = status === "submitting";
  const payload = buildUsuarioUpdatePayload(original, value);
  const dirty = Object.keys(payload).length > 0;
  const canSubmit =
    dirty &&
    value.codigoInterno.trim().length > 0 &&
    value.nome.trim().length > 0 &&
    value.email.trim().length > 0;

  const handleCloseIntent = useCallback(() => {
    if (submitting) return;

    setValue(original);
    setValidationError(null);
    reset();
    onCancel();
  }, [onCancel, original, reset, submitting]);

  function handleValueChange(nextValue: UsuarioCreateFormValue) {
    setValue(nextValue);
    setValidationError(null);
    if (status === "error") reset();
  }

  async function handleSubmit() {
    if (!formRef.current?.reportValidity()) return;

    if (!canSubmit) {
      if (dirty) {
        setValidationError(
          "Preencha o código interno, o nome e o e-mail.",
        );
      }
      return;
    }

    setValidationError(null);
    const succeeded = await submit(usuario.id, payload);
    if (!succeeded) return;

    reset();
    onUpdated();
  }

  return (
    <EntityDrawer
      open
      mode="edit"
      loading={submitting}
      onClose={handleCloseIntent}
      header={
        <EntityHeader
          title="Editar Usuário"
          description={usuario.codigoInterno}
          onClose={handleCloseIntent}
        />
      }
      footer={
        <EntityActions
          variant="edit"
          colorScheme="brand"
          primaryAction={{
            label: "Salvar Alterações",
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

export function UsuarioEditDrawer({
  usuarioId,
  onCancel,
  onUpdated,
}: UsuarioEditDrawerProps) {
  const { status, usuario, error, retry } = useUsuarioDetail(usuarioId);

  if (status === "success") {
    return (
      <UsuarioEditFormSession
        key={`${usuario.id}:${usuario.updatedAt}`}
        usuario={usuario}
        onCancel={onCancel}
        onUpdated={onUpdated}
      />
    );
  }

  return (
    <EntityDrawer
      open
      mode="edit"
      loading={status === "loading"}
      onClose={onCancel}
      header={
        <EntityHeader
          title="Editar Usuário"
          description={
            status === "loading"
              ? "Carregando dados do usuário..."
              : undefined
          }
          onClose={onCancel}
        />
      }
      footer={
        <EntityActions
          variant="edit"
          colorScheme="brand"
          primaryAction={{
            label: "Salvar Alterações",
            onClick: () => undefined,
            disabled: true,
          }}
          secondaryActions={[
            { label: "Cancelar", onClick: onCancel },
          ]}
        />
      }
    >
      {status === "loading" ? (
        <div
          role="status"
          aria-live="polite"
          className="min-w-0 flex-1 px-4 py-10 text-center text-sm text-zinc-500"
        >
          Carregando usuário...
        </div>
      ) : (
        <div className="min-w-0 flex-1 p-3">
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
      )}
    </EntityDrawer>
  );
}
