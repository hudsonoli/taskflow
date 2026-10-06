"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound } from "lucide-react";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppData } from "@/lib/AppDataContext";
import { alterarSenhaInicial, fetchSessao } from "@/lib/auth";

export function TrocarSenhaInicialView() {
  const router = useRouter();
  const { recarregarSessao } = useAppData();
  const [nome, setNome] = useState<string | undefined>(undefined);
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacaoSenha, setConfirmacaoSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    fetchSessao().then((sessao) => setNome(sessao?.nome));
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await alterarSenhaInicial(senhaAtual, novaSenha, confirmacaoSenha);
      await recarregarSessao();
      router.replace("/meu-dia");
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível trocar a senha");
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 shadow-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <BrandLogo variant="auth" className="mb-4" />
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
            <KeyRound size={20} />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-fg">
            {nome ? `Olá, ${nome}` : "Defina sua nova senha"}
          </h1>
          <p className="mt-1 text-sm text-fg-muted">
            Este é seu primeiro acesso — por segurança, defina uma senha nova antes de continuar.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Input
            label="Senha atual (a temporária que você usou pra entrar)"
            type="password"
            autoComplete="current-password"
            value={senhaAtual}
            onChange={(event) => setSenhaAtual(event.target.value)}
            required
          />
          <Input
            label="Nova senha"
            type="password"
            autoComplete="new-password"
            value={novaSenha}
            onChange={(event) => setNovaSenha(event.target.value)}
            minLength={8}
            required
          />
          <Input
            label="Confirmar nova senha"
            type="password"
            autoComplete="new-password"
            value={confirmacaoSenha}
            onChange={(event) => setConfirmacaoSenha(event.target.value)}
            minLength={8}
            required
          />

          {erro && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
              {erro}
            </p>
          )}

          <Button type="submit" disabled={enviando} className="mt-1 justify-center">
            {enviando ? "Salvando…" : "Trocar senha e continuar"}
          </Button>
        </form>
      </div>
    </div>
  );
}
