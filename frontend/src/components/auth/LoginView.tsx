"use client";

import { useEffect, useRef, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Script from "next/script";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAppData } from "@/lib/AppDataContext";
import { login, loginGoogle } from "@/lib/auth";
import { NOME_PRODUTO } from "@/lib/produto";
import { MENSAGEM_SESSAO_EXPIRADA, destinoAposLogin } from "@/lib/sessao-expirada";
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
  sessaoExpirada = false,
  proximo = null,
}: {
  googleClientId: string | null;
  slug: string;
  nomeEmpresa?: string | null;
  /** `?reason=session_expired`: mostra o aviso discreto (a sessão caiu por expiração, não por erro do usuário) */
  sessaoExpirada?: boolean;
  /** `?next=` já validado no servidor (caminho interno do tenant); `null` = destino padrão */
  proximo?: string | null;
}) {
  const router = useRouter();
  const { recarregarSessao } = useAppData();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [senhaVisivel, setSenhaVisivel] = useState(false);
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
      router.replace(mustChangePassword ? caminhoDoTenant(slug, "trocar-senha-inicial") : destinoAposLogin(slug, proximo, caminhoDoTenant(slug, "meu-dia")));
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
      router.replace(mustChangePassword ? caminhoDoTenant(slug, "trocar-senha-inicial") : destinoAposLogin(slug, proximo, caminhoDoTenant(slug, "meu-dia")));
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
    // Tela SEMPRE clara (independe do tema da empresa, da preferência pessoal e do estilo Glass): o escopo `data-theme="claro"` redefine os tokens aqui dentro, e este arquivo não usa variantes
    // `dark:` nem classes que o estilo Glass sobrepõe (bg-app, bg-surface, border-zinc-*). `data-login-claro` também fixa o esquema de cores do <html> (barras de rolagem) — ver globals.css.
    <div data-theme="claro" data-login-claro className="min-h-screen bg-white text-fg lg:grid lg:grid-cols-2">
      {googleClientId && (
        <Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onLoad={() => setGoogleScriptPronto(true)} />
      )}

      <main className="flex min-h-screen flex-col px-6 py-8 sm:px-12 lg:min-h-0">
        <div aria-hidden className="mb-8 h-1 w-14 rounded-full bg-brand-gradient lg:hidden" />
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center">
          <div className="mb-8 flex flex-col items-start">
            <BrandLogo variant="auth" className="mb-6" />
            {/* A empresa é a identidade PRINCIPAL do acesso; o produto (TaskFlow) é secundário. */}
            <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-fg">{nomeEmpresa ?? `Entrar no ${NOME_PRODUTO}`}</h1>
            {nomeEmpresa && <p className="mt-1.5 text-xs font-semibold uppercase tracking-wide text-fg-subtle">Entrar no {NOME_PRODUTO}</p>}
            <p className="mt-2 text-sm text-fg-muted">Use o e-mail e a senha do seu cadastro.</p>
          </div>

          {sessaoExpirada && (
            <p role="status" className="mb-5 rounded-xl border border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-xs text-fg-muted">
              {MENSAGEM_SESSAO_EXPIRADA}
            </p>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              label="E-mail"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <label className="block text-sm">
              <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Senha</span>
              <span className="relative block">
                <input
                  className="field w-full rounded-xl py-2.5 pl-3 pr-11 text-sm"
                  type={senhaVisivel ? "text" : "password"}
                  autoComplete="current-password"
                  value={senha}
                  onChange={(event) => setSenha(event.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setSenhaVisivel((visivel) => !visivel)}
                  aria-label={senhaVisivel ? "Ocultar senha" : "Mostrar senha"}
                  aria-pressed={senhaVisivel}
                  className="absolute right-1.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-fg-subtle transition hover:bg-neutral-100 hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                >
                  {senhaVisivel ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
                </button>
              </span>
            </label>
            <div className="-mt-1 text-right">
              <Link href={hrefDoTenant(slug, "esqueci-senha")} className="text-xs font-medium text-fg-muted underline-offset-2 hover:text-fg hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-focus">
                Esqueci minha senha
              </Link>
            </div>

            {erro && (
              <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
                {erro}
              </p>
            )}

            <Button type="submit" disabled={enviando} className="mt-1 w-full justify-center py-3! text-sm!">
              {enviando ? "Entrando…" : "Entrar"}
            </Button>
          </form>

          {googleClientId && emailValido && (
            <div className="mt-5 flex flex-col items-center gap-3">
              <div className="flex w-full items-center gap-3 text-xs text-fg-subtle">
                <span className="h-px flex-1 bg-neutral-200" />
                ou
                <span className="h-px flex-1 bg-neutral-200" />
              </div>
              <div ref={googleButtonRef} />
            </div>
          )}

          <p className="mt-8 text-center text-xs text-fg-subtle">Sem acesso? Fale com o administrador da sua empresa.</p>
        </div>
      </main>

      {/* Painel de marca (só em telas largas): gradiente da própria empresa + brilhos em CSS — sem imagem externa nem depoimento inventado. Decorativo (aria-hidden). */}
      <aside aria-hidden className="relative hidden overflow-hidden bg-brand-gradient lg:flex lg:flex-col lg:justify-end lg:p-14">
        <div className="pointer-events-none absolute -left-24 -top-24 h-[28rem] w-[28rem] rounded-full bg-white/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-32 -right-16 h-[26rem] w-[26rem] rounded-full bg-black/15 blur-3xl" />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.12]"
          style={{ backgroundImage: "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)", backgroundSize: "48px 48px" }}
        />
        <div className="relative text-on-brand">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] opacity-80">{NOME_PRODUTO}</p>
          <p className="mt-3 max-w-md text-3xl font-semibold leading-tight tracking-tight">Gestão operacional para agências</p>
          <p className="mt-3 max-w-md text-base opacity-85">Tarefas, prazos, fluxos e equipe no mesmo lugar.</p>
        </div>
      </aside>
    </div>
  );
}
