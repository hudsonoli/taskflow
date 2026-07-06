"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";

export function AlterarSenhaView() {
  const [form, setForm] = useState({
    senhaAtual: "",
    novaSenha: "",
    confirmarSenha: "",
  });

  const senhaValida = useMemo(
    () => form.novaSenha.length >= 8 && form.novaSenha === form.confirmarSenha,
    [form.novaSenha, form.confirmarSenha]
  );

  return (
    <div className="p-8">
      <PageHeader
        title="Alterar senha"
        description="Atualize a senha de acesso da sua conta."
      />

      <Card>
        <div className="grid gap-5 md:max-w-xl">
          <Input
            label="Senha atual"
            type="password"
            value={form.senhaAtual}
            onChange={(event) => setForm({ ...form, senhaAtual: event.target.value })}
          />
          <Input
            label="Nova senha"
            type="password"
            value={form.novaSenha}
            onChange={(event) => setForm({ ...form, novaSenha: event.target.value })}
          />
          <Input
            label="Confirmar senha"
            type="password"
            value={form.confirmarSenha}
            onChange={(event) => setForm({ ...form, confirmarSenha: event.target.value })}
          />

          {form.novaSenha && form.confirmarSenha && !senhaValida ? (
            <p className="text-sm text-red-600">
              A nova senha deve ter no mínimo 8 caracteres e ser igual à confirmação.
            </p>
          ) : null}
        </div>

        <div className="mt-6 flex justify-end">
          <Button
            type="button"
            disabled={!senhaValida}
            onClick={() => console.log("save password", form)}
          >
            Salvar
          </Button>
        </div>
      </Card>
    </div>
  );
}
