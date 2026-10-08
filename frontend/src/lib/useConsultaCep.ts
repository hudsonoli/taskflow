"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { camposCepParaFormulario, cepValido, consultarCep, somenteDigitos, type CamposDoEndereco } from "@/lib/brasilApi";

export type AvisoCep = { tipo: "buscando" | "sucesso" | "erro"; texto: string } | null;

const DEBOUNCE_MS = 400;

/**
 * Consulta automática de endereço ao completar o CEP (8 dígitos). Não consulta a cada tecla: só com o CEP COMPLETO, após uma
 * pausa curta, e uma única vez por CEP. Uma resposta atrasada de um CEP anterior é descartada. Em qualquer falha só mostra um
 * aviso discreto — o preenchimento manual nunca é bloqueado nem o formulário é limpo. `aplicar` recebe SÓ os campos que
 * vieram com valor (nunca número/complemento).
 */
export function useConsultaCep(ufsValidas: readonly string[]) {
  const [aviso, setAviso] = useState<AvisoCep>(null);
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sequencia = useRef(0);
  const ultimoConsultado = useRef<string | null>(null);

  const cancelar = useCallback(() => {
    if (temporizador.current) clearTimeout(temporizador.current);
    temporizador.current = null;
    sequencia.current += 1; // invalida qualquer consulta em andamento
  }, []);

  useEffect(() => cancelar, [cancelar]);

  /** Chame a cada alteração do campo CEP (já mascarado). */
  const agendar = useCallback(
    (cep: string, aplicar: (campos: CamposDoEndereco) => void) => {
      cancelar();
      if (!cepValido(cep)) {
        setAviso(null); // incompleto: nada de consultar nem de avisar
        ultimoConsultado.current = null;
        return;
      }
      const digitos = somenteDigitos(cep);
      if (digitos === ultimoConsultado.current) return; // mesmo CEP já consultado
      const minha = sequencia.current;
      temporizador.current = setTimeout(async () => {
        ultimoConsultado.current = digitos;
        setAviso({ tipo: "buscando", texto: "Buscando endereço…" });
        const resultado = await consultarCep(digitos);
        if (minha !== sequencia.current) return; // CEP mudou enquanto consultava
        if (!resultado.ok) {
          ultimoConsultado.current = null; // permite tentar de novo ao reeditar
          setAviso({ tipo: "erro", texto: resultado.mensagem });
          return;
        }
        aplicar(camposCepParaFormulario(resultado.dados, ufsValidas));
        setAviso({ tipo: "sucesso", texto: "Endereço encontrado. Informe o número e o complemento." });
      }, DEBOUNCE_MS);
    },
    [cancelar, ufsValidas],
  );

  const limparAviso = useCallback(() => setAviso(null), []);
  return { aviso, agendar, cancelar, limparAviso };
}
