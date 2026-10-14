"use client";

import { useEffect, useState } from "react";
import { AvisoFlutuante } from "@/components/ui/AvisoFlutuante";
import { useAppData } from "@/lib/AppDataContext";
import { useSnapshotExpediente } from "@/lib/estadoExpediente";
import { eventoParaAvisar, gravarEventoApresentado, lerEventoApresentado, MENSAGEM_PAUSA_AUTOMATICA } from "@/lib/pausa-automatica";

/**
 * Aviso "Tarefas pausadas automaticamente." (Fase Expediente 3). Usa o MESMO store de `/expediente/estado` (um polling só) e o `AvisoFlutuante` já existente (~5 s,
 * Esc/× fecham, `role=status`, sem vermelho). Só aparece para evento NOVO (`eventoId` ainda não apresentado a esta pessoa), RECENTE (≤ 10 min, medido contra o `agora` do
 * SERVIDOR) e com quantidade > 0 — login horas depois não mostra aviso antigo. O localStorage (com try/catch e fallback em memória) só evita repetir; não é segurança.
 */
export function PausaAutomaticaAviso() {
  const { estado } = useSnapshotExpediente();
  const { usuarioAtual } = useAppData();
  const usuarioId = usuarioAtual?.id ?? null;
  const [exibindoId, setExibindoId] = useState<string | null>(null);
  const [dispensadoId, setDispensadoId] = useState<string | null>(null);
  const [chave, setChave] = useState(0);

  const candidato = estado && usuarioId ? eventoParaAvisar(estado.ultimaPausaAutomatica, estado.agora, lerEventoApresentado(usuarioId)) : null;
  if (candidato && candidato !== exibindoId && candidato !== dispensadoId) {
    // estado derivado durante a renderização (padrão do React): abre o aviso do evento novo sem efeito colateral
    setExibindoId(candidato);
    setChave((atual) => atual + 1);
  }

  useEffect(() => {
    if (exibindoId && usuarioId) gravarEventoApresentado(usuarioId, exibindoId); // marca como apresentado: o próximo poll não repete
  }, [exibindoId, usuarioId]);

  return (
    <AvisoFlutuante
      mensagem={MENSAGEM_PAUSA_AUTOMATICA}
      aberto={exibindoId !== null && exibindoId !== dispensadoId}
      chave={chave}
      onFechar={() => setDispensadoId(exibindoId)}
    />
  );
}
