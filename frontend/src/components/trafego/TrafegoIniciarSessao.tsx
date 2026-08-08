"use client";

import { useState } from "react";
import { PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { abrirSessaoTrabalho } from "@/lib/api";
import { EMPRESA_TRAFEGO_PADRAO_ID, trafegoDemandasDisponiveis, trafegoUsuariosDisponiveis } from "@/lib/trafego";

export function TrafegoIniciarSessao({ onCreated }: { onCreated: () => void }) {
  const [usuarioId, setUsuarioId] = useState(trafegoUsuariosDisponiveis[0].id);
  const [demandaId, setDemandaId] = useState(trafegoDemandasDisponiveis[0].id);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function handleIniciar() {
    setLoading(true);
    setErro(null);
    try {
      await abrirSessaoTrabalho({
        empresaId: EMPRESA_TRAFEGO_PADRAO_ID,
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
            options={trafegoUsuariosDisponiveis.map((usuario) => ({ value: usuario.id, label: usuario.nome }))}
          />
          <Select
            label="Demanda"
            value={demandaId}
            onChange={(event) => setDemandaId(event.target.value)}
            options={trafegoDemandasDisponiveis.map((demanda) => ({ value: demanda.id, label: demanda.nome }))}
          />
        </div>
        <Button onClick={handleIniciar} disabled={loading}>
          <PlayCircle className="h-4 w-4" />
          {loading ? "Iniciando…" : "Iniciar sessão de teste"}
        </Button>
      </div>
      {erro && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{erro}</p>}
    </div>
  );
}
