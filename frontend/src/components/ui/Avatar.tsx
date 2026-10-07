"use client";

import { useState } from "react";
import { User } from "lucide-react";
import { estiloCorIdentificacao } from "@/lib/cores";
import { iniciais, srcDoAvatar } from "@/lib/notificacoes";

/**
 * Componente ÚNICO de avatar de usuário (também exportado como `UserAvatar`): foto quando existe, senão as
 * iniciais sobre a cor de identificação (com contraste automático). A foto própria vem como caminho da API
 * (`/usuarios/<id>/avatar?v=…`) e é servida pelo proxy autenticado, com cache por versão; URL externa (Google) e
 * pré-visualização local passam como estão. Se a imagem falhar ao carregar, cai nas iniciais. Sempre
 * `object-cover` — qualquer proporção de foto preenche o círculo/quadrado sem distorcer.
 */
export function Avatar({
  nome,
  corIdentificacao,
  fotoUrl,
  className,
}: {
  nome: string;
  corIdentificacao: string;
  fotoUrl?: string;
  className: string;
}) {
  const src = srcDoAvatar(fotoUrl);
  const [falhou, setFalhou] = useState<string | null>(null);

  if (src && falhou !== src) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={nome} className={`${className} object-cover`} onError={() => setFalhou(src)} />;
  }
  return (
    <div
      className={`${className} flex items-center justify-center font-bold text-white`}
      style={estiloCorIdentificacao(corIdentificacao)}
    >
      {iniciais(nome) || <User className="h-4 w-4" />}
    </div>
  );
}

export { Avatar as UserAvatar };
