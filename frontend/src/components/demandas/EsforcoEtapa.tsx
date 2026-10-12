"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ajustarEsforcoEtapaReal } from "@/lib/api-backend";
import { formatEsforco, salvarEsforco } from "@/lib/esforco";
import type { Demanda, DemandaWorkflowEtapa } from "@/types/demanda";

export function EsforcoEtapa({ demandaId, etapa, somenteLeitura, onChange }: {
  demandaId: string; etapa: DemandaWorkflowEtapa; somenteLeitura: boolean; onChange: (demanda: Demanda) => void;
}) {
  const [editando, setEditando] = useState(false);
  const [texto, setTexto] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  async function salvar() {
    if (salvando) return;
    setSalvando(true);
    setErro(null);
    const resultado = await salvarEsforco(texto, (minutos) => ajustarEsforcoEtapaReal(demandaId, etapa.id, minutos));
    setSalvando(false);
    if (resultado.ok) { setEditando(false); onChange(resultado.valor); }
    else setErro(resultado.mensagem);
  }
  return (
    <div className="mt-2 text-xs text-fg-muted">
      <span>Esforço estimado: {formatEsforco(etapa.esforcoEstimadoMinutos)}</span>
      {!somenteLeitura && etapa.podeEditarEsforco && (editando ? (
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <Input label="Esforço estimado" aria-label={`Esforço estimado de ${etapa.nome}`} placeholder="Não estimado" value={texto}
            disabled={salvando} onChange={(e) => setTexto(e.target.value)} />
          <Button type="button" disabled={salvando} onClick={() => void salvar()}>{salvando ? "Salvando…" : "Salvar esforço"}</Button>
          <Button type="button" variant="secondary" disabled={salvando} onClick={() => { setEditando(false); setErro(null); }}>Cancelar</Button>
          <p className="w-full">Tempo de trabalho previsto. Ex.: 1h 30min. Deixe vazio para não estimado.</p>
          {erro && <p className="w-full text-red-600" role="alert">{erro}</p>}
        </div>
      ) : (
        <button type="button" className="ml-2 underline" onClick={() => {
          setTexto(etapa.esforcoEstimadoMinutos == null ? "" : formatEsforco(etapa.esforcoEstimadoMinutos));
          setErro(null); setEditando(true);
        }}>Ajustar esforço</button>
      ))}
    </div>
  );
}
