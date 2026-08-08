"use client";

import { useState } from "react";
import { Layers3, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Switch } from "@/components/ui/Switch";
import { Tabs } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";
import { categoriasPecaDisponiveis, formatHoursMinutes, formatValorInput, parseHoursInput, parseValorInput } from "@/lib/pecas-mock";
import { useAppData } from "@/lib/AppDataContext";
import { podeVerDadosFinanceiros } from "@/types/usuario";
import type { Peca, PecaFormDraft } from "@/types/peca";

type FormState = {
  nome: string;
  categoria: string;
  tempoEstimado: string;
  tempoMedio: string;
  valor: string;
  sindicatoAtivo: boolean;
  valorSindicatoCriacao: string;
  valorSindicatoAdaptacao: string;
  valorSindicatoFinalizacao: string;
  briefingPadrao: string;
  ativa: boolean;
};

const tabs = [
  { id: "dados", label: "Dados" },
  { id: "valores", label: "Valores" },
  { id: "briefing", label: "Briefing" },
];

function createInitialForm(peca?: Peca): FormState {
  return {
    nome: peca?.nome ?? "",
    categoria: peca?.categoria ?? "",
    tempoEstimado: formatHoursMinutes(peca?.tempoEstimadoMinutos ?? null),
    tempoMedio: formatHoursMinutes(peca?.tempoMedioMinutos ?? null),
    valor: formatValorInput(peca?.valorTabelaCentavos ?? null),
    sindicatoAtivo: peca?.sindicatoAtivo ?? false,
    valorSindicatoCriacao: formatValorInput(peca?.valorSindicatoCriacaoCentavos ?? null),
    valorSindicatoAdaptacao: formatValorInput(peca?.valorSindicatoAdaptacaoCentavos ?? null),
    valorSindicatoFinalizacao: formatValorInput(peca?.valorSindicatoFinalizacaoCentavos ?? null),
    briefingPadrao: peca?.briefingPadrao ?? "",
    ativa: peca?.ativa ?? true,
  };
}

