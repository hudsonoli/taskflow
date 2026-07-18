"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./useAuth";
import {
  completeLogin,
  createLoginRequestBody,
} from "../../lib/auth/login-flow";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";

type LoginFormProps = {
  returnTo: string | null;
};

function getLoginErrorMessage(status: number): string {
  switch (status) {
    case 401:
      return "E-mail ou senha inválidos.";
    case 403:
      return "Seu acesso ao sistema não está liberado.";
    case 422:
      return "Revise os dados informados e tente novamente.";
    default:
      return "Não foi possível entrar agora. Tente novamente em instantes.";
  }
}

export function LoginForm({ returnTo }: LoginFormProps) {
  const router = useRouter();
  const { refresh } = useAuth();
  const submittingRef = useRef(false);
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submittingRef.current) {
      return;
    }

    submittingRef.current = true;
    setSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(createLoginRequestBody(email, senha)),
      });

      if (!response.ok) {
        setErrorMessage(getLoginErrorMessage(response.status));
        return;
      }

      const completed = await completeLogin(response, returnTo, {
        refresh,
        redirect: (path) => router.replace(path),
      });
      if (!completed) {
        setErrorMessage(
          "Não foi possível entrar agora. Tente novamente em instantes.",
        );
      }
    } catch {
      setErrorMessage(
        "Não foi possível entrar agora. Verifique sua conexão e tente novamente.",
      );
    } finally {
      submittingRef.current = false;
      setSubmitting(false);
    }
  }

  return (
    <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
      <Input
        label="E-mail"
        type="email"
        name="email"
        value={email}
        autoComplete="email"
        inputMode="email"
        required
        disabled={submitting}
        className="h-12 rounded-2xl border-[#E9E9E9] bg-white/95 px-4 shadow-[0_1px_2px_rgba(0,0,0,0.025)] ring-0 placeholder:text-zinc-300 focus:border-[#F58220] focus:ring-4 focus:ring-[#F58220]/10 disabled:bg-zinc-50/70"
        onChange={(event) => setEmail(event.target.value)}
      />

      <Input
        label="Senha"
        type="password"
        name="senha"
        value={senha}
        autoComplete="current-password"
        required
        disabled={submitting}
        className="h-12 rounded-2xl border-[#E9E9E9] bg-white/95 px-4 shadow-[0_1px_2px_rgba(0,0,0,0.025)] ring-0 placeholder:text-zinc-300 focus:border-[#F58220] focus:ring-4 focus:ring-[#F58220]/10 disabled:bg-zinc-50/70"
        onChange={(event) => setSenha(event.target.value)}
      />

      {errorMessage ? (
        <p
          role="alert"
          className="rounded-2xl border border-red-200/80 bg-red-50/90 px-4 py-2.5 text-sm text-red-700 shadow-[0_1px_2px_rgba(0,0,0,0.025)]"
        >
          {errorMessage}
        </p>
      ) : null}

      <Button
        type="submit"
        colorScheme="brand"
        className="h-12 w-full rounded-2xl bg-[#F58220] text-sm text-white shadow-[0_5px_12px_rgba(245,130,32,0.11)] transition-colors duration-200 hover:bg-[#E56F10] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#F58220]"
        disabled={submitting}
      >
        {submitting ? "Entrando..." : "Entrar"}
      </Button>
    </form>
  );
}
