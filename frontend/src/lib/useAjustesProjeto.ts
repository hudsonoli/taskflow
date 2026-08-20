"use client";

import { useEffect, useState } from "react";
import { getRelatorioAjustesPorProjeto, type RelatorioAjustesProjeto } from "@/lib/api-backend";

type Estado = {
  resultado: RelatorioAjustesProjeto | null;
  carregando: boolean;
  erro: string | null;
};

const ESTADO_VAZIO: Estado = { resultado: null, carregando: false, erro: null };

/**
 * Ajustes internos/Ajustes cliente/Refações de um Projeto (Fase 2F.4) — uma request por
 * Projeto selecionado, nunca por Demanda. Sem cache global (diferente de
 * `useDiretorioProjetos`): só dois componentes de Relatórios consomem isto, cada um com seu
 * próprio Projeto selecionado, não faz sentido compartilhar estado entre eles.
 *
 * O reset de `resultado`/`carregando` ao trocar de Projeto acontece **durante o render**
 * (comparando `projetoId` com o último consultado), não dentro do `useEffect` — setState
 * síncrono no corpo do efeito é o padrão que o lint do projeto rejeita
 * (`react-hooks/set-state-in-effect`); ajustar estado quando uma prop muda é o padrão que o
 * próprio React recomenda para este caso. Isso garante que o resultado do Projeto anterior
 * nunca aparece, nem por um frame, como se fosse do Projeto recém-selecionado.
 */
export function useAjustesProjeto(projetoId: string | null): Estado {
  const [projetoIdConsultado, setProjetoIdConsultado] = useState<string | null>(null);
  const [estado, setEstado] = useState<Estado>(ESTADO_VAZIO);

  if (projetoId !== projetoIdConsultado) {
    setProjetoIdConsultado(projetoId);
    setEstado(projetoId ? { resultado: null, carregando: true, erro: null } : ESTADO_VAZIO);
  }

  useEffect(() => {
    if (!projetoId) return;

    let cancelado = false;
    getRelatorioAjustesPorProjeto(projetoId)
      .then((resultado) => {
        if (!cancelado) setEstado({ resultado, carregando: false, erro: null });
      })
      .catch((error) => {
        if (!cancelado) {
          setEstado({
            resultado: null,
            carregando: false,
            erro: error instanceof Error ? error.message : "Não foi possível carregar os ajustes.",
          });
        }
      });

    return () => {
      cancelado = true;
    };
  }, [projetoId]);

  return estado;
}
