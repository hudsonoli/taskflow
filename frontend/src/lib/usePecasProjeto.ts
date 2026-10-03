"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getRelatorioPecasProjeto } from "@/lib/api-backend";
import type { RelatorioPeca } from "@/types/relatorios";

// D4A — tamanho da página de "Análise de peças" (+ "Carregar mais").
const TAMANHO_PAGINA = 50;

type Estado = {
  /** `null` = primeira página ainda em voo (ou falhou — ver `erro`). */
  linhas: RelatorioPeca[] | null;
  total: number;
  erro: string | null;
};

const ESTADO_VAZIO: Estado = { linhas: null, total: 0, erro: null };

export type PecasProjeto = {
  linhas: RelatorioPeca[];
  total: number;
  carregando: boolean;
  erro: string | null;
  carregandoMais: boolean;
  erroMais: string | null;
  carregarMais: () => void;
};

/**
 * D4A — "Análise de peças" paginada no servidor (`limit`/`offset`, com `total`), uma consulta
 * por Projeto. Trocar de Projeto volta à primeira página; resposta de um Projeto anterior —
 * inclusive um "carregar mais" em voo — é descartada (`cancelado` no efeito e `projetoVigenteRef`
 * no "carregar mais"). Sem Projeto resolvido não há consulta: lista vazia, sem "carregando".
 *
 * A paginação é por offset: se uma Demanda for criada/arquivada entre duas páginas, a seguinte
 * pode repetir (deduplicado aqui) ou pular uma linha até o próximo carregamento do Projeto.
 */
export function usePecasProjeto(projetoId: string | null): PecasProjeto {
  const [projetoIdConsultado, setProjetoIdConsultado] = useState<string | null>(null);
  const [estado, setEstado] = useState<Estado>(ESTADO_VAZIO);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [erroMais, setErroMais] = useState<string | null>(null);
  const projetoVigenteRef = useRef<string | null>(null);

  if (projetoId !== projetoIdConsultado) {
    setProjetoIdConsultado(projetoId);
    setEstado(ESTADO_VAZIO);
    setCarregandoMais(false);
    setErroMais(null);
  }

  useEffect(() => {
    projetoVigenteRef.current = projetoId;
    if (!projetoId) return;

    let cancelado = false;
    getRelatorioPecasProjeto(projetoId, TAMANHO_PAGINA, 0)
      .then((pagina) => {
        if (!cancelado) setEstado({ linhas: pagina.items, total: pagina.total, erro: null });
      })
      .catch((error) => {
        if (!cancelado) {
          setEstado({
            linhas: null,
            total: 0,
            erro: error instanceof Error ? error.message : "Não foi possível carregar as peças do projeto.",
          });
        }
      });

    return () => {
      cancelado = true;
    };
  }, [projetoId]);

  const carregarMais = useCallback(() => {
    if (!projetoId || !estado.linhas) return;
    const projetoDoClique = projetoId;
    setCarregandoMais(true);
    setErroMais(null);
    getRelatorioPecasProjeto(projetoId, TAMANHO_PAGINA, estado.linhas.length)
      .then((pagina) => {
        if (projetoVigenteRef.current !== projetoDoClique) return;
        setEstado((atual) => {
          if (!atual.linhas) return atual;
          const jaNaTela = new Set(atual.linhas.map((linha) => linha.demandaId));
          const novas = pagina.items.filter((item) => !jaNaTela.has(item.demandaId));
          return { linhas: [...atual.linhas, ...novas], total: pagina.total, erro: null };
        });
      })
      .catch((error) => {
        if (projetoVigenteRef.current !== projetoDoClique) return;
        setErroMais(error instanceof Error ? error.message : "Não foi possível carregar mais peças.");
      })
      .finally(() => {
        if (projetoVigenteRef.current === projetoDoClique) setCarregandoMais(false);
      });
  }, [projetoId, estado.linhas]);

  return {
    linhas: estado.linhas ?? [],
    total: estado.total,
    carregando: projetoId !== null && estado.linhas === null && estado.erro === null,
    erro: estado.erro,
    carregandoMais,
    erroMais,
    carregarMais,
  };
}
