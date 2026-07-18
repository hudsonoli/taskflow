"use client";

import { useMemo, useState } from "react";
import { useAuth } from "@/components/auth/useAuth";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { readAuthErrorResponse } from "@/lib/auth/client";

export function AlterarSenhaView() {
  const { refresh } = useAuth();
  const [form, setForm] = useState({
    senhaAtual: "",
    novaSenha: "",
    confirmarSenha: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<
    { tone: "success" | "error"; message: string } | null
  >(null);

  const senhaValida = useMemo(
    () => form.novaSenha.length >= 8 && form.novaSenha === form.confirmarSenha,
    [form.novaSenha, form.confirmarSenha],
  );

  async function handleSubmit() {
    setSubmitting(true);
    setFeedback(null);

    try {
      const response = await fetch("/api/auth/alterar-senha", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          senhaAtual: form.senhaAtual,
          novaSenha: form.novaSenha,
          confirmacaoSenha: form.confirmarSenha,
        }),
      });

      if (response.status === 401) {
        const error = await readAuthErrorResponse(response);
        await refresh();
        setFeedback({ tone: "error", message: error.error.message });
        return;
      }

      if (response.status !== 204) {
        const error = await readAuthErrorResponse(response);
        setFeedback({ tone: "error", message: error.error.message });
        return;
      }

      setForm({ senhaAtual: "", novaSenha: "", confirmarSenha: "" });
      setFeedback({ tone: "success", message: "Senha alterada com sucesso." });
    } catch {
      setFeedback({
        tone: "error",
        message: "Não foi possível alterar a senha.",
      });
    } finally {
      setSubmitting(false);
    }
  }

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
            onChange={(event) =>
              setForm({ ...form, senhaAtual: event.target.value })
            }
          />
          <Input
            label="Nova senha"
            type="password"
            value={form.novaSenha}
            onChange={(event) =>
              setForm({ ...form, novaSenha: event.target.value })
            }
          />
          <Input
            label="Confirmar senha"
            type="password"
            value={form.confirmarSenha}
            onChange={(event) =>
              setForm({ ...form, confirmarSenha: event.target.value })
            }
          />

          {form.novaSenha && form.confirmarSenha && !senhaValida ? (
            <p className="text-sm text-red-600">
              A nova senha deve ter no mínimo 8 caracteres e ser igual à
              confirmação.
            </p>
          ) : null}

          {feedback ? (
            <p
              role="status"
              className={
                feedback.tone === "success"
                  ? "text-sm text-emerald-600"
                  : "text-sm text-red-600"
              }
            >
              {feedback.message}
            </p>
          ) : null}
        </div>

        <div className="mt-6 flex justify-end">
          <Button
            type="button"
            disabled={!senhaValida || submitting}
            onClick={() => void handleSubmit()}
          >
            {submitting ? "Salvando..." : "Salvar"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
