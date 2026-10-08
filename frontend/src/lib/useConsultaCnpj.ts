"use client";

import { useCallback, useState } from "react";
import { camposParaFormulario, consultarCnpj, type CamposDoFormulario } from "@/lib/brasilApi";

export type AvisoConsulta = { tipo: "sucesso" | "erro"; texto: string } | null;

/**
 * Estado compartilhado da consulta de CNPJ (Clientes e Fornecedores). `buscar` consulta e entrega ao formulário SÓ os
 * campos que vieram preenchidos (`camposParaFormulario`); em qualquer falha devolve um aviso claro e não toca o
 * formulário — o cadastro manual nunca é bloqueado nem limpo.
 */
export function useConsultaCnpj(ufsValidas: readonly string[]) {
  const [buscando, setBuscando] = useState(false);
  const [aviso, setAviso] = useState<AvisoConsulta>(null);

  const buscar = useCallback(
    async (documento: string, aplicar: (campos: CamposDoFormulario) => void) => {
      setBuscando(true);
      setAviso(null);
      const resultado = await consultarCnpj(documento);
      setBuscando(false);
      if (!resultado.ok) {
        setAviso({ tipo: "erro", texto: resultado.mensagem });
        return;
      }
      aplicar(camposParaFormulario(resultado.dados, ufsValidas));
      setAviso({ tipo: "sucesso", texto: "Dados encontrados e preenchidos. Confira antes de salvar." });
    },
    [ufsValidas],
  );

  const limparAviso = useCallback(() => setAviso(null), []);
  return { buscando, aviso, buscar, limparAviso };
}
