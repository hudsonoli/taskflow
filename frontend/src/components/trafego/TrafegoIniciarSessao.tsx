"use client";

import { useState } from "react";
import { PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { abrirSessaoTrabalho } from "@/lib/api";
import { useDiretorioUsuarios } from "@/lib/diretorioUsuarios";
import type { DemandaDiretorio } from "@/types/demanda";

/**
 * `usuarioId` enviado ao abrir sessão é o **UUID real** de `usuarios.id`, vindo do diretório
 * autenticado — não mais a lista mock (`user-1`…`user-5`) de `legacy-referencias-mock.ts`.
 *
 * Isso não é só limpeza: é o que faz `sessoes_trabalho.usuario_uuid` ter produtor. Sem um UUID
 * real chegando aqui, toda sessão nova nasceria com o vínculo de usuário não resolvível —
 * ver docstring de `app/models/sessao_trabalho.py` no backend.
 */
export function TrafegoIniciarSessao({
  onCreated,
  demandas,
}: {
  onCreated: () => void;
  demandas: DemandaDiretorio[];
}) {
  const { usuarios } = useDiretorioUsuarios();
  const [usuarioId, setUsuarioId] = useState("");
  const [demandaId, setDemandaId] = useState("");
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleIniciar() {
    setLoading(true);
    setErro(null);
    try {
      await abrirSessaoTrabalho({
        demandaId,
        usuarioId,
      });
      onCreated();
    } catch (error) {
      setErro(error instanceof Error ? error.message : "Erro ao iniciar sessão");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="grid flex-1 gap-3 sm:grid-cols-2">
          <Select
            label="Usuário"
            value={usuarioId}
            onChange={(event) => setUsuarioId(event.target.value)}
            options={[
              { value: "", label: "Selecionar…" },
              ...usuarios.map((usuario) => ({ value: usuario.id, label: usuario.nome })),
            ]}
          />
          <Select
            label="Demanda"
            value={demandaId}
            onChange={(event) => setDemandaId(event.target.value)}
            options={demandas.map((demanda) => ({
                value: demanda.id,
                label: `#${demanda.numeroOperacional} — ${demanda.nome}`,
              }))}
          />
        </div>
        <Button onClick={handleIniciar} disabled={loading || !demandaId || !usuarioId}>
          <PlayCircle className="h-4 w-4" />
          {loading ? "Iniciando…" : "Iniciar sessão de teste"}
        </Button>
      </div>
      {erro && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{erro}</p>}
    </div>
  );
}
