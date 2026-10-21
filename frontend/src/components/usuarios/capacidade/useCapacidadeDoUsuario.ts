"use client";

import { useEffect, useState } from "react";
import { getJornadaUsuario, listarAusenciasUsuario } from "@/lib/api-backend";
import { mensagemDeErroCapacidade } from "@/lib/usuario-capacidade";
import type { AusenciaUsuario, JornadaUsuario } from "@/types/usuario-capacidade";

type Estado = { carregando: boolean; erro: string | null; jornada: JornadaUsuario | null; ausencias: AusenciaUsuario[] };

/**
 * Ao abrir a seção: UM `GET jornada` e UM `GET ausências`, em paralelo (nunca uma chamada por dia). Depois de cada mutação o componente atualiza o estado com a RESPOSTA da API (`setJornada`,
 * `setAusencias`) — sem refetch e sem recarregar o aplicativo. `recarregar` refaz só estes dois GET.
 */
export function useCapacidadeDoUsuario(usuarioId: string) {
  const [estado, setEstado] = useState<Estado>({ carregando: true, erro: null, jornada: null, ausencias: [] });
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let cancelado = false;
    Promise.all([getJornadaUsuario(usuarioId), listarAusenciasUsuario(usuarioId)])
      .then(([jornada, ausencias]) => {
        if (!cancelado) setEstado({ carregando: false, erro: null, jornada, ausencias });
      })
      .catch((erro) => {
        if (!cancelado) setEstado((atual) => ({ ...atual, carregando: false, erro: mensagemDeErroCapacidade(erro, "Não foi possível carregar a jornada e as ausências.") }));
      });
    return () => {
      cancelado = true;
    };
  }, [usuarioId, tentativa]);

  return {
    ...estado,
    setJornada: (jornada: JornadaUsuario) => setEstado((atual) => ({ ...atual, jornada })),
    setAusencias: (ausencias: AusenciaUsuario[]) => setEstado((atual) => ({ ...atual, ausencias })),
    recarregar: () => {
      setEstado((atual) => ({ ...atual, carregando: true, erro: null }));
      setTentativa((n) => n + 1);
    },
  };
}
