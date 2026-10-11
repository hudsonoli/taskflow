"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import clsx from "clsx";
import { useBranding } from "@/lib/BrandingContext";
import { srcDoLogo } from "@/lib/branding";
import { NOME_PRODUTO } from "@/lib/produto";
import { LOGO_ALTURA, LOGO_LARGURA } from "@/lib/personalizacao-logo";

// ÚNICO ponto de renderização do logo da Empresa (menu, login, recuperação de senha, prévia em Personalizar).
// O logo é sempre 320×132: o espaço é reservado com a mesma proporção, então nada "pula" quando a imagem
// carrega. <img> (não next/image) de propósito — preserva GIF animado byte a byte, sem otimização/recodificação.
// Sem logo (ou se a imagem falhar) volta à marca padrão do TaskFlow.




type Props = {
  /** header: altura fixa de 36px (menu superior) · auth: 160px de largura (telas de acesso) */
  variant: "header" | "auth";
  /** sem logo, o `header` mostra o NOME da empresa (ou "TaskFlow" fora de um ambiente de empresa) ao lado da marca padrão */
  className?: string;
  /** força um src (prévia em Personalizar, antes de salvar) */
  srcOverride?: string | null;
};

export function BrandLogo({ variant, className, srcOverride }: Props) {
  const { branding } = useBranding();
  const src = srcOverride !== undefined ? srcOverride : srcDoLogo(branding);
  const [falhou, setFalhou] = useState<string | null>(null);

  if (src && falhou !== src) {
    return (
      <span
        className={clsx("block shrink-0", variant === "header" ? "h-9" : "w-40", className)}
        style={{ aspectRatio: `${LOGO_LARGURA} / ${LOGO_ALTURA}` }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={branding.nome ? `Logo de ${branding.nome}` : "Logo da empresa"}
          width={LOGO_LARGURA}
          height={LOGO_ALTURA}
          className="h-full w-full object-contain"
          onError={() => setFalhou(src)}
        />
      </span>
    );
  }

  if (variant === "header") {
    return (
      <span className={clsx("flex shrink-0 items-center gap-2", className)}>
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-gradient shadow-lg shadow-indigo-500/30">
          <Sparkles size={18} />
        </span>
        <span className="hidden max-w-[14rem] truncate text-lg font-semibold tracking-tight text-fg sm:inline">{branding.nome ?? NOME_PRODUTO}</span>
      </span>
    );
  }
  return (
    <span className={clsx("flex h-11 w-11 items-center justify-center rounded-xl bg-brand-gradient shadow-lg shadow-indigo-500/30", className)}>
      <Sparkles size={20} />
    </span>
  );
}
