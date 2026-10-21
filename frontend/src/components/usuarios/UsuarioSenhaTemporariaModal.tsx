"use client";

import { useState } from "react";
import { KeyRound, X } from "lucide-react";
import { SenhaTemporariaAviso } from "@/components/plataforma/SenhaTemporariaAviso";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { useBranding } from "@/lib/BrandingContext";

/**
 * Entrega do primeiro acesso de um usuário da empresa por SENHA TEMPORÁRIA (hotfix de onboarding). A senha vem do SERVIDOR e vive só no estado desta tela: fechar (ou recarregar)
 * a descarta, e nenhum endpoint posterior a devolve. Não é enviada por e-mail.
 * - `senhaInicial`: acabou de ser criada (POST /usuarios) → já mostra a senha.
 * - `gerar`: quem ficou sem senha → pede confirmação (a senha anterior, se houver, deixa de valer) e só então gera.
 */
export function UsuarioSenhaTemporariaModal({
  nome,
  email,
  senhaInicial,
  gerar,
  onClose,
}: {
  nome: string;
  email: string;
  senhaInicial?: string;
  gerar?: () => Promise<string>;
  onClose: () => void;
}) {
  const { tenantSlug } = useBranding();
  const [senha, setSenha] = useState<string | null>(senhaInicial ?? null);
  const [gerando, setGerando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleGerar() {
    if (!gerar || gerando) return;
    setGerando(true);
    setErro(null);
    try {
      setSenha(await gerar());
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível gerar a senha temporária.");
    } finally {
      setGerando(false);
    }
  }

  return (
    <Modal open onClose={gerando ? () => {} : onClose} maxWidthClassName="max-w-lg">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-fg">Senha temporária de {nome}</h2>
            <p className="mt-1 text-sm text-fg-muted">
              {senha
                ? "Entregue o acesso à pessoa. No primeiro login ela precisa criar a própria senha."
                : "A pessoa ainda não definiu a própria senha. Uma nova senha temporária substitui a anterior, se houver."}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          disabled={gerando}
          aria-label="Fechar"
          className="rounded-full p-2 text-fg-subtle transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4">
        {senha ? (
          <SenhaTemporariaAviso slug={tenantSlug ?? ""} email={email} senha={senha} titulo="Primeiro acesso" />
        ) : (
          erro && <p className="text-xs text-red-600">{erro}</p>
        )}
      </div>

      <div className="mt-5 flex justify-end gap-2">
        {senha ? (
          <Button type="button" onClick={onClose}>
            Concluir
          </Button>
        ) : (
          <>
            <Button type="button" variant="secondary" onClick={onClose} disabled={gerando}>
              Cancelar
            </Button>
            <Button type="button" onClick={() => void handleGerar()} disabled={gerando}>
              {gerando ? "Gerando…" : "Gerar senha temporária"}
            </Button>
          </>
        )}
      </div>
    </Modal>
  );
}
