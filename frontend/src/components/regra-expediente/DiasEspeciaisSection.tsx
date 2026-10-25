"use client";

import { useState } from "react";
import { CalendarPlus, Loader2, Trash2, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { DateField } from "@/components/ui/DateField";
import { Select } from "@/components/ui/Select";
import { Switch } from "@/components/ui/Switch";
import { atualizarDiaEspecialReal, criarDiaEspecialReal, removerDiaEspecialReal } from "@/lib/api-backend";
import {
  DIAS_SIGLA,
  diaDaSemanaDe,
  formatarDataIso,
  ordenarPeriodos,
  TIPO_DIA_ESPECIAL_DESCRICAO,
  TIPO_DIA_ESPECIAL_ROTULO,
  validarPeriodos,
} from "@/lib/expediente-periodos";
import type { DiaEspecial, PeriodoExpediente, TipoDiaEspecial } from "@/types/regra-expediente";
import { PeriodosDoDia } from "./PeriodosDoDia";

const TIPOS: TipoDiaEspecial[] = ["feriado", "recesso", "trabalho_excepcional", "ignorado"];
const TOM_DO_TIPO: Record<TipoDiaEspecial, "red" | "amber" | "green" | "neutral"> = { feriado: "red", recesso: "amber", trabalho_excepcional: "green", ignorado: "neutral" };

/**
 * Feriados e dias especiais — cadastro MANUAL (Fase Expediente 1). Cada ação (incluir, ativar/desativar, excluir) vale na hora: não depende do botão "Salvar" da
 * regra semanal. A importação automática de feriados é de outra etapa; as linhas "Automático" (quando existirem) só podem ser ativadas/desativadas.
 */
export function DiasEspeciaisSection({ dias, onChange }: { dias: DiaEspecial[]; onChange: (dias: DiaEspecial[]) => void }) {
  const [aberto, setAberto] = useState(false);
  const [data, setData] = useState("");
  const [nome, setNome] = useState("");
  const [tipo, setTipo] = useState<TipoDiaEspecial>("feriado");
  const [periodos, setPeriodos] = useState<PeriodoExpediente[]>([{ inicio: "08:00", fim: "12:00" }]);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const errosPeriodos = tipo === "trabalho_excepcional" ? validarPeriodos(periodos) : null;
  const datasManuais = new Set(dias.filter((dia) => dia.origem === "manual").map((dia) => dia.data));
  const duplicada = data !== "" && datasManuais.has(data);
  const podeIncluir = data !== "" && nome.trim().length > 0 && !duplicada && !errosPeriodos && (tipo !== "trabalho_excepcional" || periodos.length > 0) && ocupado === null;
  const ordenados = [...dias].sort((a, b) => a.data.localeCompare(b.data) || a.origem.localeCompare(b.origem));

  async function executar<T>(chave: string, acao: () => Promise<T>): Promise<T | null> {
    setOcupado(chave);
    setErro(null);
    try {
      return await acao();
    } catch (error) {
      setErro(error instanceof Error && error.message ? error.message : "Não foi possível concluir a ação.");
      return null;
    } finally {
      setOcupado(null);
    }
  }

  async function incluir() {
    const criado = await executar("novo", () =>
      criarDiaEspecialReal({ data, nome: nome.trim(), tipo, ativo: true, periodos: tipo === "trabalho_excepcional" ? ordenarPeriodos(periodos) : [] }),
    );
    if (!criado) return;
    onChange([...dias, criado]);
    setData("");
    setNome("");
    setTipo("feriado");
    setPeriodos([{ inicio: "08:00", fim: "12:00" }]);
    setAberto(false);
  }

  async function alternar(dia: DiaEspecial) {
    const atualizado = await executar(dia.id, () => atualizarDiaEspecialReal(dia.id, { ativo: !dia.ativo }));
    if (atualizado) onChange(dias.map((item) => (item.id === dia.id ? atualizado : item)));
  }

  async function remover(dia: DiaEspecial) {
    const feito = await executar(dia.id, async () => {
      await removerDiaEspecialReal(dia.id);
      return true;
    });
    if (feito) onChange(dias.filter((item) => item.id !== dia.id));
  }

  return (
    <section aria-labelledby="dias-especiais-titulo" className="rounded-xl border border-line bg-surface p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id="dias-especiais-titulo" className="text-sm font-semibold text-fg">
            Feriados e dias especiais
          </h2>
          <p className="mt-0.5 max-w-2xl text-xs leading-5 text-fg-muted">
            Um dia especial vale no lugar da regra da semana: feriado e recesso fecham o dia; trabalho excepcional usa períodos próprios. A importação automática de
            feriados nacionais será ativada em uma próxima etapa — por enquanto, cadastre as datas manualmente.
          </p>
        </div>
        <Button type="button" variant="secondary" className="px-3 py-1.5" onClick={() => setAberto((valor) => !valor)} aria-expanded={aberto}>
          <CalendarPlus className="h-3.5 w-3.5" aria-hidden />
          Adicionar dia especial
        </Button>
      </div>

      <p
        role="note"
        className="mt-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300"
      >
        <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
        <span>
          <strong>Atenção:</strong> enquanto o novo controle de expediente não estiver ativado, os dias especiais <strong>ativos já afetam</strong> os dias úteis, a
          entrada em execução das demandas e os cálculos de prazo (SLA). Cadastre só o que deve valer de verdade.
        </span>
      </p>

      {aberto && (
        <div className="mt-4 grid gap-3 rounded-xl border border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-800 dark:bg-zinc-950/30 md:grid-cols-[10rem_minmax(0,1fr)_14rem]">
          <DateField label="Data" value={data} onChange={setData} anulavel={false} />
          <Input label="Nome" value={nome} maxLength={120} placeholder="Ex.: Nossa Senhora Aparecida" onChange={(event) => setNome(event.target.value)} />
          <Select
            label="Tipo"
            value={tipo}
            onChange={(event) => setTipo(event.target.value as TipoDiaEspecial)}
            options={TIPOS.map((valor) => ({ value: valor, label: TIPO_DIA_ESPECIAL_ROTULO[valor] }))}
          />
          <p className="text-xs text-fg-muted md:col-span-3">{TIPO_DIA_ESPECIAL_DESCRICAO[tipo]}</p>
          {duplicada && (
            <p role="alert" className="text-xs font-medium text-red-600 dark:text-red-400 md:col-span-3">
              Já existe um dia especial manual nesta data — edite ou exclua o existente.
            </p>
          )}
          {tipo === "trabalho_excepcional" && (
            <div className="md:col-span-3">
              <PeriodosDoDia dia={data ? diaDaSemanaDe(data) : 0} periodos={periodos} erro={errosPeriodos ?? undefined} onChange={setPeriodos} />
            </div>
          )}
          <div className="flex justify-end md:col-span-3">
            <Button type="button" onClick={incluir} disabled={!podeIncluir}>
              {ocupado === "novo" && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
              Incluir
            </Button>
          </div>
        </div>
      )}

      {erro && (
        <p role="alert" className="mt-3 text-xs font-medium text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}

      {ordenados.length === 0 ? (
        <p className="mt-4 rounded-xl border border-dashed border-line p-4 text-center text-sm text-fg-subtle">Nenhum dia especial cadastrado.</p>
      ) : (
        <ul className="mt-4 divide-y divide-line rounded-xl border border-line">
          {ordenados.map((dia) => (
            <li key={dia.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2.5">
              <div className="w-28 shrink-0">
                <p className="text-sm font-semibold text-fg">{formatarDataIso(dia.data)}</p>
                <p className="text-xs text-fg-muted">{DIAS_SIGLA[diaDaSemanaDe(dia.data)]}</p>
              </div>
              <div className="min-w-0 flex-1">
                <p className={`truncate text-sm ${dia.ativo ? "text-fg" : "text-fg-subtle line-through"}`}>{dia.nome}</p>
                <div className="mt-1 flex flex-wrap items-center gap-1.5">
                  <Badge tone={TOM_DO_TIPO[dia.tipo]}>{TIPO_DIA_ESPECIAL_ROTULO[dia.tipo]}</Badge>
                  <Badge>{dia.origem === "manual" ? "Manual" : "Automático"}</Badge>
                  {dia.tipo === "trabalho_excepcional" && dia.periodos.length > 0 && (
                    <span className="text-xs text-fg-muted">{ordenarPeriodos(dia.periodos.map((p) => ({ inicio: p.inicio.slice(0, 5), fim: p.fim.slice(0, 5) }))).map((p) => `${p.inicio}–${p.fim}`).join(" · ")}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Switch checked={dia.ativo} disabled={ocupado === dia.id} onChange={() => void alternar(dia)} label={dia.ativo ? "Ativo" : "Inativo"} />
                {dia.origem === "manual" && (
                  <button
                    type="button"
                    disabled={ocupado === dia.id}
                    onClick={() => void remover(dia)}
                    aria-label={`Excluir ${dia.nome}`}
                    title="Excluir"
                    className="rounded-lg p-2 text-fg-subtle transition hover:bg-surface-hover hover:text-red-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-indigo-500 disabled:opacity-40"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
