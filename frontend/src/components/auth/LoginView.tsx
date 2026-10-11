"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Script from "next/script";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppData } from "@/lib/AppDataContext";
import { login, loginGoogle } from "@/lib/auth";
import { NOME_PRODUTO } from "@/lib/produto";
import { caminhoDoTenant, hrefDoTenant } from "@/lib/tenant";

// Tipagem mínima do Google Identity Services (carregado via <Script>, não um pacote npm —
// evita dependência nova só pra isso). Só os dois métodos realmente usados aqui.
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            login_hint?: string;
          }) => void;
          renderButton: (
            parent: HTMLElement,
            options: { theme?: string; size?: string; width?: number; text?: string },
          ) => void;
        };
      };
    };
  }
}

const EMAIL_VALIDO_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// Login da empresa da URL `/e/<slug>/login` (Fase 9D): a empresa vem SEMPRE do slug — não existe login "padrão" nem EMPRESA_CODIGO.
export function LoginView({
  googleClientId,
  slug,
  nomeEmpresa,
}: {
  googleClientId: string | null;
  slug: string;
  nomeEmpresa?: string | null;
}) {
  const router = useRouter();
  const { recarregarSessao } = useAppData();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [googleScriptPronto, setGoogleScriptPronto] = useState(false);
  const googleButtonRef = useRef<HTMLDivElement>(null);

  const emailValido = EMAIL_VALIDO_REGEX.test(email.trim());

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const { mustChangePassword } = await login(email, senha, slug);
      await recarregarSessao();
      router.replace(caminhoDoTenant(slug, mustChangePassword ? "trocar-senha-inicial" : "meu-dia"));
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Não foi possível entrar");
      setEnviando(false);
    }
  }

  async function handleGoogleCredential(idToken: string) {
    if (enviando) return; // evita clique duplo (callback do Google + estado em trânsito)
    setErro(null);
    setEnviando(true);
    try {
      const { mustChangePassword } = await loginGoogle(email, idToken, slug);
      await recarregarSessao();
      router.replace(caminhoDoTenant(slug, mustChangePassword ? "trocar-senha-inicial" : "meu-dia"));
    } catch (error) {
      // Falha no Google nunca apaga email/senha já digitados — login local continua intacto.
      setErro(error instanceof Error ? error.message : "Não foi possível entrar com Google");
      setEnviando(false);
    }
  }

  // Só habilita/renderiza o botão Google depois que o e-mail tem formato válido — nunca
  // antes (evita um endpoint "esse email existe?" implícito via comportamento do botão).
  // Re-inicializa a cada troca de e-mail válido pra manter `login_hint` atualizado.
  useEffect(() => {
    if (!googleClientId || !googleScriptPronto || !emailValido || !googleButtonRef.current) return;
    const container = googleButtonRef.current;
    container.innerHTML = "";
    window.google?.accounts.id.initialize({
      client_id: googleClientId,
      callback: (response) => {
        void handleGoogleCredential(response.credential);
      },
      login_hint: email.trim(),
    });
    window.google?.accounts.id.renderButton(container, { theme: "outline", size: "large", width: 320, text: "continue_with" });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- handleGoogleCredential fecha sobre email/enviando atuais a cada render; recriar o efeito a cada mudança deles re-inicializaria o botão sem necessidade.
  }, [googleClientId, googleScriptPronto, emailValido, email]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      {googleClientId && (
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onLoad={() => setGoogleScriptPronto(true)} />
      )}
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 shadow-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <BrandLogo variant="auth" className="mb-3" />
          {/* A empresa é a identidade PRINCIPAL do acesso; o produto (TaskFlow) é secundário. */}
          <h1 className="text-lg font-semibold tracking-tight text-fg">{nomeEmpresa ?? `Entrar no ${NOME_PRODUTO}`}</h1>
          {nomeEmpresa && <p className="mt-0.5 text-xs font-medium uppercase tracking-wide text-fg-subtle">Entrar no {NOME_PRODUTO}</p>}
          <p className="mt-1 text-sm text-fg-muted">Use o e-mail e a senha do seu cadastro.</p>
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
          <div className="-mt-2 text-right">
            <Link href={hrefDoTenant(slug, "esqueci-senha")} className="text-xs text-fg-muted hover:text-indigo-600 hover:underline dark:hover:text-indigo-400">
              Esqueci minha senha
            </Link>
          </div>

          {erro && (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
              {erro}
            </p>
          )}

          <Button type="submit" disabled={enviando} className="mt-1 justify-center">
            {enviando ? "Entrando…" : "Entrar"}
          </Button>
        </form>

        {googleClientId && emailValido && (
          <div className="mt-4 flex flex-col items-center gap-3">
            <div className="flex w-full items-center gap-3 text-xs text-fg-subtle">
              <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
              ou
              <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
            </div>
            <div ref={googleButtonRef} />
          </div>
        )}
      </div>
    </div>
  );
}
