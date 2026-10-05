"use client";

import { useState } from "react";
import Link from "next/link";
import { MailCheck, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { solicitarRedefinicaoSenha } from "@/lib/auth";

/**
 * "Esqueci minha senha": só pede o e-mail. Depois do envio mostra SEMPRE a mesma mensagem — exista a
 * conta ou não — para a tela nunca servir de teste de "esse e-mail está cadastrado?". Só uma falha
 * técnica (servidor fora do ar) aparece como erro e mantém o formulário para nova tentativa.
 */
export function EsqueciSenhaView() {
  const [email, setEmail] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      setMensagem(await solicitarRedefinicaoSenha(email.trim()));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível processar o pedido agora.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <div className="w-full max-w-sm rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30">
            {mensagem ? <MailCheck size={20} /> : <Sparkles size={20} />}
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">Esqueci minha senha</h1>
          {!mensagem && (
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              Informe o e-mail do seu cadastro e enviaremos as instruções para criar uma nova senha.
            </p>
          )}
        </div>

        {mensagem ? (
          <div className="flex flex-col gap-4">
            <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300">
              {mensagem}
            </p>
            <Link href="/login" className="text-center text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">
              Voltar para o login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="E-mail"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />

            {erro && (
              <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
                {erro}
              </p>
            )}

            <Button type="submit" disabled={enviando} className="justify-center">
              {enviando ? "Enviando…" : "Enviar instruções"}
            </Button>
            <Link href="/login" className="text-center text-sm text-zinc-500 hover:underline dark:text-zinc-400">
              Voltar para o login
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
