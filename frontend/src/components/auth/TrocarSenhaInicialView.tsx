"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { KeyRound } from "lucide-react";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppData } from "@/lib/AppDataContext";
import { definirSenhaInicial, fetchSessao } from "@/lib/auth";
import { validarTrocaInicial } from "@/lib/senha-inicial";
import { useTenantPath } from "@/lib/useTenantPath";

/**
 * Troca obrigatória do primeiro acesso (`/e/<slug>/trocar-senha-inicial`, Fase 10B.1). O usuário já entrou com a senha TEMPORÁRIA que a Gestão lhe passou; aqui informa
 * SÓ a nova senha e a confirmação — nenhuma "senha atual". O servidor é quem impõe a obrigação (toda a aplicação responde 403 até a troca); esta tela é apenas o caminho.
 * Depois de salvar, a sessão é recarregada (a obrigação some) e a pessoa segue para a home da MESMA empresa, com o mesmo slug e a mesma marca.
 */
export function TrocarSenhaInicialView() {
  const router = useRouter();
  const tp = useTenantPath();
  const { recarregarSessao } = useAppData();
  const [nome, setNome] = useState<string | undefined>(undefined);
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacaoSenha, setConfirmacaoSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [tentou, setTentou] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    fetchSessao().then((sessao) => setNome(sessao?.nome));
  }, []);

  const erros = validarTrocaInicial(novaSenha, confirmacaoSenha);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setTentou(true);
    setErro(null);
    if (erros.novaSenha || erros.confirmacaoSenha || enviando) return;
    setEnviando(true);
    try {
      await definirSenhaInicial(novaSenha, confirmacaoSenha);
      await recarregarSessao();
      router.replace(tp("meu-dia"));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível criar a senha");
      setEnviando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <div data-superficie="cartao-central" className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 shadow-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <BrandLogo variant="auth" className="mb-4" />
          <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
            <KeyRound size={20} />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-fg">{nome ? `Olá, ${nome}` : "Crie sua senha pessoal"}</h1>
          <p className="mt-1 text-sm text-fg-muted">Este é seu primeiro acesso — por segurança, crie sua senha pessoal antes de continuar.</p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
          <div>
            <Input
              label="Nova senha"
              type="password"
              autoComplete="new-password"
              value={novaSenha}
              onChange={(event) => setNovaSenha(event.target.value)}
              disabled={enviando}
              required
            />
            {tentou && erros.novaSenha && <p className="mt-1 text-xs font-medium text-danger">{erros.novaSenha}</p>}
          </div>
          <div>
            <Input
              label="Repita a nova senha"
              type="password"
              autoComplete="new-password"
              value={confirmacaoSenha}
              onChange={(event) => setConfirmacaoSenha(event.target.value)}
              disabled={enviando}
              required
            />
            {tentou && erros.confirmacaoSenha && <p className="mt-1 text-xs font-medium text-danger">{erros.confirmacaoSenha}</p>}
          </div>

          {erro && (
            <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
              {erro}
            </p>
          )}

          <Button type="submit" disabled={enviando} className="mt-1 justify-center">
            {enviando ? "Salvando…" : "Criar minha senha"}
          </Button>
        </form>
      </div>
    </div>
  );
}
