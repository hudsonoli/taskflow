"use client";

import { useCallback, useSyncExternalStore } from "react";
import { ATRIBUTO_ESTILO_VISUAL, CHAVE_ESTILO_VISUAL, ESTILO_VISUAL_PADRAO, normalizarEstiloVisual, type EstiloVisual } from "./estilo-visual";

// Estilo visual (default | glass) como estado do navegador. A fonte da verdade EM TEMPO DE EXECUÇÃO é o atributo `data-visual-style` do <html> (gravado antes do primeiro paint por
// `SCRIPT_ESTILO_VISUAL` e mantido aqui); o localStorage só persiste entre visitas. `useSyncExternalStore` com snapshot de servidor = padrão mantém a hidratação estável: o controle (no menu do
// perfil) reflete o estilo real logo após hidratar, e o CSS — que lê o atributo — nunca muda de aparência por causa disso.

const ouvintes = new Set<() => void>();

function lerAtributo(): EstiloVisual {
  return normalizarEstiloVisual(document.documentElement.getAttribute(ATRIBUTO_ESTILO_VISUAL));
}

function aplicar(estilo: EstiloVisual): void {
  document.documentElement.setAttribute(ATRIBUTO_ESTILO_VISUAL, estilo);
  ouvintes.forEach((ouvinte) => ouvinte());
}

function assinar(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte);
  // outra aba mudou o estilo: acompanha (o evento `storage` só dispara nas OUTRAS abas)
  const aoMudarEmOutraAba = (evento: StorageEvent) => {
    if (evento.key !== CHAVE_ESTILO_VISUAL) return;
    aplicar(normalizarEstiloVisual(evento.newValue));
  };
  window.addEventListener("storage", aoMudarEmOutraAba);
  return () => {
    ouvintes.delete(ouvinte);
    window.removeEventListener("storage", aoMudarEmOutraAba);
  };
}

export function useEstiloVisual(): [EstiloVisual, (estilo: EstiloVisual) => void] {
  const estilo = useSyncExternalStore(assinar, lerAtributo, () => ESTILO_VISUAL_PADRAO);
  const definir = useCallback((proximo: EstiloVisual) => {
    const valido = normalizarEstiloVisual(proximo);
    try {
      window.localStorage.setItem(CHAVE_ESTILO_VISUAL, valido);
    } catch {
      // sem armazenamento: o estilo vale até recarregar (o atributo continua sendo a verdade da sessão)
    }
    aplicar(valido);
  }, []);
  return [estilo, definir];
}
