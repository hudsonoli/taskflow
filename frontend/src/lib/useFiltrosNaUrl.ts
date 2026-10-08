"use client";

import { useCallback, useMemo, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { decodificarFiltros, filtrosIguais, filtrosParaParametros } from "@/lib/filtros-avancados";
import type { DefinicaoFiltro, FiltroAtivo } from "@/types/filtros";

/**
 * Estado dos filtros (e de parâmetros simples como a busca) na URL: refresh, voltar do detalhe e link compartilhado
 * reconstroem a mesma tela. Um parâmetro por campo (`cliente=in:id1,id2`), sempre ids/códigos estáveis — nunca o rótulo.
 *
 * - `persistir=false` (ex.: aba dentro de um Projeto/Cliente): o estado vive só na memória e a URL não é tocada;
 * - o estado local reflete a mudança na hora; a URL é regravada com `history.replaceState` (sem recarregar nem empilhar
 *   histórico) e, se ela mudar por fora (voltar/avançar), o estado local a acompanha;
 * - o que vier da URL é revalidado contra as definições (`decodificarFiltros`): operador, quantidade e valores inválidos são
 *   ignorados, sem erro. Parâmetros que não são filtros (`q`, `periodo`…) são preservados e acessados por `param`.
 */
export function useFiltrosNaUrl(definicoes: readonly DefinicaoFiltro[], persistir: boolean) {
  const parametrosDaUrl = useSearchParams();
  const pathname = usePathname();
  const qsDaUrl = persistir ? parametrosDaUrl.toString() : "";
  const [qs, setQs] = useState(qsDaUrl);
  const [qsVisto, setQsVisto] = useState(qsDaUrl);

  // A URL mudou por fora (voltar/avançar, link): adota-a. Comparado no RENDER (padrão do projeto), não em efeito.
  if (persistir && qsDaUrl !== qsVisto) {
    setQsVisto(qsDaUrl);
    if (qsDaUrl !== qs) setQs(qsDaUrl);
  }

  const decodificados = useMemo(() => {
    const parametros = new URLSearchParams(qs);
    return decodificarFiltros((nome) => parametros.get(nome), definicoes);
  }, [qs, definicoes]);

  // Identidade ESTÁVEL: quando as definições mudam (opções que terminaram de carregar) mas os filtros são os mesmos, a lista
  // anterior é mantida — quem depende dela (consultas ao servidor) não refaz a busca à toa.
  const [filtros, setFiltros] = useState(decodificados);
  if (filtros !== decodificados && !filtrosIguais(filtros, decodificados)) setFiltros(decodificados);

  const gravar = useCallback(
    (proximo: URLSearchParams) => {
      const texto = proximo.toString();
      setQs(texto);
      if (persistir && typeof window !== "undefined") {
        window.history.replaceState(window.history.state, "", texto ? `${pathname}?${texto}` : pathname);
      }
    },
    [persistir, pathname],
  );

  const definirFiltros = useCallback(
    (novos: readonly FiltroAtivo[]) => {
      const proximo = new URLSearchParams(qs);
      for (const definicao of definicoes) proximo.delete(definicao.id);
      for (const [nome, valor] of filtrosParaParametros(novos)) proximo.set(nome, valor);
      gravar(proximo);
    },
    [qs, definicoes, gravar],
  );

  const param = useCallback((nome: string): string | null => new URLSearchParams(qs).get(nome), [qs]);

  const definirParam = useCallback(
    (nome: string, valor: string | null) => {
      const proximo = new URLSearchParams(qs);
      if (valor) proximo.set(nome, valor);
      else proximo.delete(nome);
      if (proximo.toString() !== qs) gravar(proximo);
    },
    [qs, gravar],
  );

  return { filtros, definirFiltros, param, definirParam };
}
