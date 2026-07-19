import type { RefObject } from "react";
import { EntityForm } from "@/components/entity";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { UsuarioCreatePayload } from "@/types/usuario-api";

const FOCUS_PRIMARY_CLASSNAME = "focus:!border-primary";

const perfilOptions = [
  { value: "admin", label: "Administrador" },
  { value: "gestor", label: "Gestor" },
  { value: "operador", label: "Operador" },
];

export type UsuarioCreateFormValue = UsuarioCreatePayload & {
  acessoSistema: boolean;
};

type UsuarioCreateFormProps = {
  formRef: RefObject<HTMLFormElement | null>;
  value: UsuarioCreateFormValue;
  disabled: boolean;
  error: string | null;
  onChange: (value: UsuarioCreateFormValue) => void;
  onSubmit: () => void;
};

export function UsuarioCreateForm({
  formRef,
  value,
  disabled,
  error,
  onChange,
  onSubmit,
}: UsuarioCreateFormProps) {
  function updatePerfil(perfilBase: string) {
    if (
      perfilBase !== "admin" &&
      perfilBase !== "gestor" &&
      perfilBase !== "operador"
    ) {
      return;
    }

    onChange({ ...value, perfilBase });
  }

  return (
    <form
      ref={formRef}
      className="min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <EntityForm>
        <div className="col-span-12 md:col-span-4">
          <Input
            label="Código interno"
            name="codigoInterno"
            placeholder="USR-001"
            value={value.codigoInterno}
            required
            maxLength={64}
            disabled={disabled}
            density="compact"
            className={FOCUS_PRIMARY_CLASSNAME}
            onChange={(event) =>
              onChange({ ...value, codigoInterno: event.target.value })
            }
          />
        </div>

        <div className="col-span-12 md:col-span-8">
          <Input
            label="Nome"
            name="nome"
            placeholder="Nome completo"
            value={value.nome}
            required
            maxLength={255}
            disabled={disabled}
            density="compact"
            className={FOCUS_PRIMARY_CLASSNAME}
            onChange={(event) =>
              onChange({ ...value, nome: event.target.value })
            }
          />
        </div>

        <div className="col-span-12 md:col-span-8">
          <Input
            label="E-mail"
            type="email"
            name="email"
            placeholder="usuario@empresa.com"
            value={value.email}
            required
            maxLength={255}
            disabled={disabled}
            density="compact"
            className={FOCUS_PRIMARY_CLASSNAME}
            onChange={(event) =>
              onChange({ ...value, email: event.target.value })
            }
          />
        </div>

        <div className="col-span-12 md:col-span-4">
          <Select
            label="Perfil"
            name="perfilBase"
            options={perfilOptions}
            value={value.perfilBase}
            required
            disabled={disabled}
            density="compact"
            className={FOCUS_PRIMARY_CLASSNAME}
            onChange={(event) => updatePerfil(event.target.value)}
          />
        </div>

        <div className="col-span-12">
          <label className="flex items-center gap-2 text-[11px] font-normal text-zinc-500">
            <input
              type="checkbox"
              name="acessoSistema"
              checked={value.acessoSistema}
              disabled={disabled}
              onChange={(event) =>
                onChange({
                  ...value,
                  acessoSistema: event.target.checked,
                })
              }
            />
            Acesso ao sistema
          </label>
        </div>
      </EntityForm>

      {error ? (
        <p
          role="alert"
          className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700"
        >
          {error}
        </p>
      ) : null}
    </form>
  );
}
