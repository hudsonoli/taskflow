"use client";

import { Button } from "@/components/ui/Button";
import { TEXTO_DIAS_ESPECIAIS, TEXTO_IMPACTO_CARGA, TEXTO_SOMENTE_LEITURA } from "@/lib/usuario-capacidade";
import { UsuarioAusenciasLista } from "./UsuarioAusenciasLista";
import { UsuarioJornadaEditor } from "./UsuarioJornadaEditor";
import { useCapacidadeDoUsuario } from "./useCapacidadeDoUsuario";

function Bloco({ className }: { className: string }) {
  return <div aria-hidden className={`animate-pulse rounded-lg bg-zinc-100 dark:bg-zinc-800 ${className}`} />;
}

/**
 * Seção "Jornada e ausências" do Usuário (Configurações → Usuários → editar → aba). Dois blocos: A) Jornada de trabalho e B) Ausências. Ao abrir faz 2 GET em paralelo (jornada e ausências).
 * `somenteLeitura` espelha a autoridade que a tela de Usuários já usa (`podeEditarUsuario`); a barreira real é o backend (403 tratado com a mensagem da API). Skeleton e erro são só da seção:
 * o restante do modal não é bloqueado.
 */
export function UsuarioCapacidadeSection({ usuarioId, somenteLeitura }: { usuarioId: string; somenteLeitura: boolean }) {
  const { carregando, erro, jornada, ausencias, setJornada, setAusencias, recarregar } = useCapacidadeDoUsuario(usuarioId);

  if (carregando && jornada === null) {
    return (
      <div role="status" aria-label="Carregando jornada e ausências" className="flex flex-col gap-3">
        <Bloco className="h-40 w-full" />
        <Bloco className="h-24 w-full" />
      </div>
    );
  }

  if (jornada === null) {
    return (
      <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-400">
        <span>{erro ?? "Não foi possível carregar a jornada e as ausências."}</span>
        <Button type="button" variant="secondary" onClick={recarregar}>
          Tentar novamente
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {somenteLeitura && (
        <p role="note" className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-xs text-fg-muted">
          {TEXTO_SOMENTE_LEITURA}
        </p>
      )}
      <UsuarioJornadaEditor usuarioId={usuarioId} jornada={jornada} somenteLeitura={somenteLeitura} onChange={setJornada} />
      <UsuarioAusenciasLista usuarioId={usuarioId} ausencias={ausencias} somenteLeitura={somenteLeitura} onChange={setAusencias} />
      <div className="flex flex-col gap-0.5 text-xs text-fg-subtle">
        <p>{TEXTO_IMPACTO_CARGA}</p>
        <p>{TEXTO_DIAS_ESPECIAIS}</p>
      </div>
    </div>
  );
}
