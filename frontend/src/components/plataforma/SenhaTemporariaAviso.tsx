"use client";

import { useState } from "react";
import { Check, Copy, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { AVISO_SENHA_UNICA, urlDeAcessoDaEmpresa } from "@/lib/plataforma";
import { useOrigem } from "@/lib/useOrigem";

type Campo = "endereco" | "usuario" | "senha";

/**
 * Entrega da senha TEMPORÁRIA do Gestor (Fase 10B.1): endereço de acesso (`/e/<slug>/login`), usuário (e-mail) e a senha — exibida UMA ÚNICA vez, só neste estado de tela.
 * Nada vai para storage, URL, console ou rota; fechar a tela (ou recarregar) descarta a senha, e nenhum endpoint posterior a devolve. O servidor persistiu apenas o hash:
 * a senha é uma credencial real e o Gestor é obrigado a trocá-la no primeiro acesso. Não é enviada por e-mail.
 */
export function SenhaTemporariaAviso({ slug, urlAcesso, email, senha }: { slug: string; urlAcesso?: string; email: string; senha: string }) {
  const origem = useOrigem();
  const [copiado, setCopiado] = useState<Campo | null>(null);
  const endereco = urlAcesso && /^https?:\/\//i.test(urlAcesso) ? urlAcesso : urlDeAcessoDaEmpresa(origem, slug);

  async function copiar(campo: Campo, valor: string) {
    try {
      await navigator.clipboard.writeText(valor);
      setCopiado(campo);
    } catch {
      setCopiado(null); // sem permissão da área de transferência: o valor continua visível para cópia manual
    }
  }

  const linhas: { campo: Campo; rotulo: string; valor: string; botao: string; teste: string; mono: boolean }[] = [
    { campo: "endereco", rotulo: "Acesso", valor: endereco, botao: "Copiar endereço", teste: "url-acesso", mono: false },
    { campo: "usuario", rotulo: "Usuário", valor: email, botao: "Copiar usuário", teste: "usuario-gestor", mono: false },
    { campo: "senha", rotulo: "Senha temporária", valor: senha, botao: "Copiar senha", teste: "senha-temporaria", mono: true },
  ];

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line bg-surface-2 p-3">
      <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">
        <KeyRound size={12} /> Primeiro acesso do Gestor
      </p>
      {linhas.map((linha) => (
        <div key={linha.campo}>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">{linha.rotulo}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <code
              data-testid={linha.teste}
              className={`min-w-0 flex-1 select-all break-all rounded-lg border border-field-line bg-field px-3 py-2 font-mono text-fg ${linha.mono ? "text-sm tracking-wide" : "text-xs"}`}
            >
              {linha.valor}
            </code>
            <Button type="button" variant="secondary" onClick={() => void copiar(linha.campo, linha.valor)} aria-label={linha.botao}>
              {copiado === linha.campo ? <Check size={14} /> : <Copy size={14} />} {copiado === linha.campo ? "Copiado" : linha.botao}
            </Button>
          </div>
        </div>
      ))}
      <p
        role="note"
        className="rounded-xl border border-amber-300/60 bg-amber-50 px-3 py-2.5 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
      >
        {AVISO_SENHA_UNICA} Entregue por um canal seguro.
      </p>
    </div>
  );
}