export function PecaFormModal({
  open,
  peca,
  onClose,
  onSave,
}: {
  open: boolean;
  peca?: Peca;
  onClose: () => void;
  onSave: (draft: PecaFormDraft, pecaId?: string) => void;
}) {
  const { perfilAtual } = useAppData();
  const [form, setForm] = useState<FormState>(() => createInitialForm(peca));
  const [activeTab, setActiveTab] = useState("dados");

  const editing = peca !== undefined;
  const canSave = form.nome.trim().length > 0;
  const podeVerValor = podeVerDadosFinanceiros(perfilAtual);

  function updateForm(patch: Partial<FormState>) {
    setForm((current) => ({ ...current, ...patch }));
  }

  function handleSave() {
    const draft: PecaFormDraft = {
      nome: form.nome,
      categoria: form.categoria,
      tempoEstimadoMinutos: form.tempoEstimado.trim() === "" ? null : parseHoursInput(form.tempoEstimado),
      tempoMedioMinutos: form.tempoMedio.trim() === "" ? null : parseHoursInput(form.tempoMedio),
      tempoCalculadoExecucaoMinutos: peca?.tempoCalculadoExecucaoMinutos ?? null,
      valorTabelaCentavos: podeVerValor ? (form.valor.trim() === "" ? null : parseValorInput(form.valor)) : (peca?.valorTabelaCentavos ?? null),
      sindicatoAtivo: podeVerValor ? form.sindicatoAtivo : (peca?.sindicatoAtivo ?? false),
      valorSindicatoCriacaoCentavos: podeVerValor
        ? (form.valorSindicatoCriacao.trim() === "" ? null : parseValorInput(form.valorSindicatoCriacao))
        : (peca?.valorSindicatoCriacaoCentavos ?? null),
      valorSindicatoAdaptacaoCentavos: podeVerValor
        ? (form.valorSindicatoAdaptacao.trim() === "" ? null : parseValorInput(form.valorSindicatoAdaptacao))
        : (peca?.valorSindicatoAdaptacaoCentavos ?? null),
      valorSindicatoFinalizacaoCentavos: podeVerValor
        ? (form.valorSindicatoFinalizacao.trim() === "" ? null : parseValorInput(form.valorSindicatoFinalizacao))
        : (peca?.valorSindicatoFinalizacaoCentavos ?? null),
      briefingPadrao: form.briefingPadrao,
      ativa: form.ativa,
    };
    onSave(draft, peca?.id);
  }

  return (
    <Modal open={open} onClose={onClose} maxWidthClassName="max-w-xl">
      <div className="flex items-start justify-between gap-4 border-b border-zinc-100 pb-5 dark:border-zinc-800">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
            <Layers3 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-zinc-950 dark:text-zinc-50">
              {editing ? `Editando: ${peca.nome}` : "Nova peça no catálogo"}
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-500 dark:text-zinc-400">
              Modelo reutilizável — tempo estimado, valor de tabela e briefing padrão.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fechar"
          className="rounded-full p-2 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-5">
        <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      <div className="mt-5 flex flex-col gap-4">
        {activeTab === "dados" && (
          <>
            <Input
              label="Nome da peça"
              value={form.nome}
              onChange={(event) => updateForm({ nome: event.target.value })}
              placeholder="ex.: Post feed, Outdoor 9x3, VT 30s"
            />

            <div>
              <Input
                label="Categoria"
                value={form.categoria}
                onChange={(event) => updateForm({ categoria: event.target.value })}
                list="pecas-categorias"
                placeholder="ex.: Digital, Impresso, Vídeo"
              />
              <datalist id="pecas-categorias">
                {categoriasPecaDisponiveis.map((categoria) => (
                  <option key={categoria} value={categoria} />
                ))}
              </datalist>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Input
                label="Tempo estimado (h:mm)"
                value={form.tempoEstimado}
                onChange={(event) => updateForm({ tempoEstimado: event.target.value })}
                placeholder="ex.: 2:30"
                className="font-mono tabular-nums"
              />
              <Input
                label="Tempo médio (h:mm)"
                value={form.tempoMedio}
                onChange={(event) => updateForm({ tempoMedio: event.target.value })}
                placeholder="ex.: 3:15"
                className="font-mono tabular-nums"
              />
            </div>
            <p className="text-xs text-zinc-400">
              O tempo calculado pela execução da tarefa no sistema é automático — aparece assim que houver sessões de
              trabalho vinculadas a esta peça.
            </p>

            <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
              <Switch
                checked={form.ativa}
                onChange={(checked) => updateForm({ ativa: checked })}
                label={form.ativa ? "Ativa no catálogo" : "Inativa"}
                description={form.ativa ? undefined : "Não sugerir em novos orçamentos"}
              />
            </div>
          </>
        )}

        {activeTab === "valores" && (
          <>
            {podeVerValor ? (
              <Input
                label="Valor de tabela (R$)"
                value={form.valor}
                onChange={(event) => updateForm({ valor: event.target.value })}
                placeholder="ex.: 600,00"
                className="font-mono tabular-nums"
              />
            ) : (
              <div>
                <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                  Valor de tabela (R$)
                </span>
                <p className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/70 px-3 py-2.5 text-xs text-zinc-400 dark:border-zinc-700 dark:bg-zinc-800/60">
                  Visível apenas para Gestão e Diretoria
                </p>
              </div>
            )}

            {podeVerValor ? (
              <div>
                <div className="rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 dark:border-zinc-700 dark:bg-zinc-900">
                  <Switch
                    checked={form.sindicatoAtivo}
                    onChange={(checked) => updateForm({ sindicatoAtivo: checked })}
                    label="Aplicar valores de sindicato a esta peça"
                    description={form.sindicatoAtivo ? undefined : "Peça não sujeita a valores de sindicato"}
                  />
                </div>

                {form.sindicatoAtivo && (
                  <div className="mt-3">
                    <span className="mb-1.5 block text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                      Valores de sindicato
                    </span>
                    <div className="grid gap-3 md:grid-cols-3">
                      <Input
                        label="Criação (R$)"
                        value={form.valorSindicatoCriacao}
                        onChange={(event) => updateForm({ valorSindicatoCriacao: event.target.value })}
                        placeholder="0,00"
                        className="font-mono tabular-nums"
                      />
                      <Input
                        label="Adaptação (R$)"
                        value={form.valorSindicatoAdaptacao}
                        onChange={(event) => updateForm({ valorSindicatoAdaptacao: event.target.value })}
                        placeholder="0,00"
                        className="font-mono tabular-nums"
                      />
                      <Input
                        label="Finalização (R$)"
                        value={form.valorSindicatoFinalizacao}
                        onChange={(event) => updateForm({ valorSindicatoFinalizacao: event.target.value })}
                        placeholder="0,00"
                        className="font-mono tabular-nums"
                      />
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/70 px-3 py-2.5 text-xs text-zinc-400 dark:border-zinc-700 dark:bg-zinc-800/60">
                Valores de sindicato visíveis apenas para Gestão e Diretoria.
              </p>
            )}
          </>
        )}

        {activeTab === "briefing" && (
          <Textarea
            label="Briefing padrão"
            rows={10}
            placeholder="Formatos, especificações, observações que valem para toda peça deste tipo…"
            value={form.briefingPadrao}
            onChange={(event) => updateForm({ briefingPadrao: event.target.value })}
          />
        )}
      </div>

      <div className="mt-6 flex flex-col justify-end gap-3 border-t border-zinc-100 pt-4 dark:border-zinc-800 sm:flex-row">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="button" disabled={!canSave} onClick={handleSave}>
          {editing ? "Salvar alterações" : "Adicionar ao catálogo"}
        </Button>
      </div>
    </Modal>
  );
}
