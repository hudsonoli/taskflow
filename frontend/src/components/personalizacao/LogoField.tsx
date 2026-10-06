"use client";

import { useRef, useState } from "react";
import { ImageUp, Trash2 } from "lucide-react";
import { BrandLogo } from "@/components/branding/BrandLogo";
import { Button } from "@/components/ui/Button";
import { LOGO_ALTURA, LOGO_LARGURA, validarLogoNoNavegador } from "@/lib/personalizacao-logo";

// Logo da Empresa: PNG ou GIF, exatamente 320×132 px, até 2 MB. O arquivo escolhido fica só no rascunho (prévia)
// até "Salvar alterações" — nada é enviado antes disso.
export function LogoField({
  arquivo,
  previaUrl,
  logoAtual,
  removendo,
  onEscolher,
  onRemover,
  onDesfazer,
}: {
  arquivo: File | null;
  previaUrl: string | null;
  logoAtual: boolean;
  removendo: boolean;
  onEscolher: (arquivo: File) => void;
  onRemover: () => void;
  onDesfazer: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function aoEscolher(lista: FileList | null) {
    const escolhido = lista?.[0];
    if (inputRef.current) inputRef.current.value = "";
    if (!escolhido) return;
    const mensagem = await validarLogoNoNavegador(escolhido);
    setErro(mensagem);
    if (!mensagem) onEscolher(escolhido);
  }

  // undefined → logo salvo (BrandLogo decide) · null → sem logo (removido) · string → arquivo escolhido
  const srcPrevia = arquivo && previaUrl ? previaUrl : removendo ? null : undefined;
  const temLogo = arquivo !== null || (logoAtual && !removendo);

  return (
    <div>
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Logo</p>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="shrink-0 rounded-xl border border-line bg-surface-2 p-3">
          <BrandLogo variant="auth" srcOverride={srcPrevia} />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-fg-muted">
            PNG ou GIF, exatamente {LOGO_LARGURA}×{LOGO_ALTURA} px, até 2 MB. GIF animado é mantido como enviado.
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input
              ref={inputRef}
              type="file"
              accept=".png,.gif,image/png,image/gif"
              className="sr-only"
              aria-label="Arquivo do logo"
              onChange={(event) => void aoEscolher(event.target.files)}
            />
            <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
              <ImageUp size={14} /> {temLogo ? "Trocar logo" : "Enviar logo"}
            </Button>
            {temLogo && (
              <Button type="button" variant="ghost" onClick={onRemover}>
                <Trash2 size={14} /> Remover logo
              </Button>
            )}
            {(arquivo || removendo) && (
              <Button type="button" variant="ghost" onClick={onDesfazer}>
                Desfazer
              </Button>
            )}
          </div>
          {arquivo && (
            <p className="mt-1.5 truncate text-xs text-fg-muted">Novo logo selecionado: {arquivo.name} (pendente de salvar)</p>
          )}
          {removendo && <p className="mt-1.5 text-xs text-fg-muted">O logo será removido ao salvar.</p>}
          {erro && (
            <p role="alert" className="mt-1.5 text-xs font-medium text-danger">
              {erro}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
