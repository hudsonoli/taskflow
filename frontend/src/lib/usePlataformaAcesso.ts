"use client";

import { useEffect, useState } from "react";
import { consultarAcessoPlataforma } from "@/lib/plataforma-api";

/**
 * O usuário logado é Administrador da Plataforma? A resposta vem do BACKEND (`GET /plataforma/acesso`) — nunca de
 * e-mail, `perfil_base` ou `is_system_account`. Enquanto não houver confirmação, ou se a consulta falhar, é `false`
 * (a entrada some do menu; a API continua sendo a barreira real). Reconsulta ao trocar de usuário.
 */
export function usePlataformaAcesso(usuarioId: string | undefined): boolean {
  const [resultado, setResultado] = useState<{ usuarioId: string; permitido: boolean } | null>(null);

  useEffect(() => {
    if (!usuarioId) return;
    let cancelado = false;
    void consultarAcessoPlataforma().then((permitido) => {
      if (!cancelado) setResultado({ usuarioId, permitido });
    });
    return () => {
      cancelado = true;
    };
  }, [usuarioId]);

  // Resposta de OUTRO usuário (troca de sessão na mesma aba) nunca vale.
  return resultado !== null && resultado.usuarioId === usuarioId && resultado.permitido;
}
