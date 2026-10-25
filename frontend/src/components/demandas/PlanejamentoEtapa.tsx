"use client";

import { useState } from "react";
import { CalendarRange } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { DateField } from "@/components/ui/DateField";
import { ajustarPlanejamentoEtapaReal } from "@/lib/api-backend";
import {
  TEXTO_AJUDA_PLANEJAMENTO,
  TEXTO_PLANEJAMENTO_INCOMPLETO,
  estadoDoFormulario,
  planejamentoDaEtapa,
  resumoDoPlanejamento,
  salvarPlanejamento,
} from "@/lib/planejamento-etapa";
import type { Demanda, DemandaWorkflowEtapa } from "@/types/demanda";

/**
 * Janela PLANEJADA da etapa (11B.2B-A): "Planejado de … até …". É planejamento da equipe, NÃO o prazo — por isso tem ícone, rótulo e ajuda próprios e nunca
 * aparece junto do prazo da tarefa. Sem planejamento não há nenhuma indicação (só o atalho "Planejar" para quem pode editar). A autoridade vem do servidor
 * (`podeEditarPlanejamento`); `sem_dia_util` e `janela_vencida` pertencem à Fase B (Carga) e não existem aqui.
 */
export function PlanejamentoEtapa({ demandaId, etapa, somenteLeitura, onChange }: {
  demandaId: string; etapa: DemandaWorkflowEtapa; somenteLeitura: boolean; onChange: (demanda: Demanda) => void;
}) {
  const planejamento = planejamentoDaEtapa(etapa);
  const resumo = resumoDoPlanejamento(planejamento);
  const podeEditar = !somenteLeitura && etapa.podeEditarPlanejamento === true;
  const [editando, setEditando] = useState(false);
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const atual = { inicio: planejamento.planejadoInicio ?? "", fim: planejamento.planejadoFim ?? "" };
  const formulario = estadoDoFormulario(atual, { inicio, fim });
  const erroLocal = editando ? formulario.erro : null;

  async function salvar() {
    if (salvando) return;
    setSalvando(true);
    setErro(null);
    const resultado = await salvarPlanejamento(atual, { inicio, fim }, (corpo) => ajustarPlanejamentoEtapaReal(demandaId, etapa.id, corpo));
    setSalvando(false);
    if (resultado.ok) { setEditando(false); onChange(resultado.valor); }
    else setErro(resultado.mensagem);
  }

  if (!resumo && !podeEditar) return null;
  return (
    <div className="mt-1 text-xs text-fg-muted" data-planejamento={planejamento.estado}>
      {resumo && (
        <span className="inline-flex flex-wrap items-center gap-1.5">
          <CalendarRange className="h-3.5 w-3.5" aria-hidden="true" />
          <span>{resumo.texto}</span>
          {resumo.incompleto && <span className="text-amber-700 dark:text-amber-400">· {TEXTO_PLANEJAMENTO_INCOMPLETO}</span>}
        </span>
      )}
      {podeEditar && (editando ? (
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <DateField label="Planejado de" rotuloAcessivel={`Planejado de, etapa ${etapa.nome}`} value={inicio} disabled={salvando} className="w-44"
            onChange={setInicio} />
          <DateField label="Planejado até" rotuloAcessivel={`Planejado até, etapa ${etapa.nome}`} value={fim} disabled={salvando} className="w-44"
            onChange={setFim} />
          <Button type="button" disabled={salvando || !formulario.podeSalvar} onClick={() => void salvar()}>{salvando ? "Salvando…" : "Salvar planejamento"}</Button>
          <Button type="button" variant="secondary" disabled={salvando} onClick={() => { setEditando(false); setErro(null); }}>Cancelar</Button>
          <p className="w-full">{TEXTO_AJUDA_PLANEJAMENTO} Deixe os dois vazios para limpar.</p>
          {(erroLocal && (inicio || fim)) && <p className="w-full text-amber-700 dark:text-amber-400" role="alert">{erroLocal}</p>}
          {erro && <p className="w-full text-red-600" role="alert">{erro}</p>}
        </div>
      ) : (
        <button type="button" className={resumo ? "ml-2 underline" : "underline"} onClick={() => {
          setInicio(planejamento.planejadoInicio ?? "");
          setFim(planejamento.planejadoFim ?? "");
          setErro(null); setEditando(true);
        }}>{resumo ? "Ajustar planejamento" : "Planejar etapa"}</button>
      ))}
    </div>
  );
}
