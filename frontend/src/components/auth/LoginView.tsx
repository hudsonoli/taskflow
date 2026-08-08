"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppData } from "@/lib/AppDataContext";
import { login } from "@/lib/auth";

export function LoginView() {
  const router = useRouter();
  const { recarregarSessao } = useAppData();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const { mustChangePassword } = await login(email, senha);
      await recarregarSessao();
      router.replace(mustChangePassword ? "/trocar-senha-inicial" : "/meu-dia");
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível entrar");
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <div className="w-full max-w-sm rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
            <Sparkles size={20} />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Entrar no Taskfloww</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Use o e-mail e a senha do seu cadastro.</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="E-mail"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <Input
            label="Senha"
            type="password"
            autoComplete="current-password"
            value={senha}
            onChange={(event) => setSenha(event.target.value)}
            required
          />

          {erro && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
              {erro}
            </p>
          )}

          <Button type="submit" disabled={enviando} className="mt-1 justify-center">
            {enviando ? "Entrando…" : "Entrar"}
          </Button>
        </form>
      </div>
    </div>
  );
}
