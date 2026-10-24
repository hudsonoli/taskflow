"use client";

import { useCallback, useSyncExternalStore } from "react";

// Preferências puramente VISUAIS do navegador (nada vai ao servidor). `localStorage` com try/catch e fallback em memória (navegação privada/bloqueio de armazenamento não pode derrubar a tela);
// `useSyncExternalStore` mantém a hidratação estável (o servidor renderiza o padrão) e sincroniza abas e componentes.

const memoria = new Map<string, boolean>();
const ouvintes = new Set<() => void>();

function ler(chave: string, padrao: boolean): boolean {
  try {
    const valor = window.localStorage.getItem(chave);
    if (valor === "1") return true;
    if (valor === "0") return false;
    return memoria.get(chave) ?? padrao;
  } catch {
    return memoria.get(chave) ?? padrao;
  }
}

function gravar(chave: string, valor: boolean): void {
  memoria.set(chave, valor);
  try {
    window.localStorage.setItem(chave, valor ? "1" : "0");
  } catch {
    // sem armazenamento: a preferência vale até recarregar
  }
  ouvintes.forEach((ouvinte) => ouvinte());
}

function assinar(ouvinte: () => void): () => void {
  ouvintes.add(ouvinte);
  window.addEventListener("storage", ouvinte);
  return () => {
    ouvintes.delete(ouvinte);
    window.removeEventListener("storage", ouvinte);
  };
}

export function usePreferenciaBooleana(chave: string, padrao: boolean): [boolean, (valor: boolean) => void] {
  const valor = useSyncExternalStore(
    assinar,
    () => ler(chave, padrao),
    () => padrao,
  );
  const definir = useCallback((proximo: boolean) => gravar(chave, proximo), [chave]);
  return [valor, definir];
}
