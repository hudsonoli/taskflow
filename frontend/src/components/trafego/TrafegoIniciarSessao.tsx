"use client";

import { rotuloDemanda } from "@/lib/referencias";
import { useState } from "react";
import { PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { MemberSelector } from "@/components/ui/MemberSelector";
import { Select } from "@/components/ui/Select";
import { abrirSessaoTrabalho } from "@/lib/api";
import { opcoesDeDemanda, podeIniciarSessao } from "@/lib/trafego-ui";
import { useUsuariosSelector } from "@/lib/useResponsaveisSelector";
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
  const { buscarOpcoes } = useUsuariosSelector({ todosStatus: true });
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
    <div className="flex flex-[3_1_40rem] flex-wrap items-end gap-3">
      {/* Busca no servidor (sem o corte de 200); qualquer status, como a lista de antes. O `usuarioId`
          enviado continua sendo o UUID real do usuário. */}
      <div className="min-w-[12rem] flex-1">
        <MemberSelector
          label="Usuário"
          multiple={false}
          values={usuarioId ? [usuarioId] : []}
          onChange={(values) => setUsuarioId(values[0] ?? "")}
          placeholder="Selecionar…"
          buscarOpcoes={buscarOpcoes}
          emptyLabel="Nenhum usuário encontrado"
        />
      </div>
      <div className="min-w-[14rem] flex-[1.4]">
        <Select
          label="Demanda"
          value={demandaId}
          onChange={(event) => setDemandaId(event.target.value)}
          options={opcoesDeDemanda(demandas, (demanda) => ({ value: demanda.id, label: `${rotuloDemanda(demanda)} — ${demanda.nome}` }))}
        />
      </div>
      <Button onClick={handleIniciar} disabled={!podeIniciarSessao({ enviando: loading, demandaId, usuarioId })} className="shrink-0">
        <PlayCircle className="h-4 w-4" />
        {loading ? "Iniciando…" : "Iniciar sessão de teste"}
      </Button>
      {erro && <p className="basis-full text-sm text-red-600 dark:text-red-400">{erro}</p>}
    </div>
  );
}
