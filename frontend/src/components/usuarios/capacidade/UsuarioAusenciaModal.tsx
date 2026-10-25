"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { DateField } from "@/components/ui/DateField";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { atualizarAusenciaUsuario, criarAusenciaUsuario } from "@/lib/api-backend";
import {
  AUSENCIA_VAZIA,
  MAX_OBSERVACAO,
  OPCOES_TIPO_AUSENCIA,
  TEXTO_AUSENCIA_DIA_INTEIRO,
  TEXTO_SOBREPOSICAO,
  draftDaAusencia,
  mensagemDeErroCapacidade,
  patchDaAusencia,
  sobrepoeOutraAusencia,
  validarAusencia,
} from "@/lib/usuario-capacidade";
import type { AusenciaDraft, AusenciaUsuario, TipoAusencia } from "@/types/usuario-capacidade";

/** Nova ausência / edição: tipo, data inicial, data final (um dia = início igual ao fim) e observação opcional. Sempre dias inteiros — sem hora e sem "dia inteiro" para ligar. */
export function UsuarioAusenciaModal({
  usuarioId,
  ausencia,
  existentes,
  onClose,
  onSaved,
}: {
  usuarioId: string;
  ausencia?: AusenciaUsuario;
  existentes: readonly AusenciaUsuario[];
  onClose: () => void;
  onSaved: (ausencia: AusenciaUsuario) => void;
}) {
  const [draft, setDraft] = useState<AusenciaDraft>(() => (ausencia ? draftDaAusencia(ausencia) : AUSENCIA_VAZIA));
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentou, setTentou] = useState(false);

  const erros = validarAusencia(draft);
  const invalido = Object.keys(erros).length > 0;
  const sobrepoe = sobrepoeOutraAusencia(draft, existentes, ausencia?.id);
  const editando = ausencia !== undefined;

  function atualizar(patch: Partial<AusenciaDraft>) {
    setDraft((atual) => ({ ...atual, ...patch }));
  }

  async function salvar() {
    setTentou(true);
    if (invalido || salvando) return;
    setSalvando(true);
    setErro(null);
    try {
      if (ausencia) {
        const patch = patchDaAusencia(ausencia, draft);
        if (patch === null) {
          onClose(); // nada mudou: nenhuma chamada
          return;
        }
        onSaved(await atualizarAusenciaUsuario(usuarioId, ausencia.id, patch));
      } else {
        onSaved(await criarAusenciaUsuario(usuarioId, draft));
      }
    } catch (e) {
      setErro(mensagemDeErroCapacidade(e, "Não foi possível salvar a ausência."));
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Modal open onClose={salvando ? () => {} : onClose} maxWidthClassName="max-w-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-fg">{editando ? "Editar ausência" : "Adicionar ausência"}</h2>
          <p className="mt-1 text-xs text-fg-muted">{TEXTO_AUSENCIA_DIA_INTEIRO}</p>
        </div>
        <button type="button" onClick={onClose} disabled={salvando} aria-label="Fechar" className="rounded-full p-2 text-fg-subtle transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-4 flex flex-col gap-3">
        <Select label="Tipo" value={draft.tipo} onChange={(e) => atualizar({ tipo: e.target.value as TipoAusencia })} options={OPCOES_TIPO_AUSENCIA.map((o) => ({ value: o.value, label: o.label }))} />
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <DateField
              label="Data inicial"
              anulavel={false}
              value={draft.inicio}
              onChange={(inicio) => {
                // conveniência: sem fim (ou fim antes do novo início) o fim acompanha o início — um dia só até o usuário mudar
                atualizar({ inicio, ...(draft.fim === "" || draft.fim < inicio ? { fim: inicio } : {}) });
              }}
            />
            {tentou && erros.inicio && (
              <p role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
                {erros.inicio}
              </p>
            )}
          </div>
          <div>
            <DateField label="Data final" anulavel={false} value={draft.fim} min={draft.inicio || undefined} onChange={(fim) => atualizar({ fim })} />
            {(tentou || draft.fim !== "") && erros.fim && (
              <p role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
                {erros.fim}
              </p>
            )}
          </div>
        </div>
        <div>
          <Textarea label="Observação (opcional)" rows={2} maxLength={MAX_OBSERVACAO} value={draft.observacao} onChange={(e) => atualizar({ observacao: e.target.value })} />
          {erros.observacao && (
            <p role="alert" className="mt-1 text-xs text-red-600 dark:text-red-400">
              {erros.observacao}
            </p>
          )}
        </div>
        {sobrepoe && (
          <p role="note" className="text-xs text-amber-700 dark:text-amber-400">
            {TEXTO_SOBREPOSICAO}
          </p>
        )}
        {erro && (
          <p role="alert" className="text-xs text-red-600 dark:text-red-400">
            {erro}
          </p>
        )}
      </div>

      <div className="mt-5 flex justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800">
        <Button type="button" variant="secondary" onClick={onClose} disabled={salvando}>
          Cancelar
        </Button>
        <Button type="button" onClick={salvar} disabled={salvando || (tentou && invalido)}>
          {salvando ? "Salvando…" : editando ? "Salvar ausência" : "Adicionar ausência"}
        </Button>
      </div>
    </Modal>
  );
}
