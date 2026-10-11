"use client";

import { useEffect, useState } from "react";

/**
 * Origem pública atual (`https://taskflow.exemplo.com`). Vazia na renderização do servidor e na primeira do cliente (sem divergência de hidratação); preenchida logo
 * depois. Serve só para MOSTRAR/copiar endereços absolutos (endereço de login da empresa) — nunca para decidir empresa ou autorização.
 */
export function useOrigem(): string {
  const [origem, setOrigem] = useState("");
  useEffect(() => {
    const timeout = setTimeout(() => setOrigem(window.location.origin), 0);
    return () => clearTimeout(timeout);
  }, []);
  return origem;
}
