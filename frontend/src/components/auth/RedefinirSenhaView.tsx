"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CheckCircle2, KeyRound } from "lucide-react";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { confirmarRedefinicaoSenha, LinkRedefinicaoInvalidoError } from "@/lib/auth";

// Mínimo de caracteres da senha — o mesmo do backend (`AuthService._validate_new_password`), que
// continua sendo a autoridade; aqui só evita uma ida ao servidor por erro óbvio.
const TAMANHO_MINIMO_SENHA = 8;
const MENSAGEM_LINK_INVALIDO = "Este link é inválido ou expirou. Solicite uma nova redefinição de senha.";

/** `#token=<valor>` -> `<valor>`; qualquer outra coisa (ou fragmento ausente) -> `null`. */
function extrairToken(hash: string): string | null {
  const parametros = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
  const token = parametros.get("token");
  return token && token.trim() ? token.trim() : null;
}

/**
 * Redefinição de senha pelo link do e-mail (`/redefinir-senha#token=...`).
 *
 * O token vem no FRAGMENTO da URL: o navegador não o envia ao servidor web na requisição da
 * página, então ele não cai em log de proxy/servidor. Ao carregar, é lido uma vez, guardado SÓ em
 * memória (estado do componente — nunca localStorage/sessionStorage/cookie) e o fragmento é
 * removido da barra de endereço (`history.replaceState`), para não ficar em histórico/captura de
 * tela. Não autentica: depois do sucesso o usuário volta ao login.
 */
export function RedefinirSenhaView() {
  // `undefined` = ainda lendo a URL; `null` = não há token (ou foi recusado); string = em memória.
  const [token, setToken] = useState<string | null | undefined>(undefined);
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [concluido, setConcluido] = useState(false);

  useEffect(() => {
    // Mesmo padrão de AppDataContext: tira o setState do corpo do efeito (react-hooks/set-state-in-effect).
    const timeout = setTimeout(() => {
      setToken(extrairToken(window.location.hash));
      if (window.location.hash) {
        window.history.replaceState(null, "", window.location.pathname + window.location.search);
      }
    }, 0);
    return () => clearTimeout(timeout);
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setErro(null);
    if (novaSenha.length < TAMANHO_MINIMO_SENHA) {
      setErro(`A nova senha deve ter pelo menos ${TAMANHO_MINIMO_SENHA} caracteres.`);
      return;
    }
    if (novaSenha !== confirmacao) {
      setErro("A confirmação não confere com a nova senha.");
      return;
    }
    setEnviando(true);
    try {
      await confirmarRedefinicaoSenha(token, novaSenha, confirmacao);
      setToken(null); // uso único: o token sai da memória
      setNovaSenha("");
      setConfirmacao("");
      setConcluido(true);
    } catch (error) {
      if (error instanceof LinkRedefinicaoInvalidoError) {
        setToken(null);
      } else {
        setErro(error instanceof Error ? error.message : "Não foi possível redefinir a senha agora.");
      }
    } finally {
      setEnviando(false);
    }
  }

  if (token === undefined && !concluido) {
    return <Casca><p className="text-center text-sm text-fg-muted">Carregando…</p></Casca>;
  }

  if (concluido) {
    return (
      <Casca>
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400">
            <CheckCircle2 size={20} />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-fg">Senha redefinida com sucesso.</h1>
          <p className="text-sm text-fg-muted">Use a nova senha para entrar.</p>
          <Link href="/login" className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">
            Voltar para o login
          </Link>
        </div>
      </Casca>
    );
  }

  if (token === null) {
    return (
      <Casca>
        <div className="flex flex-col items-center gap-4 text-center">
          <h1 className="text-lg font-semibold tracking-tight text-fg">Link inválido</h1>
          <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
            {MENSAGEM_LINK_INVALIDO}
          </p>
          <Link href="/esqueci-senha" className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">
            Solicitar nova redefinição
          </Link>
          <Link href="/login" className="text-sm text-fg-muted hover:underline">
            Voltar para o login
          </Link>
        </div>
      </Casca>
    );
  }

  return (
    <Casca>
      <div className="mb-6 flex flex-col items-center text-center">
        <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
          <KeyRound size={20} />
        </div>
        <h1 className="text-lg font-semibold tracking-tight text-fg">Defina sua nova senha</h1>
        <p className="mt-1 text-sm text-fg-muted">Escolha uma senha nova para a sua conta.</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Input label="Nova senha" type="password" autoComplete="new-password" value={novaSenha} onChange={(event) => setNovaSenha(event.target.value)} required />
        <Input label="Confirmar nova senha" type="password" autoComplete="new-password" value={confirmacao} onChange={(event) => setConfirmacao(event.target.value)} required />

        {erro && (
          <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
            {erro}
          </p>
        )}

        <Button type="submit" disabled={enviando} className="justify-center">
          {enviando ? "Salvando…" : "Redefinir senha"}
        </Button>
      </form>
    </Casca>
  );
}

function Casca({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 shadow-sm">
        <div className="mb-5 flex justify-center">
          <BrandLogo variant="auth" />
        </div>
        {children}
      </div>
    </div>
  );
}
