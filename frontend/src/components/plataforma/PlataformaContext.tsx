"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * "Empresa em foco": a empresa que a Administração da Plataforma está consultando/editando agora. É só um rótulo de
 * contexto para a pessoa não confundir de qual empresa está mexendo — NÃO muda a sessão, o token nem a empresa do
 * usuário (a Plataforma nunca "entra" no tenant; ver docs/administracao-plataforma.md).
 */
export type EmpresaEmFoco = { id: string; nome: string; slug: string };

type Valor = { empresaEmFoco: EmpresaEmFoco | null; definirEmpresaEmFoco: (empresa: EmpresaEmFoco | null) => void };

const Contexto = createContext<Valor | null>(null);

export function PlataformaProvider({ children }: { children: ReactNode }) {
  const [empresaEmFoco, definirEmpresaEmFoco] = useState<EmpresaEmFoco | null>(null);
  const valor = useMemo(() => ({ empresaEmFoco, definirEmpresaEmFoco }), [empresaEmFoco]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function usePlataforma(): Valor {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("usePlataforma precisa estar dentro de <PlataformaProvider>");
  return valor;
}
