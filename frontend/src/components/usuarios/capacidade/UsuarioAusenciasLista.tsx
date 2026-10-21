"use client";

import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import clsx from "clsx";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { removerAusenciaUsuario } from "@/lib/api-backend";
import {
  TEXTO_CONFIRMAR_REMOVER_AUSENCIA,
  TEXTO_SEM_AUSENCIAS,
  formatarPeriodoAusencia,
  hojeLocalIso,
  mensagemDeErroCapacidade,
  rotuloDuracaoAusencia,
  rotuloDoTipoAusencia,
  separarAusencias,
} from "@/lib/usuario-capacidade";
import type { AusenciaUsuario } from "@/types/usuario-capacidade";
import { ConfirmacaoCurta } from "./ConfirmacaoCurta";
import { UsuarioAusenciaModal } from "./UsuarioAusenciaModal";

const TOM_TIPO: Record<string, BadgeTone> = { ferias: "blue", afastamento: "amber", folga: "neutral", outro: "neutral" };

function Linha({ ausencia, passada, somenteLeitura, onEditar, onRemover }: { ausencia: AusenciaUsuario; passada: boolean; somenteLeitura: boolean; onEditar: () => void; onRemover: () => void }) {
  const periodo = formatarPeriodoAusencia(ausencia.inicio, ausencia.fim);
  return (
    <li className={clsx("flex items-start gap-3 border-b border-line py-2.5 last:border-b-0", passada && "opacity-60")}>
      <div className="w-24 shrink-0 pt-0.5">
        <Badge tone={TOM_TIPO[ausencia.tipo] ?? "neutral"}>{rotuloDoTipoAusencia(ausencia.tipo)}</Badge>
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-fg">
          {periodo} <span className="text-xs text-fg-subtle">· {rotuloDuracaoAusencia(ausencia.inicio, ausencia.fim)}</span>
        </p>
        {ausencia.observacao && (
          <p className="truncate text-xs text-fg-muted" title={ausencia.observacao}>
            {ausencia.observacao}
          </p>
        )}
      </div>
      {!somenteLeitura && (
        <div className="flex shrink-0 gap-1">
          <button type="button" onClick={onEditar} aria-label={`Editar ausência ${periodo}`} title="Editar" className="rounded-lg p-2 text-fg-subtle transition hover:bg-surface-hover hover:text-fg">
            <Pencil className="h-3.5 w-3.5" aria-hidden />
          </button>
          <button type="button" onClick={onRemover} aria-label={`Remover ausência ${periodo}`} title="Remover" className="rounded-lg p-2 text-fg-subtle transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-500/10 dark:hover:text-red-400">
            <Trash2 className="h-3.5 w-3.5" aria-hidden />
          </button>
        </div>
      )}
    </li>
  );
}

/**
 * Bloco B — Ausências: lista compacta (tipo, período, observação). Atuais e futuras primeiro; passadas depois, esmaecidas — nada é escondido. Criar/editar num modal; remover com confirmação.
 * Cada mutação atualiza a lista com a resposta da API. Sem status persistido: o "passada" é só visual, calculado localmente.
 */
export function UsuarioAusenciasLista({ usuarioId, ausencias, somenteLeitura, onChange }: { usuarioId: string; ausencias: AusenciaUsuario[]; somenteLeitura: boolean; onChange: (ausencias: AusenciaUsuario[]) => void }) {
  const [modal, setModal] = useState<{ ausencia?: AusenciaUsuario } | null>(null);
  const [remover, setRemover] = useState<AusenciaUsuario | null>(null);
  const [removendo, setRemovendo] = useState(false);
  const [erroRemover, setErroRemover] = useState<string | null>(null);
  const { proximas, passadas } = separarAusencias(ausencias, hojeLocalIso());

  function salva(ausencia: AusenciaUsuario) {
    const existe = ausencias.some((a) => a.id === ausencia.id);
    onChange(existe ? ausencias.map((a) => (a.id === ausencia.id ? ausencia : a)) : [...ausencias, ausencia]);
    setModal(null);
  }

  async function confirmarRemocao() {
    if (!remover) return;
    setRemovendo(true);
    setErroRemover(null);
    try {
      await removerAusenciaUsuario(usuarioId, remover.id);
      onChange(ausencias.filter((a) => a.id !== remover.id));
      setRemover(null);
    } catch (e) {
      setErroRemover(mensagemDeErroCapacidade(e, "Não foi possível remover a ausência."));
    } finally {
      setRemovendo(false);
    }
  }

  return (
    <section aria-label="Ausências" className="rounded-2xl border border-line bg-surface p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-fg">Ausências</h3>
        {!somenteLeitura && (
          <Button type="button" variant="secondary" onClick={() => setModal({})}>
            <Plus className="h-3.5 w-3.5" />
            Adicionar ausência
          </Button>
        )}
      </div>

      {ausencias.length === 0 ? (
        <p className="mt-3 rounded-xl border border-dashed border-line bg-surface-2 px-3 py-4 text-center text-xs text-fg-subtle">{TEXTO_SEM_AUSENCIAS}</p>
      ) : (
        <>
          {proximas.length > 0 && (
            <ul className="mt-2" aria-label="Ausências atuais e futuras">
              {proximas.map((a) => (
                <Linha key={a.id} ausencia={a} passada={false} somenteLeitura={somenteLeitura} onEditar={() => setModal({ ausencia: a })} onRemover={() => setRemover(a)} />
              ))}
            </ul>
          )}
          {passadas.length > 0 && (
            <>
              {proximas.length > 0 && <p className="mt-3 text-[11px] font-semibold uppercase tracking-wide text-fg-subtle">Passadas</p>}
              <ul className="mt-1" aria-label="Ausências passadas">
                {passadas.map((a) => (
                  <Linha key={a.id} ausencia={a} passada somenteLeitura={somenteLeitura} onEditar={() => setModal({ ausencia: a })} onRemover={() => setRemover(a)} />
                ))}
              </ul>
            </>
          )}
        </>
      )}

      {modal && <UsuarioAusenciaModal usuarioId={usuarioId} ausencia={modal.ausencia} existentes={ausencias} onClose={() => setModal(null)} onSaved={salva} />}
      {remover && (
        <ConfirmacaoCurta
          titulo="Remover ausência"
          texto={TEXTO_CONFIRMAR_REMOVER_AUSENCIA}
          confirmar="Remover"
          ocupado={removendo}
          erro={erroRemover}
          onConfirm={confirmarRemocao}
          onClose={() => setRemover(null)}
        />
      )}
    </section>
  );
}
