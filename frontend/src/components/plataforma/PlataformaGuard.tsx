"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { AcessoNegado } from "@/components/operacional/AcessoNegado";
import { useAppData } from "@/lib/AppDataContext";
import { abrirSessaoPlataforma, consultarAcessoPlataforma } from "@/lib/plataforma-api";

type Estado = "verificando" | "liberado" | "negado";

/**
 * Proteção de URL direta de `/gestao/**`. A decisão vem do BACKEND (`GET /plataforma/acesso`, com a sessão
 * tenant) — nunca de e-mail, perfil ou conta de sistema — e só depois disso a sessão de plataforma (cookie
 * `tf_platform`) é aberta. Quem não é Administrador da Plataforma vê "Acesso negado" e nenhuma chamada a
 * `/plataforma/*` (API) é feita. A barreira real continua sendo a API (`require_platform_admin` a cada requisição).
 */
export function PlataformaGuard({ children }: { children: ReactNode }) {
  const { usuarioAtual, sessaoCarregando } = useAppData();
  const [estado, setEstado] = useState<Estado>("verificando");
  const usuarioId = usuarioAtual?.id;

  useEffect(() => {
    if (sessaoCarregando || !usuarioId) return;
    let cancelado = false;
    void (async () => {
      const ehAdministrador = await consultarAcessoPlataforma();
      if (!ehAdministrador) return cancelado ? undefined : setEstado("negado");
      try {
        await abrirSessaoPlataforma();
        if (!cancelado) setEstado("liberado");
      } catch {
        if (!cancelado) setEstado("negado");
      }
    })();
    return () => {
      cancelado = true;
    };
  }, [sessaoCarregando, usuarioId]);

  if (sessaoCarregando || !usuarioId || estado === "verificando") {
    return (
      <div className="flex items-center justify-center gap-2 p-10 text-sm text-fg-muted">
        <Loader2 className="h-4 w-4 animate-spin" />
        Verificando acesso…
      </div>
    );
  }
  if (estado === "negado") {
    return (
      <AcessoNegado
        titulo="Área restrita à Gestão da plataforma"
        descricao="Esta área é exclusiva de quem administra a plataforma. Se você precisa dela, fale com o responsável pelo TaskFlow."
      />
    );
  }
  return <>{children}</>;
}
